import json
import shutil
import subprocess
import sys
import tempfile
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


class FailOpenTests(Base):
    def test_malformed_stdin_exit0(self):
        for name in ("warn",):
            for stdin in ("", "not json", "[1, 2]", '{"session_id": 5}'):
                result = self.hook(name, stdin)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""),
                                 (name, stdin))


if __name__ == "__main__":
    unittest.main()
