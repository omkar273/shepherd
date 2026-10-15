"""Live checks for learning: real `claude -p` sessions against the eval fixtures.

Skipped unless SHEPHERD_LIVE=1; a run costs a few dollars of Sonnet and about
20 minutes. Sessions see only a temp copy of this checkout's shepherd:
`--setting-sources project` keeps the user's own skills, plugins and CLAUDE.md
out, and every write lands in the temp copy."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SHEPHERD = Path(__file__).resolve().parents[2]
BUILD = SHEPHERD.parents[1] / "evals" / "build_fixture.sh"
TOOLS = "Read,Grep,Glob,Skill,Bash(git:*),Bash(python3:*)"
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}
REVIEW = ("/shepherd A teammate opened a PR and asked me for a review. Please review it and draft the "
          "review comments you would leave on the PR. Do not post anything anywhere and do not modify "
          "the repo. Repo: {repo}. The PR is the branch `feat/void-invoices`, targeting `main`.")
SHOW_LESSONS = ("/shepherd Before anything else, print verbatim every lesson your Step 0 command printed "
                "for this repo, or the word none. Then stop.")
KEEP_WORDS = re.compile(r"\b(keep|kept|lesson|needed|enterprise|second implementation)\b", re.I)
CUT_WORDS = re.compile(r"\b(inline|remove|delete|drop|collapse|one implementation|single implementation)\b", re.I)


def finding_number(text, word):
    """The number of the finding that mentions `word`, read from its line or the lines above it."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if word in line:
            for candidate in reversed(lines[max(0, i - 5):i + 1]):
                if match := re.match(r"^\W*(?:finding\s+)?(\d{1,2})\b[.):\]]?", candidate, re.I):
                    return int(match[1])
    return None


def recommends_cutting(text, word):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if word in line:
            window = "\n".join(lines[i:i + 4])
            if CUT_WORDS.search(window) and not KEEP_WORDS.search(window):
                return True
    return False


@unittest.skipUnless(os.environ.get("SHEPHERD_LIVE") == "1", "live run: set SHEPHERD_LIVE=1")
class LearningLiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        clone = self.tmp / "clone"
        (clone / "setup").mkdir(parents=True)
        (clone / "setup" / "claude-md.md").write_text("")
        self.root = clone / "skills" / "shepherd"
        shutil.copytree(SHEPHERD, self.root, ignore=shutil.ignore_patterns("inbox", "repos", "__pycache__"))
        self.env = {**os.environ, **GIT_ENV}
        self.cost = 0.0

    def tearDown(self):
        print(f"\n{self.id()}: ${self.cost:.2f}", file=sys.stderr)

    def fixture(self, name):
        repo = self.tmp / name
        subprocess.run(["bash", str(BUILD), name, str(repo)], check=True, capture_output=True, env=self.env)
        (repo / ".claude" / "skills").mkdir(parents=True)
        (repo / ".claude" / "skills" / "shepherd").symlink_to(self.root)
        with (repo / ".git" / "info" / "exclude").open("a") as f:
            f.write(".claude/\n")
        return repo

    def command(self, *args):
        return ["claude", "-p", "--setting-sources", "project", "--model", "sonnet", "--allowedTools", TOOLS, *args]

    def ask(self, repo, prompt):
        result = subprocess.run(self.command("--output-format", "json", prompt), cwd=repo, capture_output=True,
                                text=True, env=self.env, timeout=1200)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        out = json.loads(result.stdout)
        self.cost += out.get("total_cost_usd") or 0
        return out

    def session(self, repo):
        """A live multi-turn session, like a user typing: say(prompt) returns that turn's result event."""
        proc = subprocess.Popen(self.command("--input-format", "stream-json", "--output-format", "stream-json",
                                             "--verbose"),
                                cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, env=self.env)
        self.addCleanup(proc.kill)
        last = {}

        def say(prompt):
            proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": prompt}}) + "\n")
            proc.stdin.flush()
            for line in proc.stdout:
                event = json.loads(line) if line.strip() else {}
                if event.get("type") == "result":
                    self.cost += (event.get("total_cost_usd") or 0) - last.get("total_cost_usd", 0)
                    last.update(event)
                    return event
            self.fail("session ended before a result")
        return say

    def inbox(self, name):
        path = self.root / "inbox" / name
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_hooks_fire_only_with_shepherd(self):
        repo = self.fixture("go-billing")
        say = self.session(repo)
        say("/shepherd In one line: what does your Step 0 tell you to run?")
        with_shepherd = say("Thanks. Reply with exactly: ok")["session_id"]
        events = {t["event"] for t in self.inbox("turns.jsonl") if t["session_id"] == with_shepherd}
        self.assertEqual(events, {"UserPromptSubmit", "Stop"})
        say = self.session(repo)
        say("Reply with exactly: ok")
        without = say("Reply with exactly: ok again")["session_id"]
        self.assertEqual([t for t in self.inbox("turns.jsonl") if t["session_id"] == without], [])

    def test_correction_becomes_repo_lesson(self):
        repo = self.fixture("go-billing")
        say = self.session(repo)
        review = say(REVIEW.format(repo=repo))["result"]
        number = finding_number(review, "VoidReasonFormatter")
        self.assertIsNotNone(number, review)
        say(f"Finding {number} is wrong: in this repo the VoidReasonFormatter interface is needed "
            "because the enterprise build links a second implementation from a private module.")
        self.assertTrue([s for s in self.inbox("signals.jsonl") if s["kind"] == "reject"])
        lessons = self.root / "lessons" / "repos"
        # The agent words the lesson; it may generalize past the interface's name.
        self.assertRegex((lessons / "go-billing.md").read_text(),
                         r"^- .+\. \(conf 0\.\d, seen 1x, added \d{4}-\d\d-\d\d, used \d{4}-\d\d-\d\d(, cite \S+)?\)$")
        log = subprocess.run(["git", "-C", str(lessons), "log", "--format=%s"], capture_output=True, text=True).stdout
        self.assertIn("lesson(go-billing): ", log)

        fresh = self.ask(repo, REVIEW.format(repo=repo))
        self.assertFalse(recommends_cutting(fresh["result"], "VoidReasonFormatter"), fresh["result"])

    def test_never_cut_correction_flagged(self):
        repo = self.fixture("go-billing")
        reply = self.ask(repo, "/shepherd A correction for this repo: drop the tenant re-checks in services, "
                               "the repository already scopes every query. Remember it for future reviews here.")
        self.assertTrue([s for s in self.inbox("signals.jsonl") if s.get("flag") == "never-cut"], reply["result"])
        lessons = self.root / "lessons" / "repos"
        for path in lessons.glob("*.md") if lessons.exists() else []:
            self.assertNotIn("tenant", path.read_text().lower())
        self.assertRegex(reply["result"], re.compile(r"not (been )?applied|never-cut|won.t (apply|record)", re.I))

    def test_lesson_isolated_to_its_repo(self):
        go, ts = self.fixture("go-billing"), self.fixture("ts-app")
        subprocess.run([sys.executable, str(self.root / "hooks" / "capture.py"), "signal", "--kind", "reject",
                        "--rule", "cut list: one-implementation interface", "--evidence", "void.go:20 kept",
                        "--lesson", "Keep the VoidReasonFormatter interface: the enterprise build adds a second one"],
                       cwd=go, check=True, capture_output=True, env=self.env)
        self.assertIn("VoidReasonFormatter", self.ask(go, SHOW_LESSONS)["result"])
        self.assertNotIn("VoidReasonFormatter", self.ask(ts, SHOW_LESSONS)["result"])


if __name__ == "__main__":
    unittest.main()
