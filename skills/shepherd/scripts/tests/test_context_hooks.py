import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "context_hooks.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hooks"
WARNING = ("Context is at {}k. If this is a new task, start a fresh session; "
           "otherwise `/compact` at the next task boundary.")


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.logs = self.home / ".claude" / "shepherd" / "logs"

    def hook(self, name, data):
        stdin = data if isinstance(data, str) else json.dumps(data)
        return subprocess.run([sys.executable, str(SCRIPT), name, "--home", str(self.home)],
                              input=stdin, capture_output=True, text=True)


class WarnTests(Base):
    def setUp(self):
        super().setUp()
        self.transcript = self.home / "session.jsonl"
        self.data = fixture("user_prompt_submit")
        self.data["transcript_path"] = str(self.transcript)

    def write_transcript(self, tokens, sidechain_tokens=None):
        entries = [{"type": "user", "message": {"role": "user", "content": "hi"}},
                   self.assistant(tokens, False)]
        if sidechain_tokens:
            entries.append(self.assistant(sidechain_tokens, True))
        self.transcript.write_text("".join(json.dumps(e) + "\n" for e in entries))

    @staticmethod
    def assistant(tokens, sidechain):
        usage = {"input_tokens": 2, "cache_creation_input_tokens": 1000,
                 "cache_read_input_tokens": tokens - 1002, "output_tokens": 50}
        return {"type": "assistant", "isSidechain": sidechain,
                "message": {"role": "assistant", "usage": usage, "content": []}}

    def warn(self, tokens):
        self.write_transcript(tokens)
        return self.hook("warn", self.data)

    def test_warn_silent_below_200k(self):
        result = self.warn(150_000)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_warn_once_past_200k(self):
        output = json.loads(self.warn(250_000).stdout)
        line = WARNING.format(250)
        self.assertEqual(output["systemMessage"], line)
        self.assertEqual(output["hookSpecificOutput"],
                         {"hookEventName": "UserPromptSubmit", "additionalContext": line})
        self.assertEqual(self.warn(260_000).stdout, "")

    def test_warn_again_past_400k(self):
        self.warn(250_000)
        output = json.loads(self.warn(410_000).stdout)
        self.assertEqual(output["systemMessage"], WARNING.format(410))
        self.assertEqual(self.warn(420_000).stdout, "")

    def test_warn_ignores_sidechain(self):
        self.write_transcript(150_000, sidechain_tokens=300_000)
        result = self.hook("warn", self.data)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_warn_missing_transcript_exit0(self):
        result = self.hook("warn", self.data)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_bad_session_id_noop(self):
        self.data["session_id"] = "../x"
        result = self.warn(250_000)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse((self.home / ".claude").exists())


class TrimTests(Base):
    def setUp(self):
        super().setUp()
        self.data = fixture("post_tool_use_bash")
        self.session_logs = self.logs / self.data["session_id"]

    def trim(self, stdout="", stderr="", command="make test", **response):
        self.data["tool_input"]["command"] = command
        self.data["tool_response"].update(stdout=stdout, stderr=stderr, **response)
        return self.hook("trim", self.data)

    @staticmethod
    def numbered(count):
        return [f"line {i}" for i in range(1, count + 1)]

    def test_trim_under_limit_silent(self):
        result = self.trim("\n".join(self.numbered(150)))
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.logs.exists())

    def test_trim_over_limit(self):
        lines = self.numbered(1000)
        output = json.loads(self.trim("\n".join(lines)).stdout)["hookSpecificOutput"]
        log = self.session_logs / "1.log"
        self.assertEqual(output["hookEventName"], "PostToolUse")
        replaced = output["updatedToolOutput"]
        self.assertEqual(replaced["stdout"].splitlines(),
                         lines[:60] + [f"[880 lines trimmed; full log: {log}]"] + lines[-60:])
        expected = dict(self.data["tool_response"], stdout=replaced["stdout"])
        self.assertEqual(replaced, expected)
        self.assertEqual(log.read_text().splitlines(), lines)

    def test_trim_stderr(self):
        lines = self.numbered(300)
        replaced = json.loads(self.trim("ok", "\n".join(lines)).stdout)[
            "hookSpecificOutput"]["updatedToolOutput"]
        self.assertEqual(replaced["stdout"], "ok")
        self.assertEqual(len(replaced["stderr"].splitlines()), 121)
        self.assertIn("[180 lines trimmed;", replaced["stderr"])
        self.assertEqual((self.session_logs / "1.log").read_text().splitlines(),
                         ["ok", "[stderr]"] + lines)

    def test_trim_full_exempt(self):
        result = self.trim("\n".join(self.numbered(1000)), command="make test  # full")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_trim_skips_persisted_output(self):
        result = self.trim("\n".join(self.numbered(1000)),
                           persistedOutputPath="/tmp/out.txt", persistedOutputSize=90000)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_trim_second_log_is_2(self):
        self.trim("\n".join(self.numbered(300)))
        self.trim("\n".join(self.numbered(300)))
        self.assertEqual(sorted(p.name for p in self.session_logs.iterdir()), ["1.log", "2.log"])

    def test_trim_prunes_old_session_dirs(self):
        old, recent = self.logs / "old-session", self.logs / "recent-session"
        for path, days in ((old, 8), (recent, 1)):
            path.mkdir(parents=True)
            stamp = time.time() - days * 86400
            os.utime(path, (stamp, stamp))
        self.trim("\n".join(self.numbered(300)))
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())


class FailOpenTests(Base):
    def test_malformed_stdin_exit0(self):
        for name in ("warn", "trim"):
            for stdin in ("", "not json", "[1, 2]", '{"session_id": 5}'):
                result = self.hook(name, stdin)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""),
                                 (name, stdin))


if __name__ == "__main__":
    unittest.main()
