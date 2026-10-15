import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "write_hooks.py"
REPORT = ("Rung: 2\nChanged: a.py - x\nLean: nothing cut\nFixed alongside: none\n"
          "Follow-ups: none\nNot checked: none")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

    def hook(self, name, data):
        stdin = data if isinstance(data, str) else json.dumps(data)
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        return subprocess.run([sys.executable, str(SCRIPT), name], input=stdin,
                              capture_output=True, text=True, env=env)


# Prompts and commits are this far in the past. A block's "at" is seconds from the stop.
PROMPT = 100
OLD = 1000


def stamp(when):
    return datetime.fromtimestamp(when, timezone.utc).isoformat().replace("+00:00", "Z")


def bash(command, at=10):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}, "at": at}


def refine(at=10):
    return {"type": "tool_use", "name": "Agent", "at": at,
            "input": {"model": "haiku", "prompt": "Refine pass. Do not edit files."}}


def say(text):
    return {"type": "text", "text": text, "at": 20}


class StopTests(Base):
    def setUp(self):
        super().setUp()
        self.transcript = self.tmp / "session.jsonl"
        self.data = {"session_id": "s1", "transcript_path": str(self.transcript), "cwd": str(self.repo),
                     "prompt_id": "p2", "stop_hook_active": False, "last_assistant_message": ""}
        self.commit({"a.py": "x = 1\n"})

    def commit(self, files):
        for name, text in files.items():
            (self.repo / name).write_text(text)
            os.utime(self.repo / name, (time.time() - OLD, time.time() - OLD))
        old = f"@{int(time.time() - OLD)}"
        env = dict(os.environ, GIT_AUTHOR_DATE=old, GIT_COMMITTER_DATE=old)
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "base"], check=True, env=env)

    def write(self, name, lines=1):
        (self.repo / name).write_text("y = 2\n" * lines)

    def stop(self, *blocks, earlier=()):
        now, entries = time.time(), []
        for prompt_id, ago, turn in (("p1", OLD, earlier), ("p2", PROMPT, blocks)):
            entries.append({"type": "user", "promptId": prompt_id, "timestamp": stamp(now - ago),
                            "message": {"content": "do it"}})
            for block in turn:
                at = block.pop("at")
                entries.append({"type": "assistant", "timestamp": stamp(now + at),
                                "message": {"content": [block]}})
        self.transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))
        result = self.hook("stop", self.data)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        return json.loads(result.stdout) if result.stdout else None

    def test_no_write_silent(self):
        self.assertIsNone(self.stop(bash("git status"), say("All good.")))

    def test_write_without_report_blocks(self):
        self.write("a.py")
        result = self.stop(say("Done."))
        self.assertEqual(result["decision"], "block")
        self.assertIn("code/write.md", result["reason"])
        self.assertIn("Rung, Changed, Lean, Fixed alongside, Follow-ups, Not checked", result["reason"])
        self.assertNotIn("Run these checks", result["reason"])
        self.assertNotIn("refine", result["reason"])

    def test_write_with_report_silent(self):
        self.write("a.py")
        self.assertIsNone(self.stop(say(REPORT)))

    def test_committed_write_counts(self):
        self.write("b.py")
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "turn"], check=True)
        self.assertEqual(self.stop(say("Done."))["decision"], "block")

    def test_file_from_before_the_prompt_ignored(self):
        self.write("b.py", 40)
        os.utime(self.repo / "b.py", (time.time() - PROMPT - 10, time.time() - PROMPT - 10))
        self.assertIsNone(self.stop(say("Hi.")))

    def test_bold_labels_count(self):
        self.write("a.py")
        bold = REPORT.replace("Rung:", "**Rung:**").replace("Lean:", "**Lean**:")
        self.assertIsNone(self.stop(say(bold)))

    def test_report_in_last_message_counts(self):
        self.write("a.py")
        self.data["last_assistant_message"] = REPORT
        self.assertIsNone(self.stop())

    def test_names_missing_lines_only(self):
        self.write("a.py")
        result = self.stop(say(REPORT.replace("Not checked: none", "")))
        self.assertIn("These lines are missing: Not checked.", result["reason"])

    def test_big_write_needs_refine_pass(self):
        self.write("b.py", 30)
        result = self.stop(say(REPORT))
        self.assertIn("Do the refine pass of step 1.", result["reason"])
        self.assertNotIn("missing", result["reason"])
        self.assertIsNone(self.stop(refine(), say(REPORT)))

    def test_refine_before_writes_does_not_count(self):
        self.write("b.py", 30)
        self.assertIn("refine pass", self.stop(refine(at=-50), say(REPORT))["reason"])

    def test_added_lines_of_tracked_file(self):
        self.write("a.py", 15)
        self.assertIsNone(self.stop(say(REPORT)))
        self.write("a.py", 25)
        self.assertIn("refine pass", self.stop(say(REPORT))["reason"])

    def test_go_check_must_follow_last_write(self):
        self.commit({"go.mod": "module x\n"})
        self.write("a.go")
        result = self.stop(bash("go vet ./...", at=-50), say(REPORT))
        self.assertEqual(result["decision"], "block")
        self.assertIn("Run these checks after your last edit: go vet ./....", result["reason"])
        self.assertNotIn("missing", result["reason"])
        self.assertIsNone(self.stop(bash("go build ./... && go vet ./..."), say(REPORT)))

    def test_package_scripts(self):
        self.commit({"package.json": json.dumps({"scripts": {"lint": "eslint .", "test": "vitest",
                                                             "build": "vite build"}}),
                     "pnpm-lock.yaml": ""})
        self.write("a.ts")
        result = self.stop(bash("pnpm lint"), bash("pnpm test", at=-50), say(REPORT))
        self.assertIn("Run these checks after your last edit: pnpm run test.", result["reason"])
        self.assertIsNone(self.stop(bash("pnpm lint && pnpm test -- a"), say(REPORT)))

    def test_stop_hook_active_silent(self):
        self.write("a.py")
        self.data["stop_hook_active"] = True
        self.assertIsNone(self.stop(say("Done.")))

    def test_write_outside_repo_silent(self):
        (self.tmp / "notes.md").write_text("x\n")
        self.assertIsNone(self.stop(say("Done.")))

    def test_not_a_repo_silent(self):
        self.write("a.py")
        self.data["cwd"] = str(self.tmp)
        self.assertIsNone(self.stop(say("Done.")))


class LintTests(Base):
    def setUp(self):
        super().setUp()
        self.file = self.repo / "a.py"
        self.file.write_text("x = 1\n" * 6)
        (self.repo / "ruff.toml").write_text("")

    def fake(self, name, stdout="", stderr="", folder=None):
        path = (folder or self.bin) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!/bin/sh\nprintf '%s' '{stdout}'\nprintf '%s' '{stderr}' >&2\n")
        path.chmod(0o755)

    def lint(self, path=None, edited=(2,)):
        response = {"type": "create", "structuredPatch": []} if edited is None else {
            "type": "update",
            "structuredPatch": [{"newStart": n, "newLines": 1, "lines": ["-old", "+new"]} for n in edited]}
        data = {"tool_name": "Edit", "tool_input": {"file_path": str(path or self.file)},
                "tool_response": response}
        result = self.hook("lint", data)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] if result.stdout else None

    def test_ruff_edited_lines_first(self):
        self.fake("ruff", "a.py:5:1: E501 long\na.py:2:1: F401 unused\nb.py:2:1: F401 other\n")
        self.assertEqual(self.lint(), "ruff findings in a.py after this edit:\na.py:2:1: F401 unused\n"
                         "Outside the edited lines (fix only the ones that this edit caused):\n"
                         "a.py:5:1: E501 long")

    def test_new_file_all_edited(self):
        self.fake("ruff", "a.py:5:1: E501 long\n")
        self.assertEqual(self.lint(edited=None), "ruff findings in a.py after this edit:\na.py:5:1: E501 long")

    def test_clean_file_silent(self):
        self.fake("ruff")
        self.assertIsNone(self.lint())

    def test_no_config_silent(self):
        (self.repo / "ruff.toml").unlink()
        self.fake("ruff", "a.py:2:1: F401 unused\n")
        self.assertIsNone(self.lint())

    def test_config_in_pyproject(self):
        (self.repo / "ruff.toml").unlink()
        (self.repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        self.fake("ruff", "a.py:2:1: F401 unused\n")
        self.assertIn("a.py:2:1: F401 unused", self.lint())

    def test_eslint_json(self):
        web = self.repo / "web"
        (web / "a.ts").parent.mkdir()
        (web / "a.ts").write_text("let x = 1\n")
        (web / "eslint.config.js").write_text("")
        report = [{"filePath": str(web / "a.ts"), "messages": [
            {"line": 1, "column": 5, "message": "x is unused", "ruleId": "no-unused-vars"}]}]
        self.fake("eslint", json.dumps(report), folder=self.repo / "node_modules" / ".bin")
        self.assertEqual(self.lint(web / "a.ts", edited=(1,)),
                         "eslint findings in a.ts after this edit:\na.ts:1:5: x is unused (no-unused-vars)")

    def test_go_vet(self):
        (self.repo / "a.go").write_text("package a\n")
        self.fake("go", stderr="# example.com/a\n./a.go:1:9: fmt.Printf format %d has arg x\n")
        self.assertEqual(self.lint(self.repo / "a.go", edited=(1,)),
                         "go vet findings in a.go after this edit:\n./a.go:1:9: fmt.Printf format %d has arg x")

    def test_go_vet_skips_type_errors(self):
        (self.repo / "a.go").write_text("package a\n")
        self.fake("go", stderr="# example.com/a\nvet: ./a.go:1:9: undefined: y\n")
        self.assertIsNone(self.lint(self.repo / "a.go", edited=(1,)))

    def test_cap(self):
        self.fake("ruff", "".join(f"a.py:2:{n}: F401 unused\n" for n in range(30)))
        lines = self.lint().splitlines()
        self.assertEqual(len(lines), 21)
        self.assertEqual(lines[-1], "(11 more lines)")


class FailOpenTests(Base):
    def test_malformed_stdin_exit0(self):
        for name in ("stop", "lint"):
            for stdin in ("", "not json", "[1, 2]", '{"cwd": 5}', '{"tool_input": {}}'):
                result = self.hook(name, stdin)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""),
                                 (name, stdin))


if __name__ == "__main__":
    unittest.main()
