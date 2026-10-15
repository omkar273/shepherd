import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SKILLS_DIR = Path(__file__).resolve().parents[3]
CMD = 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"'


def run(script, home, *args, check=True):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, "--home", str(home)],
        capture_output=True, text=True, check=check,
    )


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        (self.home / ".claude").mkdir()
        self.settings = self.home / ".claude" / "settings.json"
        self.state = self.home / ".claude" / "shepherd.json"


class SettingsTests(Base):
    def add(self, *extra):
        return run("settings.py", self.home, "add-hook", "--event", "SessionStart",
                   "--command", CMD, *extra, check=False)

    def hooks(self):
        return json.loads(self.settings.read_text())["hooks"]["SessionStart"]

    def test_add_hook_to_empty(self):
        self.assertEqual(self.add("--write").returncode, 0)
        self.assertEqual(self.hooks(), [{"hooks": [{"type": "command", "command": CMD}]}])

    def test_add_hook_idempotent(self):
        self.add("--write")
        result = self.add("--write")
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(len(self.hooks()), 1)

    def test_keeps_other_keys(self):
        self.settings.write_text(json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": []}]}}))
        self.add("--write")
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["model"], "opus")
        self.assertIn("Stop", data["hooks"])

    def test_invalid_json_exit1_untouched(self):
        self.settings.write_text("{not json")
        self.assertEqual(self.add("--write").returncode, 1)
        self.assertEqual(self.settings.read_text(), "{not json")

    def test_no_write_without_flag(self):
        result = self.add()
        self.assertIn("SessionStart", result.stdout)
        self.assertFalse(self.settings.exists())

    def merge(self, patch, *extra):
        return run("settings.py", self.home, "merge", "--json", json.dumps(patch), *extra)

    def test_merge_top_level(self):
        self.settings.write_text(json.dumps({"model": "opus"}))
        self.merge({"autoCompactWindow": 300000}, "--write")
        self.assertEqual(json.loads(self.settings.read_text()),
                         {"model": "opus", "autoCompactWindow": 300000})

    def test_merge_nested_keeps_siblings(self):
        self.settings.write_text(json.dumps({"skillOverrides": {"a": "off"}}))
        self.merge({"skillOverrides": {"b": "name-only"}}, "--write")
        self.assertEqual(json.loads(self.settings.read_text())["skillOverrides"],
                         {"a": "off", "b": "name-only"})

    def test_merge_null_removes_key(self):
        self.settings.write_text(json.dumps({"skillOverrides": {"a": "name-only", "b": "off"}}))
        self.merge({"skillOverrides": {"a": None, "c": None}}, "--write")
        self.assertEqual(json.loads(self.settings.read_text())["skillOverrides"], {"b": "off"})

    def test_merge_to_file(self):
        local = self.home / "repo" / ".claude" / "settings.local.json"
        self.merge({"enabledPlugins": {"x@y": False}}, "--file", str(local), "--write")
        self.assertEqual(json.loads(local.read_text()), {"enabledPlugins": {"x@y": False}})
        self.assertFalse(self.settings.exists())

    def test_merge_idempotent(self):
        self.merge({"autoCompactWindow": 300000}, "--write")
        self.assertEqual(self.merge({"autoCompactWindow": 300000}, "--write").stdout, "")

    def test_merge_no_write_without_flag(self):
        self.assertIn('+  "autoCompactWindow": 300000', self.merge({"autoCompactWindow": 300000}).stdout)
        self.assertFalse(self.settings.exists())

    def test_add_hook_to_file(self):
        local = self.home / "settings.local.json"
        self.add("--file", str(local), "--write")
        self.assertIn("SessionStart", json.loads(local.read_text())["hooks"])
        self.assertFalse(self.settings.exists())

    def test_remove_hook(self):
        self.add("--write")
        run("settings.py", self.home, "remove-hook", "--event", "SessionStart",
            "--command", CMD, "--write")
        self.assertNotIn("SessionStart", json.loads(self.settings.read_text()).get("hooks", {}))


class NudgeTests(Base):
    def nudge(self):
        return run("nudge.py", self.home)

    def stamp(self, days_ago):
        day = datetime.date.today() - datetime.timedelta(days=days_ago)
        self.state.write_text(json.dumps({"repo": "/r", "last_update": day.isoformat()}))

    def test_stale_prints_line(self):
        self.stamp(9)
        self.assertEqual(self.nudge().stdout.strip(),
                         'Skills last updated 9 days ago. Say "update my skills".')

    def test_fresh_silent(self):
        self.stamp(2)
        self.assertEqual(self.nudge().stdout, "")

    def test_missing_state_silent(self):
        self.assertEqual(self.nudge().stdout, "")

    def test_garbage_state_exit0(self):
        self.state.write_text("garbage")
        result = self.nudge()
        self.assertEqual((result.returncode, result.stdout), (0, ""))


class StateTests(Base):
    def test_stamp_keeps_other_keys(self):
        self.state.write_text(json.dumps({"repo": "/old", "packs": ["design"]}))
        run("state.py", self.home, "stamp", "--repo", "/new")
        data = json.loads(self.state.read_text())
        self.assertEqual((data["repo"], data["packs"]), ("/new", ["design"]))

    def test_stamp_writes_today(self):
        run("state.py", self.home, "stamp", "--repo", "/some/repo")
        data = json.loads(self.state.read_text())
        self.assertEqual(data, {"repo": "/some/repo", "last_update": datetime.date.today().isoformat()})


class StatusTests(Base):
    def status(self):
        return json.loads(run("status.py", self.home).stdout)

    def test_reports_missing(self):
        report = self.status()
        self.assertIn("claude/shepherd", report["missing"])
        self.assertIn("summary", report)

    def test_reports_broken_link(self):
        runtime = self.home / ".claude" / "skills"
        runtime.mkdir()
        (runtime / "gone").symlink_to(self.home / "nowhere")
        self.assertIn("claude/gone", self.status()["broken"])

    def test_status_reports_packs(self):
        self.state.write_text(json.dumps({"packs": ["design"]}))
        report = self.status()
        self.assertEqual(report["packs_installed"], ["design"])
        self.assertIn("packs_available", report)

    def test_reports_shadowed(self):
        (self.home / ".claude" / "skills" / "research").mkdir(parents=True)
        self.assertIn("claude/research", self.status()["shadowed"])


def listing(*names):
    return {"type": "attachment", "attachment": {"type": "skill_listing", "names": list(names)}}


def tool_use(name, **tool_input):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_1", "name": name, "input": tool_input}]}}


def prompt(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


class CatalogUsageTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = self.home / "work" / "my.app"
        self.repo.mkdir(parents=True)
        # Claude Code names project folders this way, e.g. "/a/my.app" -> "-a-my-app".
        self.slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.repo.resolve()))
        self.sessions = 0
        # A name with no skill folder and no builtin is stale, so the tests install these as user skills.
        for name in ("shepherd", "grilling", "prototype", "wizard", "pr", "seo-audit"):
            (self.home / ".claude" / "skills" / name).mkdir(parents=True)

    def session(self, entries, project=None, days_ago=0):
        self.sessions += 1
        folder = self.home / ".claude" / "projects" / (project or self.slug)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"session-{self.sessions}.jsonl"
        path.write_text("".join(json.dumps(e) + "\n" for e in entries))
        stamp = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).timestamp()
        os.utime(path, (stamp, stamp))
        return path

    def report(self, *args):
        result = run("status.py", self.home, "--catalog", "--repo", str(self.repo), *args)
        return json.loads(result.stdout)

    def skill(self, report, name):
        return next(s for s in report["skills"] if s["name"] == name)

    def write_overrides(self, overrides):
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "settings.local.json").write_text(json.dumps({"skillOverrides": overrides}))

    def write_skill(self, base, name, description):
        (base / ".claude" / "skills" / name).mkdir(parents=True, exist_ok=True)
        (base / ".claude" / "skills" / name / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n")

    def index(self):
        return run("status.py", self.home, "--index", "--repo", str(self.repo)).stdout

    def test_catalog_name_only_for_unused(self):
        self.session([listing("shepherd", "grilling", "prototype"), tool_use("Skill", skill="shepherd"),
                      prompt("<command-name>/grilling</command-name>")])
        report = self.report()
        self.assertEqual(report["sessions"], 1)
        self.assertEqual(report["keep"], ["grilling", "shepherd"])
        self.assertEqual(report["patch"], {"skillOverrides": {"prototype": "name-only"}})
        self.assertEqual(self.skill(report, "shepherd")["invocations"], 1)

    def test_catalog_keeps_routed_and_listed_skills(self):
        local = self.repo / ".claude" / "settings.local.json"
        local.parent.mkdir()
        local.write_text(json.dumps({"skillOverrides": {"seo-audit": "name-only", "grilling": "off"}}))
        (self.home / ".claude" / "skills" / "brainstorming").mkdir()
        self.session([listing("shepherd", "brainstorming", "executing-plans", "seo-audit", "grilling", "wizard",
                              "superpowers:executing-plans", "superpowers:writing-plans")])
        self.session([tool_use("Skill", skill="superpowers:executing-plans")])
        report = self.report("--keep", "seo-*")
        self.assertEqual(report["keep"], ["brainstorming", "seo-audit", "shepherd"])
        self.assertEqual(report["patch"], {"skillOverrides": {"seo-audit": None, "wizard": "name-only"}})
        self.assertEqual(report["app_plugins"], {})

    def test_catalog_patch_only(self):
        self.session([listing("grilling")])
        output = run("status.py", self.home, "--catalog", "--repo", str(self.repo), "--patch").stdout
        self.assertEqual(json.loads(output), {"skillOverrides": {"grilling": "name-only"}})

    def test_catalog_kinds(self):
        (self.repo / ".claude" / "skills" / "local").mkdir(parents=True)
        self.session([listing("shepherd", "local", "simplify", "design:ux-copy", "gone")])
        report = self.report()
        kinds = {s["name"]: s["kind"] for s in report["skills"]}
        self.assertEqual(kinds, {"shepherd": "user", "local": "project", "simplify": "builtin",
                                 "design:ux-copy": "plugin", "gone": "stale"})

    def test_catalog_counts_bare_plugin_skill_name(self):
        self.session([listing("superpowers:brainstorming", "design:ux-copy"),
                      tool_use("Skill", skill="brainstorming")])
        report = self.report()
        self.assertEqual(self.skill(report, "superpowers:brainstorming")["invocations"], 1)
        self.assertEqual(report["app_plugins"], {"design": 1})

    def test_catalog_plugin_agents_and_mcp_count(self):
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": {"pt@market": [{"scope": "user"}]}}))
        self.session([listing("eng:debug", "pt:audit"), tool_use("Agent", subagent_type="eng:reviewer"),
                      tool_use("mcp__plugin_pt_server__fetch")])
        report = self.report()
        self.assertEqual((report["patch"], report["app_plugins"]), ({}, {}))
        self.assertEqual(report["plugins"], [{"name": "eng", "key": None, "invocations": 1},
                                             {"name": "pt", "key": "pt@market", "invocations": 1}])

    def test_catalog_ignores_old_sessions(self):
        self.session([listing("grilling"), tool_use("Skill", skill="grilling")], days_ago=40)
        self.session([listing("grilling")])
        report = self.report()
        self.assertEqual((report["sessions"], report["patch"]), (1, {"skillOverrides": {"grilling": "name-only"}}))

    def test_catalog_includes_worktrees_and_subagents_not_siblings(self):
        self.session([listing("grilling", "pr")])
        self.session([tool_use("Skill", skill="grilling")], project=f"{self.slug}--claude-worktrees-x")
        self.session([tool_use("Skill", skill="pr")], project=f"{self.slug}/session-1/subagents")
        self.session([listing("zzz")], project=f"{self.slug}-old")
        report = self.report()
        self.assertEqual([s["name"] for s in report["skills"]], ["grilling", "pr"])
        self.assertEqual(report["patch"], {})
        self.assertEqual(report["sessions"], 2)

    def test_catalog_turns_off_unused_keyed_plugin(self):
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(json.dumps(
            {"plugins": {"pt@market": [], "sp@market": []}}))
        self.session([listing("pt:audit", "sp:systematic-debugging", "eng:debug", "eng:standup")])
        report = self.report()
        self.assertEqual(report["patch"], {"enabledPlugins": {"pt@market": False}})
        self.assertEqual(report["app_plugins"], {"eng": 2})

    def test_catalog_drops_stale_names(self):
        self.write_overrides({"gone": "name-only", "old": "off", "sp:x": "name-only"})
        self.session([listing("grilling", "removed")])
        report = self.report()
        self.assertEqual(self.skill(report, "removed")["kind"], "stale")
        self.assertEqual(report["patch"], {"skillOverrides": {"gone": None, "grilling": "name-only"}})

    def test_index_cuts_descriptions(self):
        self.write_overrides({"grilling": "name-only", "local": "name-only", "simplify": "name-only",
                              "wizard": "off", "gone": "name-only", "sp:x": "name-only"})
        self.write_skill(self.home, "grilling", "Grill the user about a plan, or a decision.")
        self.write_skill(self.repo, "local", "alpha " * 40)
        lines = self.index().splitlines()
        self.assertEqual(lines[1:3], ["- grilling: Grill the user about a plan, or a decision.",
                                      "- local: " + " ".join(["alpha"] * 26) + " ..."])
        self.assertTrue(lines[3].startswith("- simplify: Review the changed code"))
        self.assertEqual(len(lines), 4)

    def test_index_stays_under_hook_cap(self):
        names = [f"skill-{i:03d}" for i in range(120)]
        self.write_overrides(dict.fromkeys(names, "name-only"))
        for name in names:
            self.write_skill(self.home, name, "Use when the task needs this skill. " * 10)
        output = self.index()
        self.assertLessEqual(len(output), 10_000)
        self.assertEqual(len(output.splitlines()), 121)

    def test_index_silent_without_overrides(self):
        self.assertEqual(self.index(), "")

    def test_prune_registers_index_hook_for_startup_clear_compact(self):
        doc = (SCRIPTS.parent / "skills.md").read_text()
        command = re.search(r"`settings\.py (add-hook [^`]*--index[^`]*)`", doc).group(1)
        run("settings.py", self.home, *shlex.split(command.replace("<the repo>", str(self.repo))), "--write")
        group = json.loads((self.repo / ".claude" / "settings.local.json").read_text())["hooks"]["SessionStart"][0]
        self.assertEqual(group["matcher"], "startup|clear|compact")
        self.assertIn('status.py" --index', group["hooks"][0]["command"])

    def test_catalog_no_transcript_text(self):
        self.session([listing("grilling"), prompt("SECRET-PROMPT-TEXT"),
                      tool_use("Bash", command="SECRET-COMMAND")])
        output = run("status.py", self.home, "--catalog", "--repo", str(self.repo)).stdout
        self.assertNotIn("SECRET", output)


if __name__ == "__main__":
    unittest.main()
