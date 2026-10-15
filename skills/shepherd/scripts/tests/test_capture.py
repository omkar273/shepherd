import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

CAPTURE = Path(__file__).resolve().parents[2] / "hooks" / "capture.py"
SKILL = Path(__file__).resolve().parents[2] / "SKILL.md"
TODAY = datetime.date.today().isoformat()
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def hook_commands():
    """The command each event runs, from the hooks block in SKILL.md's frontmatter."""
    commands, event = {}, None
    for line in SKILL.read_text().split("---", 2)[1].splitlines():
        if match := re.match(r"^  (\w+):$", line):
            event = match[1]
        elif (match := re.match(r"^\s+command: '(.*)'$", line)) and event:
            commands[event] = match[1].replace("''", "'")
    return commands


def ago(days):
    stamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return stamp.isoformat(timespec="seconds")


class Base(unittest.TestCase):
    """A full-clone layout in a temp dir: <tmp>/clone/{setup/claude-md.md, skills/shepherd}."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        clone = self.tmp / "clone"
        (clone / "setup").mkdir(parents=True)
        (clone / "setup" / "claude-md.md").write_text("")
        self.root = clone / "skills" / "shepherd"
        (self.root / "lessons").mkdir(parents=True)
        (self.root / "lessons" / "global.md").write_text("")
        self.inbox = self.root / "inbox"
        self.env = {**os.environ, **GIT_ENV}

    def run_capture(self, *args, stdin="", cwd=None):
        return subprocess.run(
            [sys.executable, str(CAPTURE), *args, "--root", str(self.root)],
            input=stdin, capture_output=True, text=True, env=self.env, cwd=cwd,
        )

    def lines(self, name):
        path = self.inbox / name
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def make_repo(self, name, remote=None):
        repo = self.tmp / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, env=self.env)
        if remote:
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", remote], check=True, env=self.env)
        return repo


class TurnTests(Base):
    def turn(self, payload):
        return self.run_capture("turn", stdin=payload if isinstance(payload, str) else json.dumps(payload))

    def test_prompt_appends_one_line(self):
        result = self.turn({"session_id": "s1", "cwd": "/x", "hook_event_name": "UserPromptSubmit",
                            "prompt": "hello", "transcript_path": "/t.jsonl"})
        self.assertEqual(result.returncode, 0)
        [entry] = self.lines("turns.jsonl")
        self.assertEqual(set(entry), {"ts", "session_id", "cwd", "event", "text"})
        self.assertEqual((entry["session_id"], entry["cwd"], entry["event"], entry["text"]),
                         ("s1", "/x", "UserPromptSubmit", "hello"))

    def test_stop_uses_last_assistant_message(self):
        self.turn({"session_id": "s1", "cwd": "/x", "hook_event_name": "Stop",
                   "last_assistant_message": "done", "stop_hook_active": False})
        self.assertEqual(self.lines("turns.jsonl")[0]["text"], "done")

    def test_correction_prompt_gets_a_reminder(self):
        for prompt in ["Finding 6 is wrong: in this repo the interface is needed because of plugins",
                       "Put that nil check back, the worker passes nil", "Undo that cut"]:
            with self.subTest(prompt=prompt):
                out = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit",
                                 "prompt": prompt}).stdout
                self.assertIn("capture.py signal", out)

    def test_other_turns_print_nothing(self):
        prompt = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit",
                            "prompt": "Review the branch feat/x"})
        reply = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "Stop",
                           "last_assistant_message": "Finding 2 is wrong to keep; undo it"})
        self.assertEqual((prompt.stdout, reply.stdout), ("", ""))

    def test_garbage_exits_0(self):
        for payload in ["not json", "", "[]", "null", '{"hook_event_name": "Stop"}']:
            with self.subTest(payload=payload):
                self.assertEqual(self.turn(payload).returncode, 0)
        self.assertEqual(self.lines("turns.jsonl"), [])

    def test_text_cut_to_4kb(self):
        self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit", "prompt": "é" * 5000})
        self.assertEqual(self.lines("turns.jsonl")[0]["text"], "é" * 2048)

    def test_drops_entries_older_than_30_days(self):
        self.inbox.mkdir()
        old = {"ts": ago(31), "session_id": "old", "cwd": "/", "event": "Stop", "text": "a"}
        recent = {"ts": ago(29), "session_id": "recent", "cwd": "/", "event": "Stop", "text": "b"}
        (self.inbox / "turns.jsonl").write_text(json.dumps(old) + "\n" + json.dumps(recent) + "\n")
        self.turn({"session_id": "new", "cwd": "/", "hook_event_name": "UserPromptSubmit", "prompt": "c"})
        self.assertEqual([e["session_id"] for e in self.lines("turns.jsonl")], ["recent", "new"])

    def test_silent_outside_full_clone(self):
        (self.tmp / "clone" / "setup" / "claude-md.md").unlink()
        result = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit", "prompt": "x"})
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.inbox.exists())


class SignalTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = self.make_repo("billing", "git@github.com:acme/billing.git")
        self.lesson_file = self.root / "lessons" / "repos" / "acme-billing.md"

    def signal(self, kind, lesson=None, *extra, cwd=None, evidence="a.go:12 kept for plugins"):
        args = ["signal", "--kind", kind, "--rule", "cut list: one-impl interface", "--evidence", evidence]
        if lesson is not None:
            args += ["--lesson", lesson]
        return self.run_capture(*args, *extra, cwd=cwd or self.repo)

    def test_records_fields(self):
        self.signal("reject")
        [entry] = self.lines("signals.jsonl")
        self.assertEqual(set(entry), {"ts", "repo", "kind", "rule", "evidence", "lesson"})
        self.assertEqual((entry["repo"], entry["kind"], entry["rule"], entry["evidence"], entry["lesson"]),
                         ("acme-billing", "reject", "cut list: one-impl interface", "a.go:12 kept for plugins", ""))

    def test_slug_from_remote_or_directory(self):
        cases = [
            (self.make_repo("a", "git@github.com:o/r.git"), "o-r"),
            (self.make_repo("b", "https://github.com/o/r"), "o-r"),
            (self.make_repo("plain"), "plain"),
        ]
        sub = cases[2][0] / "pkg" / "inner"
        sub.mkdir(parents=True)
        cases.append((sub, "plain"))
        for cwd, slug in cases:
            with self.subTest(cwd=cwd.name):
                self.signal("accept", cwd=cwd)
                self.assertEqual(self.lines("signals.jsonl")[-1]["repo"], slug)

    def test_evidence_first_line_capped(self):
        self.signal("reject", evidence="a.go:1 kept\n```\nAPI_KEY=abc\n```")
        self.signal("reject", evidence="y" * 500)
        first, second = self.lines("signals.jsonl")
        self.assertEqual(first["evidence"], "a.go:1 kept")
        self.assertEqual(second["evidence"], "y" * 200)

    def test_lesson_written_and_committed(self):
        lesson = "Keep the Formatter interface: the enterprise build adds a second implementation"
        self.assertEqual(self.signal("reject", lesson).returncode, 0)
        self.assertEqual(self.lesson_file.read_text(), f"- {lesson}. ({TODAY}, seen 1x)\n")
        subject = subprocess.run(["git", "-C", str(self.lesson_file.parent), "log", "-1", "--format=%s"],
                                 capture_output=True, text=True, env=self.env).stdout.strip()
        self.assertEqual(subject, f"lesson(acme-billing): {lesson}")
        self.assertNotIn("a.go:12", self.lesson_file.read_text())

    def test_same_lesson_bumps_count(self):
        self.signal("reject", "Keep the Formatter interface")
        self.signal("revert", "keep the formatter interface.")
        self.assertEqual(self.lesson_file.read_text(), f"- Keep the Formatter interface. ({TODAY}, seen 2x)\n")

    def test_accept_never_writes_lesson(self):
        self.signal("accept", "Keep the Formatter interface")
        self.assertFalse(self.lesson_file.exists())
        self.assertEqual(self.lines("signals.jsonl")[0]["kind"], "accept")

    def test_never_cut_flag_not_applied(self):
        result = self.signal("reject", "Skip the nil check on repo", "--flag", "never-cut")
        self.assertFalse(self.lesson_file.exists())
        self.assertEqual(self.lines("signals.jsonl")[0]["flag"], "never-cut")
        self.assertIn("not applied", result.stdout)

    def test_weakening_lesson_auto_flagged(self):
        for lesson in ["Drop the tenant re-checks in services", "Remove the ownership check in getInvoice",
                       "skip the rollback on Void", "Cut the already-voided state guard",
                       "The tenant re-check is redundant here"]:
            with self.subTest(lesson=lesson):
                result = self.signal("reject", lesson)
                self.assertEqual(self.lines("signals.jsonl")[-1].get("flag"), "never-cut")
                self.assertIn("not applied", result.stdout)
        self.assertFalse(self.lesson_file.exists())

    def test_strengthening_lesson_applied(self):
        lessons = ["Never remove the rollback in Void", "Keep the tenant re-check: it is not redundant",
                   "Don't drop the balance check"]
        for lesson in lessons:
            self.signal("restore", lesson)
        self.assertEqual(len(self.lesson_file.read_text().splitlines()), 3)
        self.assertNotIn("flag", self.lines("signals.jsonl")[-1])

    def test_fortieth_line_fills_the_file(self):
        self.lesson_file.parent.mkdir(parents=True)
        self.lesson_file.write_text("".join(f"- Lesson {i}. (2026-01-01, seen 1x)\n" for i in range(39)))
        result = self.signal("reject", "Lesson forty")
        self.assertEqual(len(self.lesson_file.read_text().splitlines()), 40)
        self.assertIn("full", result.stdout)

    def test_full_file_records_signal_only(self):
        self.lesson_file.parent.mkdir(parents=True)
        full = "".join(f"- Lesson {i}. (2026-01-01, seen 1x)\n" for i in range(40))
        self.lesson_file.write_text(full)
        result = self.signal("reject", "One more lesson")
        self.assertEqual(self.lesson_file.read_text(), full)
        self.assertEqual(len(self.lines("signals.jsonl")), 1)
        self.assertIn("full", result.stdout)

    def test_global_never_written(self):
        self.signal("reject", "Keep the Formatter interface")
        self.assertTrue(self.lesson_file.exists())
        self.assertEqual((self.root / "lessons" / "global.md").read_text(), "")


class LessonsTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = self.make_repo("billing", "https://github.com/acme/billing.git")
        self.repos = self.root / "lessons" / "repos"
        self.repos.mkdir()

    def test_prints_global_and_repo(self):
        (self.root / "lessons" / "global.md").write_text("- Global rule. (2026-01-01, seen 2x)\n")
        (self.repos / "acme-billing.md").write_text("- Repo rule. (2026-01-02, seen 1x)\n")
        out = self.run_capture("lessons", cwd=self.repo).stdout
        self.assertIn("- Global rule. (2026-01-01, seen 2x)", out)
        self.assertIn("- Repo rule. (2026-01-02, seen 1x)", out)

    def test_other_repo_not_printed(self):
        (self.repos / "acme-billing.md").write_text("- Mine.\n")
        (self.repos / "acme-web.md").write_text("- Other repo rule.\n")
        out = self.run_capture("lessons", cwd=self.repo).stdout
        self.assertIn("Mine", out)
        self.assertNotIn("Other repo rule", out)

    def test_empty_prints_nothing(self):
        result = self.run_capture("lessons", cwd=self.repo)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_pull_stamped_at_most_hourly(self):
        stamp = self.inbox / "last-pull"
        self.run_capture("lessons", cwd=self.repo)
        self.assertTrue(stamp.exists())
        recent = time.time() - 600
        os.utime(stamp, (recent, recent))
        self.run_capture("lessons", cwd=self.repo)
        self.assertAlmostEqual(stamp.stat().st_mtime, recent, delta=1)
        stale = time.time() - 7200
        os.utime(stamp, (stale, stale))
        self.run_capture("lessons", cwd=self.repo)
        self.assertGreater(stamp.stat().st_mtime, time.time() - 60)


class Step0Tests(Base):
    def setUp(self):
        super().setUp()
        self.env["HOME"] = str(self.tmp / "home")
        self.repo = self.make_repo("app")

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def step0(self, cwd=None):
        result = self.run_capture("step0", cwd=cwd or self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_card_lists_checks_lint_config_and_nested_docs(self):
        self.write("package.json", json.dumps({"scripts": {"lint": "eslint .", "test": "vitest", "dev": "vite"}}))
        self.write("pnpm-lock.yaml", "")
        self.write("Makefile", ".PHONY: test\ntest:\n\tgo test ./...\ndeploy:\n\t./deploy.sh\n")
        self.write(".github/workflows/ci.yml", "jobs:\n  a:\n    steps:\n      - run: go vet ./...\n"
                                               "      - run: |\n          make lint\n")
        self.write("eslint.config.js", "")
        self.write("src/billing/AGENTS.md", "# billing\n")
        out = self.step0()
        for line in ("- pnpm run lint: eslint .", "- pnpm run test: vitest", "- make test",
                     "- CI ci.yml: go vet ./...", "- CI ci.yml: make lint", "Lint config: eslint.config.js",
                     "Nested AGENTS.md and CLAUDE.md: src/billing/AGENTS.md"):
            self.assertIn(line, out)
        self.assertNotIn("run dev", out)
        self.assertNotIn("make deploy", out)

    def test_card_cached_until_a_root_file_changes(self):
        self.write("package.json", json.dumps({"scripts": {"lint": "eslint ."}}))
        self.step0()
        [cache] = (self.tmp / "home" / ".claude" / "shepherd" / "repo-cards").glob("*.json")
        cache.write_text(json.dumps({**json.loads(cache.read_text()), "text": "from cache"}))
        self.assertEqual(self.step0().strip(), "from cache")
        self.write("package.json", json.dumps({"scripts": {"lint": "eslint .", "test": "vitest run"}}))
        self.assertIn("vitest run", self.step0())

    def test_root_agents_md_not_imported_is_named(self):
        self.write("AGENTS.md", "# rules\n")
        self.write("CLAUDE.md", "# notes\n")
        self.assertIn("Root AGENTS.md is not loaded", self.step0())
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.assertNotIn("Root AGENTS.md is not loaded", self.step0())

    def test_outside_a_repo(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertIn("not a git repo", self.step0(cwd=plain))

    def test_lessons_follow_the_card(self):
        (self.root / "lessons" / "global.md").write_text("- Global rule. (2026-01-01, seen 2x)\n")
        out = self.step0()
        self.assertLess(out.index("Repo card"), out.index("- Global rule."))


class HookCommandTests(Base):
    """Runs the frontmatter hook commands the way Claude Code does: sh -c, JSON on stdin."""

    def setUp(self):
        super().setUp()
        (self.root / "hooks").mkdir()
        shutil.copy(CAPTURE, self.root / "hooks" / "capture.py")
        self.env.pop("CLAUDE_PLUGIN_ROOT", None)
        # A real interpreter first on PATH: version-manager shims break under a different HOME.
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "python3").symlink_to(sys.executable)
        self.env["PATH"] = f"{self.tmp / 'bin'}{os.pathsep}{self.env['PATH']}"
        self.commands = hook_commands()

    def run_hook(self, event, payload, **env):
        return subprocess.run(["sh", "-c", self.commands[event]], input=json.dumps(payload),
                              capture_output=True, text=True, env={**self.env, **env})

    def test_prompt_and_reply_recorded(self):
        self.assertEqual(set(self.commands), {"UserPromptSubmit", "Stop"})
        self.run_hook("UserPromptSubmit", {"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit",
                                           "prompt": "fix it"}, CLAUDE_PLUGIN_ROOT=str(self.root))
        self.run_hook("Stop", {"session_id": "s", "cwd": "/", "hook_event_name": "Stop",
                               "last_assistant_message": "fixed"}, CLAUDE_PLUGIN_ROOT=str(self.root))
        self.assertEqual([e["text"] for e in self.lines("turns.jsonl")], ["fix it", "fixed"])

    def test_falls_back_to_installed_skill(self):
        home = self.tmp / "home"
        (home / ".claude" / "skills").mkdir(parents=True)
        (home / ".claude" / "skills" / "shepherd").symlink_to(self.root)
        self.run_hook("Stop", {"session_id": "s", "cwd": "/", "hook_event_name": "Stop",
                               "last_assistant_message": "fixed"}, HOME=str(home))
        self.assertEqual(len(self.lines("turns.jsonl")), 1)

    def test_missing_script_never_blocks_the_prompt(self):
        result = self.run_hook("UserPromptSubmit", {"hook_event_name": "UserPromptSubmit", "prompt": "x"},
                               CLAUDE_PLUGIN_ROOT=str(self.tmp / "missing"))
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
