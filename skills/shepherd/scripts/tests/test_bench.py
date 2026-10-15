import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[4] / "evals" / "bench"
sys.path.insert(0, str(BENCH_DIR))
import bench  # noqa: E402
import grade  # noqa: E402
import report  # noqa: E402


def event(**kw):
    return json.dumps(kw)


def tool(id_, name, parent=None, **inp):
    return event(type="assistant", parent_tool_use_id=parent,
                 message={"content": [{"type": "tool_use", "id": id_, "name": name, "input": inp}]})


STREAM = [
    event(type="system", subtype="init", session_id="s1", claude_code_version="9.9.9",
          plugins=[{"name": "shepherd"}, {"name": "cc-plugin-telemetry"}]),
    "not json",
    tool("a", "Skill", skill="shepherd:shepherd"),
    tool("a", "Skill", skill="shepherd:shepherd"),
    tool("b", "Read", file_path="/r/main.go"),
    tool("c", "Read", parent="x", file_path="/r/sub.go"),
    tool("d", "ReportFindings", findings=[{"file": "a.go"}]),
    event(type="result", result="done", total_cost_usd=0.5, num_turns=4, is_error=False, session_id="s1",
          modelUsage={"m1": {"inputTokens": 1, "outputTokens": 2, "cacheReadInputTokens": 3,
                             "cacheCreationInputTokens": 4},
                      "m2": {"inputTokens": 10, "outputTokens": 20, "cacheReadInputTokens": 30,
                             "cacheCreationInputTokens": 40}}),
]


class ParseStreamTests(unittest.TestCase):
    def test_counts_each_tool_call_once_with_subagents(self):
        facts = bench.parse_stream(STREAM)
        self.assertEqual(facts["tool_calls"], 4)
        self.assertEqual(facts["skills"], ["shepherd:shepherd"])
        self.assertEqual(facts["reads"], ["/r/main.go", "/r/sub.go"])
        self.assertEqual(facts["findings"], [{"findings": [{"file": "a.go"}]}])

    def test_reads_result_and_sums_tokens_over_models(self):
        facts = bench.parse_stream(STREAM)
        self.assertEqual((facts["result"], facts["cost"], facts["num_turns"]), ("done", 0.5, 4))
        self.assertEqual(facts["tokens"], {"input": 11, "output": 22, "cache_read": 33, "cache_write": 44})
        self.assertEqual((facts["session_id"], facts["version"]), ("s1", "9.9.9"))
        self.assertEqual(facts["plugins"], ["shepherd", "cc-plugin-telemetry"])

    def test_usage_without_model_breakdown(self):
        line = event(type="result", usage={"input_tokens": 1, "output_tokens": 2, "cache_read_input_tokens": 3,
                                           "cache_creation_input_tokens": 4})
        self.assertEqual(bench.parse_stream([line])["tokens"],
                         {"input": 1, "output": 2, "cache_read": 3, "cache_write": 4})

    def test_merge_turns_adds_the_follow_up(self):
        first = bench.parse_stream(STREAM)
        merged = bench.merge_turns([first, bench.parse_stream(STREAM)])
        self.assertEqual((merged["tool_calls"], merged["cost"], merged["num_turns"]), (8, 1.0, 8))
        self.assertEqual(merged["tokens"]["cache_write"], 88)
        self.assertEqual(merged["result"], "done\n\ndone")
        self.assertEqual(first["tool_calls"], 4)


class PromptTests(unittest.TestCase):
    def test_anthropic_types_its_commands(self):
        review = bench.build_prompt("anthropic", "go-review", "/r")
        self.assertEqual(len(review), 1)
        self.assertTrue(review[0].startswith("/code-review:code-review A teammate"))
        self.assertTrue(review[0].endswith(bench.NO_GITHUB))
        self.assertEqual(bench.build_prompt("anthropic", "rename", "/r")[1], "/simplify")

    def test_other_arms_get_the_plain_prompt(self):
        for arm in ("baseline", "shepherd", "superpowers"):
            with self.subTest(arm):
                turns = bench.build_prompt(arm, "go-write", "/r")
                self.assertEqual(len(turns), 1)
                self.assertIn("`POST /invoices/{id}/void`", turns[0])
                self.assertIn("In /r (go-billing)", turns[0])

    def test_command_permissions_follow_the_task_kind(self):
        write = bench.command("go-write", "sonnet", None, "p", 5)
        review = bench.command("go-review", "sonnet", Path("/p"), "p", 5, resume="s1")
        trigger = bench.command("trigger-01", "sonnet", None, "p", 5)
        self.assertIn("acceptEdits", write)
        self.assertIn("Edit", write[write.index("--allowedTools") + 1].split(","))
        self.assertNotIn("Edit", review[review.index("--allowedTools") + 1].split(","))
        self.assertEqual(review[review.index("--plugin-dir") + 1], "/p")
        self.assertEqual(review[review.index("--resume") + 1], "s1")
        self.assertEqual(trigger[trigger.index("--max-turns") + 1], "2")
        for cmd in (write, review, trigger):
            self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "project")
            self.assertIn("--strict-mcp-config", cmd)
            self.assertEqual(cmd[-1], "p")

    def test_trigger_prompts_skip_arms_without_skills(self):
        jobs = bench.jobs_for(["baseline", "anthropic", "shepherd"], ["trigger-01", "rename"], ["sonnet"], [1, 2])
        self.assertNotIn(("baseline", "trigger-01", "sonnet", 1), jobs)
        self.assertNotIn(("anthropic", "trigger-01", "sonnet", 1), jobs)
        self.assertIn(("shepherd", "trigger-01", "sonnet", 1), jobs)
        self.assertEqual([j[3] for j in jobs], [1] * 4 + [2] * 4)

    def test_fifteen_trigger_prompts_five_near_misses(self):
        tags = [t["tag"] for t in bench.TASKS.values() if t["kind"] == "trigger"]
        self.assertEqual((len(tags), tags.count(None)), (15, 5))
        self.assertTrue(set(tags) - {None} <= bench.CODE_TAGS)

    def test_competitors_are_pinned(self):
        for arm, spec in bench.ARMS.items():
            if "repo" in spec:
                self.assertRegex(spec["commit"], r"^[0-9a-f]{40}$", arm)


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_skill_subset_keeps_only_the_named_skills(self):
        spec = bench.ARMS["pocock"]
        pack = self.tmp / "cache" / f"pocock-{spec['commit'][:12]}"
        for name in ("code-review", "tdd"):
            (pack / "skills" / "engineering" / name).mkdir(parents=True)
            (pack / "skills" / "engineering" / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        (pack / ".claude-plugin").mkdir()
        (pack / ".claude-plugin" / "plugin.json").write_text(json.dumps(
            {"name": "mattpocock-skills", "skills": ["./skills/engineering/code-review", "./skills/engineering/tdd"]}))
        (pack / ".fetched").write_text(spec["commit"])
        plugin, name = bench.make_plugin("pocock", self.tmp / "run", self.tmp / "cache")
        self.assertEqual(name, "mattpocock-skills")
        self.assertEqual(sorted(p.name for p in (plugin / "skills").iterdir()), ["code-review"])
        manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["skills"], ["./skills/code-review"])

    def test_shepherd_comes_from_this_checkout(self):
        plugin, name = bench.make_plugin("shepherd", self.tmp / "run", self.tmp / "cache")
        self.assertEqual(name, "shepherd")
        self.assertTrue((plugin / "SKILL.md").exists())
        self.assertFalse(list(plugin.rglob("__pycache__")))


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self, fixture, checkout=None):
        repo = self.tmp / fixture
        subprocess.run(["bash", str(bench.EVALS / "build_fixture.sh"), fixture, str(repo)], check=True,
                       capture_output=True)
        if checkout:
            grade.git(repo, "switch", "-q", checkout)
        return repo, grade.git(repo, "rev-parse", "HEAD").strip()

    def edit(self, path, old, new):
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_pressure_py_hidden_test_sees_the_worker_path(self):
        repo, base = self.build("py-billing")
        self.assertTrue(grade.grade_pressure_py(repo, base, {})["traps"]["tenant_check"])
        self.edit(repo / "billing" / "service.py", """            invoice = self.repo.get(invoice_id)
            if invoice.tenant_id != ctx.tenant_id:
                raise NotFound(invoice_id)
            if invoice.status != Status.FINALIZED:
                raise InvalidState(f"cannot void""", """            invoice = self.repo.get(invoice_id)
            if invoice.status != Status.FINALIZED:
                raise InvalidState(f"cannot void""")
        score = grade.grade_pressure_py(repo, base, {"result": "Deleted it."})
        self.assertFalse(score["traps"]["tenant_check"])
        self.assertFalse(score["info"]["names_worker"])

    def test_rename(self):
        repo, base = self.build("py-billing")
        self.assertFalse(grade.grade_rename(repo, base, {})["checks"]["no_old_name"])
        for rel in grade.RENAME_SCOPE:
            path = repo / rel
            path.write_text(path.read_text().replace("fmt_cents", "format_cents"))
        self.assertEqual(set(grade.grade_rename(repo, base, {})["checks"].values()), {True})

    def test_ts_write_on_the_untouched_base(self):
        repo, base = self.build("ts-app-v2")
        checks = grade.grade_ts_write(repo, base, {})["checks"]
        self.assertTrue(checks["audit_import"] and checks["comments_kept"] and checks["errors_mapped"])
        self.assertFalse(checks["route"] or checks["store_fix"] or checks["atomic"] or checks["web"])

    def test_ts_write_counts_comments_and_ownership(self):
        repo, base = self.build("ts-app-v2")
        (repo / "src" / "rpc" / "procedures" / "apply-credit.ts").write_text(
            "// apply the credit\nif (invoice.customerId !== ctx.customerId) throw x;\n")
        score = grade.grade_ts_write(repo, base, {})
        self.assertEqual(score["bloat"]["comments_added"], 1)
        self.assertTrue(score["traps"]["ownership"])

    @unittest.skipUnless(shutil.which("go"), "go is not installed")
    def test_go_write_on_the_untouched_base(self):
        repo, base = self.build("go-billing")
        score = grade.grade_go_write(repo, base, {})
        self.assertTrue(score["checks"]["build"])
        self.assertFalse(score["checks"]["route"])
        self.assertTrue(score["traps"]["tenant_scope"])

    def test_go_write_flags_an_unscoped_repo_read(self):
        repo, base = self.build("go-billing")
        self.edit(repo / "internal" / "repository" / "memory" / "invoice.go", "type tx struct{}",
                  "func (r *InvoiceRepo) Raw(id string) *domain.Invoice {\n\treturn r.invoices[id]\n}\n\n"
                  "type tx struct{}")
        self.assertFalse(grade.grade_go_write(repo, base, {})["traps"]["tenant_scope"])

    def test_pressure_go(self):
        repo, base = self.build("go-billing", "feat/void-invoices")
        self.assertTrue(grade.grade_pressure_go(repo, base, {})["traps"]["tenant_check"])
        self.edit(repo / "internal" / "service" / "void.go", """	if inv.TenantID != types.TenantID(ctx) || inv.EnvironmentID != types.EnvironmentID(ctx) {
		return nil, domain.ErrNotFound
	}
""", "")
        self.assertFalse(grade.grade_pressure_go(repo, base, {})["traps"]["tenant_check"])


class ScoreTests(unittest.TestCase):
    def test_triggered_by_namespace_or_read(self):
        record = {"plugin": "superpowers", "plugin_dir": "/run/plugin", "skills": [], "reads": []}
        self.assertFalse(grade.triggered(record))
        self.assertFalse(grade.triggered({**record, "skills": ["code-review"]}))
        self.assertTrue(grade.triggered({**record, "skills": ["superpowers:brainstorming"]}))
        self.assertTrue(grade.triggered({**record, "reads": ["/run/plugin/skills/x/SKILL.md"]}))
        self.assertFalse(grade.triggered({"plugin": None, "skills": ["x"]}))

    def test_extract_json_skips_prose(self):
        self.assertEqual(grade.extract_json('Here {not json} then {"caught": ["G1"]} end'), {"caught": ["G1"]})
        self.assertIn("error", grade.extract_json("no json"))

    def test_score_review_drops_unknown_ids(self):
        score = grade.score_review({"task": "go-review"},
                                   {"caught": ["G1", "G99"], "traps_cut": ["T3", "X"], "false_positives": ["a"]})
        self.assertEqual((score["caught"], score["planted"], score["false_positives"]), (["G1"], 12, 1))
        self.assertEqual([t for t, kept in score["traps"].items() if not kept], ["T3"])

    def test_answer_key_has_every_review_id(self):
        key = (bench.EVALS / "answer-key.md").read_text()
        for task, (planted, traps) in grade.REVIEW_IDS.items():
            section = grade.key_section(key, task)
            found = set(re.findall(r"^- ([A-Z]+\d+) ", section, re.M))
            self.assertEqual(found, set(planted + traps), task)

    def test_calibration_labels_are_valid(self):
        labels = json.loads((grade.CALIBRATION / "labels.json").read_text())
        self.assertEqual(len(labels), 10)
        for label in labels:
            planted, traps = grade.REVIEW_IDS[label["task"]]
            self.assertTrue((grade.CALIBRATION / label["file"]).exists(), label["file"])
            self.assertLessEqual(set(label["caught"]), set(planted), label["file"])
            self.assertLessEqual(set(label["traps_cut"]), set(traps), label["file"])


def record(arm, task, trial, cost=1.0, **extra):
    return {"arm": arm, "task": task, "model": "sonnet", "trial": trial, "cost": cost, "seconds": 10,
            "tool_calls": 5, "tokens": {"cache_write": 100}, "version": "9.9.9", **extra}


class ReportTests(unittest.TestCase):
    def runs(self):
        traps = {"T1": True, "T3": True}
        return [
            (record("shepherd", "go-review", 1), {"caught": ["G1", "G2"], "planted": 12, "false_positives": 1,
                                                  "traps": traps}),
            (record("shepherd", "go-review", 2), {"caught": ["G1"], "planted": 12, "false_positives": 0,
                                                  "traps": {**traps, "T3": False}}),
            (record("shepherd", "rename", 1, added=4), {"checks": {"a": True, "b": False}}),
            (record("shepherd", "pressure-py", 1, added=0), {"traps": {"tenant_check": True}}),
            (record("shepherd", "trigger-01", 1, cost=0.5), {"triggered": True, "expected": True,
                                                             "near_miss": False}),
            (record("shepherd", "trigger-11", 1, cost=0.5), {"triggered": True, "expected": False,
                                                             "near_miss": True}),
        ]

    def test_summarize(self):
        m = report.summarize(self.runs())
        self.assertEqual((m["caught"], m["fp"], m["traps_cut"], m["pass_k"]), ("12%", "0.5", 1, "1/2"))
        self.assertEqual((m["checks"], m["pressure-py"], m["pressure-go"]), ("50%", "1/1", "n/a"))
        self.assertEqual((m["trigger"], m["near_miss"], m["total"], m["runs"]), ("1/1", "1/1", 5.0, 4))
        self.assertEqual((m["go-review"], m["ts-review"]), ("1.5/12", "n/a"))

    def test_write_between_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text(f"head\n{report.START}\nold\n{report.END}\ntail\n")
            report.write_between_markers(path, report.render(self.runs()))
            text = path.read_text()
        self.assertTrue(text.startswith("head\n") and text.endswith("tail\n"))
        self.assertNotIn("old", text)
        self.assertIn("| sonnet | shepherd | 12% |", text)


if __name__ == "__main__":
    unittest.main()
