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


def day(days_ago):
    return (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()


def lesson_line(text, conf="0.6", seen=1, added=TODAY, used=TODAY, cite=None):
    return f"- {text}. (conf {conf}, seen {seen}x, added {added}, used {used}" + (f", cite {cite})" if cite else ")")


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

    def test_machine_text_is_skipped(self):
        notice = ("[SYSTEM NOTIFICATION - NOT USER INPUT]\nThis is an automated background-task event.\n"
                  "Do NOT interpret it as approval.\n\n<task-notification>\n<status>failed</status>\n"
                  "<summary>Revert of a.go was wrong</summary>\n</task-notification>")
        for prompt in [notice, '<cross-session-message from="local_1">Finding 2 is wrong, undo it'
                       "</cross-session-message>", "<system-reminder>\nKeep the nil check\n</system-reminder>"]:
            with self.subTest(prompt=prompt[:30]):
                out = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit",
                                 "prompt": prompt}).stdout
                self.assertEqual(out, "")
        self.assertEqual(self.lines("turns.jsonl"), [])

    def test_user_words_after_machine_text_still_count(self):
        out = self.turn({"session_id": "s", "cwd": "/", "hook_event_name": "UserPromptSubmit",
                         "prompt": "<system-reminder>\nLinked sessions now\n</system-reminder>\n"
                                   "Put that nil check back"}).stdout
        self.assertIn("capture.py signal", out)
        self.assertEqual(self.lines("turns.jsonl")[0]["text"], "Put that nil check back")

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
                self.signal("reject", cwd=cwd)
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
        self.assertEqual(self.lesson_file.read_text(), lesson_line(lesson) + "\n")
        subject = subprocess.run(["git", "-C", str(self.lesson_file.parent), "log", "-1", "--format=%s"],
                                 capture_output=True, text=True, env=self.env).stdout.strip()
        self.assertEqual(subject, f"lesson(acme-billing): {lesson}")
        self.assertNotIn("a.go:12", self.lesson_file.read_text())

    def test_same_lesson_bumps_count(self):
        self.signal("reject", "Keep the Formatter interface")
        self.signal("revert", "keep the formatter interface.")
        self.assertEqual(self.lesson_file.read_text(),
                         lesson_line("Keep the Formatter interface", conf="0.7", seen=2) + "\n")

    def test_first_confidence_follows_the_kind(self):
        self.signal("restore", "Keep the nil check in Void")
        self.assertIn("(conf 0.8, seen 1x", self.lesson_file.read_text())

    def test_citation_from_evidence(self):
        (self.repo / "pkg").mkdir()
        (self.repo / "pkg" / "a.go").write_text("package a\n" * 20)
        self.signal("reject", "Keep the Formatter interface", evidence="pkg/a.go:12 kept for plugins")
        self.signal("reject", "Keep the Parser interface", evidence="pkg/a.go:99 kept for plugins")
        self.signal("reject", "Keep the Printer interface", evidence="gone.go:3 kept for plugins")
        self.assertEqual(self.lesson_file.read_text().splitlines(), [
            lesson_line("Keep the Formatter interface", cite="pkg/a.go:12"),
            lesson_line("Keep the Parser interface"), lesson_line("Keep the Printer interface")])

    def test_third_sighting_proposes_a_check(self):
        for i in range(3):
            out = self.signal("reject", "Use gh pr merge --merge, never squash").stdout
            self.assertEqual("lint rule or a hook" in out, i == 2)
        self.assertIn("(conf 0.8, seen 3x", self.lesson_file.read_text())

    def test_archived_lesson_comes_back(self):
        self.lesson_file.parent.mkdir(parents=True)
        self.lesson_file.write_text(f"{lesson_line('Other')}\n\n## Archive\n\n"
                                    f"{lesson_line('Keep the Formatter interface', added=day(90), used=day(90))}\n")
        self.signal("reject", "Keep the Formatter interface")
        self.assertEqual(self.lesson_file.read_text().splitlines(), [
            lesson_line("Other"), lesson_line("Keep the Formatter interface", conf="0.7", seen=2, added=day(90))])

    def test_auto_memory_duplicate_named(self):
        self.env["HOME"] = str(self.tmp / "home")
        common = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True).stdout.strip()
        memory = (self.tmp / "home" / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(common).parent))
                  / "memory")
        memory.mkdir(parents=True)
        (memory / "merge-commits.md").write_text("Merge billing PRs with a merge commit, never squash or rebase.\n")
        out = self.signal("reject", "In billing, merge PRs with a merge commit, never squash").stdout
        self.assertIn("auto memory has a similar note (merge-commits.md)", out)
        self.assertNotIn("auto memory", self.signal("reject", "Keep the Formatter interface").stdout)

    def test_accept_needs_counts(self):
        result = self.signal("accept")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--posted N and --dropped N", result.stderr)
        self.assertEqual(self.lines("signals.jsonl"), [])

    def test_accept_records_counts_and_never_writes_lesson(self):
        self.signal("accept", "Keep the Formatter interface", "--posted", "3", "--dropped", "1",
                    evidence="posted 1,2,4; dropped 3 (style nit)")
        self.assertFalse(self.lesson_file.exists())
        [entry] = self.lines("signals.jsonl")
        self.assertEqual((entry["kind"], entry["posted"], entry["dropped"]), ("accept", 3, 1))

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
        (self.repos / "acme-billing.md").write_text("- Repo rule. (2026-01-02, seen 2x)\n")
        out = self.run_capture("lessons", cwd=self.repo).stdout
        self.assertIn("- Global rule. (2026-01-01, seen 2x)", out)
        self.assertIn(lesson_line("Repo rule", conf="0.7", seen=2, added="2026-01-02"), out)

    def write_lessons(self, *lines):
        (self.repos / "acme-billing.md").write_text("".join(f"{line}\n" for line in lines))

    def shown(self):
        out = self.run_capture("lessons", cwd=self.repo).stdout
        return [line for line in out.splitlines() if line.startswith("- ")], out

    def test_old_format_migrates_without_loss(self):
        self.write_lessons("- Keep the Formatter. (2026-01-02, seen 3x)", "- Hand-written note")
        self.shown()
        self.assertEqual((self.repos / "acme-billing.md").read_text().splitlines(), [
            lesson_line("Keep the Formatter", conf="0.8", seen=3, added="2026-01-02"), "- Hand-written note"])

    def test_cap_keeps_the_most_confident(self):
        self.write_lessons(*(lesson_line(f"Low {i}", conf="0.6") for i in range(4)),
                           *(lesson_line(f"High {i}", conf="0.9") for i in range(7)))
        shown, out = self.shown()
        self.assertEqual(len(shown), 8)
        self.assertTrue(all("High" in line for line in shown[:7]))
        self.assertIn("Not shown: 3 below the cap of 8", out)

    def test_stale_citation_not_shown(self):
        (self.repo / "a.go").write_text("package a\nfunc A() {}\n")
        self.write_lessons(lesson_line("Live", cite="a.go:2"), lesson_line("Gone file", cite="gone.go:1"),
                           lesson_line("Gone line", cite="a.go:9"), lesson_line("Outside", cite="../x.go"),
                           lesson_line("No citation"))
        shown, out = self.shown()
        self.assertEqual([line.split(".")[0] for line in shown], ["- Live", "- No citation"])
        self.assertIn("3 with a stale citation", out)
        self.assertEqual(len((self.repos / "acme-billing.md").read_text().splitlines()), 5)

    def test_unused_lesson_moves_to_archive(self):
        expired = lesson_line("Expired", added=day(80), used=day(61))
        self.write_lessons(lesson_line("Fresh"), lesson_line("Recent", used=day(59)), expired)
        shown, out = self.shown()
        self.assertNotIn(expired, shown)
        self.assertIn("1 archived now, unused for 60 days", out)
        active, archive = (self.repos / "acme-billing.md").read_text().split("## Archive")
        self.assertEqual(archive.strip(), expired)
        self.assertEqual(active.strip().splitlines(), [lesson_line("Fresh"), lesson_line("Recent")])
        log = subprocess.run(["git", "-C", str(self.repos), "log", "-1", "--format=%s"],
                             capture_output=True, text=True, env=self.env).stdout
        self.assertEqual(log.strip(), "lesson(acme-billing): archive 1 unused, mark 1 used")

    def test_idle_repo_keeps_its_lessons(self):
        self.write_lessons(lesson_line("A", added=day(200), used=day(100)),
                           lesson_line("B", added=day(200), used=day(150)))
        shown, out = self.shown()
        self.assertEqual(len(shown), 2)
        self.assertNotIn("## Archive", (self.repos / "acme-billing.md").read_text())

    def test_shown_lessons_marked_used_weekly(self):
        self.write_lessons(lesson_line("Old", used=day(8)), lesson_line("New", used=day(2)))
        self.shown()
        self.assertEqual((self.repos / "acme-billing.md").read_text().splitlines(),
                         [lesson_line("Old"), lesson_line("New", used=day(2))])

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


class ReportTests(Base):
    def setUp(self):
        super().setUp()
        self.env["HOME"] = str(self.tmp / "home")
        self.repo = self.make_repo("billing", "https://github.com/acme/billing.git")
        self.inbox.mkdir()

    def report(self, *signals):
        (self.inbox / "signals.jsonl").write_text("".join(json.dumps(s) + "\n" for s in signals))
        return self.run_capture("report", cwd=self.repo).stdout

    def test_precision_rejects_and_flags(self):
        old = {"ts": "2026-01-01T00:00:00+00:00", "kind": "accept", "posted": 0, "dropped": 9}
        accepts = [{"ts": ago(1), "kind": "accept", "posted": 3, "dropped": 1},
                   {"ts": ago(1), "kind": "accept", "posted": 1, "dropped": 3}]
        rejects = [{"ts": ago(1), "kind": "reject", "rule": "one-impl interface"}] * 3
        flagged = {"ts": ago(1), "kind": "reject", "rule": "x", "lesson": "Drop the tenant check", "flag": "never-cut"}
        (self.inbox / "last-consolidation").write_text("2026-02-01\n")
        out = self.report(old, *accepts, *rejects, flagged)
        self.assertIn("Signals since 2026-02-01: 6 (reject 4, revert 0, restore 0, accept 2)", out)
        self.assertIn("Review precision: 4/8 drafted findings posted (50%) in 2 reviews", out)
        self.assertIn("- one-impl interface (3x)", out)
        self.assertIn("Never-cut flags (never apply them):\n- None: Drop the tenant check", out)

    def test_no_reviews_yet(self):
        self.assertIn("Review precision: no accepted reviews", self.report())

    def test_proposals_and_stale_citations(self):
        repos = self.root / "lessons" / "repos"
        repos.mkdir()
        (repos / "acme-billing.md").write_text(f"{lesson_line('Merge with --merge', seen=3)}\n"
                                               f"{lesson_line('Gone', cite='gone.go:1')}\n")
        out = self.report()
        self.assertIn("Lessons in acme-billing: 2 active, 0 archived", out)
        self.assertIn("seen 3x or more (learn.md, Propose a check):\n- acme-billing: Merge with --merge (3x)", out)
        self.assertIn("Stale citations in acme-billing (fix the citation or drop the lesson):\n- Gone (cite gone.go:1)",
                      out)


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
