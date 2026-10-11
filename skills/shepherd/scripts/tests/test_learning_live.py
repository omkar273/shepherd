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

    def claude(self, repo, *args, stdin=None):
        result = subprocess.run(
            ["claude", "-p", "--setting-sources", "project", "--model", "sonnet", "--allowedTools", TOOLS, *args],
            cwd=repo, input=stdin, capture_output=True, text=True, env=self.env, timeout=1200,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        return result.stdout

    def ask(self, repo, prompt, resume=None):
        out = json.loads(self.claude(repo, *(["--resume", resume] if resume else []), "--output-format", "json", prompt))
        self.cost += out.get("total_cost_usd") or 0
        return out

    def converse(self, repo, prompts):
        """One session, several user turns; returns its session id."""
        stdin = "".join(json.dumps({"type": "user", "message": {"role": "user", "content": p}}) + "\n" for p in prompts)
        events = [json.loads(l) for l in self.claude(repo, "--input-format", "stream-json", "--output-format",
                                                      "stream-json", "--verbose", stdin=stdin).splitlines() if l.strip()]
        self.cost += sum(e.get("total_cost_usd") or 0 for e in events if e.get("type") == "result")
        return next(e["session_id"] for e in events if e.get("session_id"))

    def inbox(self, name):
        path = self.root / "inbox" / name
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_hooks_fire_only_with_shepherd(self):
        repo = self.fixture("go-billing")
        with_shepherd = self.converse(repo, ["/shepherd In one line: what does your Step 0 tell you to run?",
                                             "Thanks. Reply with exactly: ok"])
        events = {t["event"] for t in self.inbox("turns.jsonl") if t["session_id"] == with_shepherd}
        self.assertEqual(events, {"UserPromptSubmit", "Stop"})
        without = self.converse(repo, ["Reply with exactly: ok", "Reply with exactly: ok again"])
        self.assertEqual([t for t in self.inbox("turns.jsonl") if t["session_id"] == without], [])

    def test_correction_becomes_repo_lesson(self):
        repo = self.fixture("go-billing")
        review = self.ask(repo, REVIEW.format(repo=repo))
        number = finding_number(review["result"], "VoidReasonFormatter")
        self.assertIsNotNone(number, review["result"])
        self.ask(repo, f"Finding {number} is wrong: in this repo the VoidReasonFormatter interface is needed "
                       "because the enterprise build links a second implementation from a private module.",
                 resume=review["session_id"])
        self.assertTrue([s for s in self.inbox("signals.jsonl") if s["kind"] == "reject"])
        lessons = self.root / "lessons" / "repos"
        self.assertIn("VoidReasonFormatter", (lessons / "go-billing.md").read_text())
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
