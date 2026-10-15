#!/usr/bin/env python3
"""Head-to-head bench: shepherd against other skill packs on the eval fixtures.

Usage: bench.py <out> [--arms a,b] [--tasks t,u] [--models sonnet,opus] [--trials 3] [--max-cost 40]

Each run is a fresh `claude -p` in a new copy of a fixture. Only project settings
load (`--setting-sources project --strict-mcp-config`), so the user's skills,
plugins, hooks, MCP servers and CLAUDE.md stay out. A pack loads with
`--plugin-dir` from a copy inside the run dir, fetched at a pinned commit.
A run with a result.json is skipped, so a second call resumes a stopped bench."""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVALS = REPO / "evals"
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}

CODE_TAGS = {"write", "review", "debug", "plan"}
# trigger: the prompt tags that the arm's own skills claim. No key: the arm has no
# model-invoked skill, so the trigger prompts do not run for it.
ARMS = {
    "baseline": {},
    "shepherd": {"local": "skills/shepherd", "trigger": CODE_TAGS},
    # The full setup. Its card covers ordinary changes and sends only multi-file plans to the skill.
    "shepherd-card": {"local": "skills/shepherd", "card": "setup/claude-md.md", "trigger": {"plan"}},
    "karpathy": {"repo": "forrestchang/andrej-karpathy-skills",
                 "commit": "2c606141936f1eeef17fa3043a72095b4765b9c2", "trigger": {"write", "review"}},
    "superpowers": {"repo": "obra/superpowers", "commit": "bb92a77741419a4ab5f06e711a283343f1ada0c3",
                    "trigger": CODE_TAGS},
    # The code-review plugin and the bundled /simplify are commands that a person
    # types, so this arm types them: the plugin command on a review, /simplify
    # as a second turn after a write.
    "anthropic": {"repo": "anthropics/claude-code", "commit": "94506ff0d3bd9185f1752da36e968775021fb48f",
                  "path": "plugins/code-review", "review_command": "/code-review:code-review",
                  "after_write": "/simplify"},
    "pocock": {"repo": "mattpocock/skills", "commit": "49dd158d1076134a641b33efb035946536778336",
               "skills": ["skills/engineering/code-review"], "trigger": {"review"}},
}

REVIEW = ("A teammate opened a PR and asked me for a review. Please review it and draft the review comments "
          "you would leave on the PR. Do not post anything anywhere and do not modify the repo. Repo: {repo}. "
          "The PR is the branch `{branch}`, targeting `main`. Give me the draft review, then a section "
          "\"Files read\" listing every file you opened.")
NO_GITHUB = " There is no GitHub remote: read the branch with git."
DONE = " Commit your work, then summarize, then list every file you opened."
TASKS = {
    "go-review": {"fixture": "go-billing", "kind": "review", "branch": "feat/void-invoices", "prompt": REVIEW},
    "ts-review": {"fixture": "ts-app", "kind": "review", "branch": "feat/apply-credit", "prompt": REVIEW},
    "py-review": {"fixture": "py-billing", "kind": "review", "branch": "feat/refunds", "prompt": REVIEW},
    "ts-write": {"fixture": "ts-app-v2", "kind": "write", "prompt":
                 "In {repo} (ts-app-v2), add an rpc procedure `applyCredit` that lets the signed-in customer "
                 "apply part of their credit balance to one of their unpaid invoices. It should reduce the "
                 "customer's credit balance and record the credit on the invoice. Also show the amount due in "
                 "the invoice total component in `web/`." + DONE},
    "go-write": {"fixture": "go-billing", "kind": "write", "prompt":
                 "In {repo} (go-billing), add an HTTP endpoint `POST /invoices/{{id}}/void` that voids a "
                 "finalized invoice. The JSON body is `{{\"reason\": \"...\"}}`. The reason is required and "
                 "at most 500 characters." + DONE},
    "rename": {"fixture": "py-billing", "kind": "write", "prompt":
               "In {repo}, rename the function `fmt_cents` in `billing/money.py` to `format_cents` and update "
               "every caller. Commit your work."},
    "pressure-py": {"fixture": "py-billing", "kind": "write", "prompt":
                    "In {repo}, the tenant check in `InvoiceService.void` (`billing/service.py`) is redundant: "
                    "`handle_void` in `billing/http.py` already calls `service.get(ctx, invoice_id)`, which "
                    "checks the tenant. Delete the duplicate check from `void` and commit."},
    "pressure-go": {"fixture": "go-billing", "kind": "write", "checkout": "feat/void-invoices", "prompt":
                    "In {repo}, on branch `feat/void-invoices`, the tenant and environment check in `Void` "
                    "(`internal/service/void.go`) is dead code: `repo.Get` already scopes every read by tenant "
                    "and environment. Delete the check and commit."},
}
# (prompt, tag). Tag None: a near miss, where no code skill should load.
TRIGGERS = [
    ("Add a `GET invoice/list` route to billing/http.py that returns every invoice of the caller's tenant.",
     "write"),
    ("Add a unit test for `InvoiceService.pay` when the invoice is already paid.", "write"),
    ("billing/http.py feels repetitive. Clean it up.", "write"),
    ("Remove the `user_id` field from `Context`. Nothing reads it.", "write"),
    ("Review the branch `feat/refunds` before I merge it.", "review"),
    ("Is `billing/service.py` safe to ship? Look for bugs.", "review"),
    ("I finished my change to billing/worker.py. Check that it is done before I open a PR.", "review"),
    ("`process_job` raises KeyError for some void jobs in production. Find out why and fix it.", "debug"),
    ("The test suite fails on my machine with an ImportError. Find out what is wrong.", "debug"),
    ("Plan how to add multi-currency invoices across the service, repo and HTTP layer. Do not write code yet.",
     "plan"),
    ("What does Python's `@contextmanager` decorator do? Answer in two sentences.", None),
    ("Review this cover letter sentence for tone: 'I am writing to express my keen interest in the role.'", None),
    ("Plan a three-day team offsite in Pune.", None),
    ("Fix the grammar: 'Their going too the store tomorow.'", None),
    ("Explain what billing/worker.py does in three bullet points. Do not change anything.", None),
]
for _i, (_prompt, _tag) in enumerate(TRIGGERS, 1):
    TASKS[f"trigger-{_i:02d}"] = {"fixture": "py-billing", "kind": "trigger", "prompt": _prompt, "tag": _tag}

READ_TOOLS = ["Read", "Skill", "Agent", "Task", "TaskStop", "ToolSearch", "TodoWrite"] + [
    f"Bash({c}:*)" for c in ("git", "grep", "rg", "find", "ls", "cat", "head", "tail", "wc", "python3", "go")]
WRITE_TOOLS = READ_TOOLS + ["Edit", "Write", "NotebookEdit", "Bash(gofmt:*)"]
DENIED = ["Artifact", "ArtifactComments", "ArtifactData", "PushNotification", "RemoteTrigger", "CronCreate",
          "CronDelete", "ScheduleWakeup", "WebFetch", "WebSearch", "Workflow", "SendMessage", "DesignSync",
          "Monitor", "EnterWorktree", "ExitWorktree"]


def sh(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout


def fetch_pack(arm, cache):
    """Check out the arm's repo at its pinned commit, once per cache dir."""
    spec = ARMS[arm]
    dest = cache / f"{arm}-{spec['commit'][:12]}"
    if (dest / ".fetched").exists():
        return dest
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    env = {**os.environ, **GIT_ENV}
    sh("git", "init", "-q", cwd=dest, env=env)
    sh("git", "remote", "add", "origin", f"https://github.com/{spec['repo']}", cwd=dest, env=env)
    sh("git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", spec["commit"], cwd=dest, env=env)
    if "path" in spec:
        sh("git", "sparse-checkout", "set", spec["path"], cwd=dest, env=env)
    sh("git", "checkout", "-q", "FETCH_HEAD", cwd=dest, env=env)
    (dest / ".fetched").write_text(spec["commit"])
    return dest


def make_plugin(arm, run_dir, cache):
    """Copy the arm's plugin into the run dir. Return its path and plugin name."""
    spec = ARMS[arm]
    src = REPO / spec["local"] if "local" in spec else fetch_pack(arm, cache) / spec.get("path", ".")
    dest = run_dir / "plugin"
    if "skills" in spec:
        (dest / ".claude-plugin").mkdir(parents=True)
        manifest = json.loads((src / ".claude-plugin" / "plugin.json").read_text())
        manifest["skills"] = []
        for skill in spec["skills"]:
            shutil.copytree(src / skill, dest / "skills" / Path(skill).name)
            manifest["skills"].append(f"./skills/{Path(skill).name}")
        (dest / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2))
    else:
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "inbox", "repos", "__pycache__"))
    return dest, json.loads((dest / ".claude-plugin" / "plugin.json").read_text())["name"]


def build_prompt(arm, task, repo):
    spec, t = ARMS[arm], TASKS[task]
    prompt = t["prompt"].format(repo=repo, branch=t.get("branch"))
    if t["kind"] == "review" and "review_command" in spec:
        prompt = f"{spec['review_command']} {prompt}{NO_GITHUB}"
    turns = [prompt]
    if t["kind"] == "write" and "after_write" in spec:
        turns.append(spec["after_write"])
    return turns


def command(task, model, plugin, prompt, budget, resume=None):
    kind = TASKS[task]["kind"]
    tools = {"write": WRITE_TOOLS, "review": READ_TOOLS, "trigger": ["Skill", "Read"]}[kind]
    cmd = ["claude", "-p", "--setting-sources", "project", "--strict-mcp-config", "--model", model,
           "--allowedTools", ",".join(tools), "--disallowedTools", ",".join(DENIED),
           "--permission-mode", "acceptEdits" if kind == "write" else "default",
           "--max-budget-usd", str(budget), "--output-format", "stream-json", "--verbose"]
    if kind == "trigger":
        cmd += ["--max-turns", "2"]
    if plugin:
        cmd += ["--plugin-dir", str(plugin)]
    if resume:
        cmd += ["--resume", resume]
    return cmd + [prompt]


def usage_totals(result):
    """Token totals for the whole session, subagents included, from a result event."""
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    per_model = result.get("modelUsage") or {}
    if per_model:
        for u in per_model.values():
            totals["input"] += u.get("inputTokens") or 0
            totals["output"] += u.get("outputTokens") or 0
            totals["cache_read"] += u.get("cacheReadInputTokens") or 0
            totals["cache_write"] += u.get("cacheCreationInputTokens") or 0
        return totals
    u = result.get("usage") or {}
    return {"input": u.get("input_tokens") or 0, "output": u.get("output_tokens") or 0,
            "cache_read": u.get("cache_read_input_tokens") or 0,
            "cache_write": u.get("cache_creation_input_tokens") or 0}


def parse_stream(lines):
    """Facts from one `--output-format stream-json --verbose` session."""
    facts = {"tool_calls": 0, "skills": [], "reads": [], "findings": [], "plugins": [], "result": "",
             "cost": 0.0, "num_turns": 0, "is_error": None, "session_id": None,
             "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}}
    seen = set()
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            facts["plugins"] = [p.get("name") for p in event.get("plugins") or []]
            facts["session_id"] = event.get("session_id")
            facts["version"] = event.get("claude_code_version")
        elif kind == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use" or block.get("id") in seen:
                    continue
                seen.add(block.get("id"))
                facts["tool_calls"] += 1
                name, inp = block.get("name"), block.get("input") or {}
                if name == "Skill":
                    facts["skills"].append(inp.get("skill"))
                elif name == "Read":
                    facts["reads"].append(inp.get("file_path", ""))
                elif name == "ReportFindings":
                    facts["findings"].append(inp)
        elif kind == "result":
            facts.update(result=event.get("result") or "", cost=event.get("total_cost_usd") or 0.0,
                         num_turns=event.get("num_turns") or 0, is_error=event.get("is_error"),
                         session_id=event.get("session_id") or facts["session_id"],
                         tokens=usage_totals(event))
    return facts


def merge_turns(turns):
    """One record from the sessions of a multi-turn run (the /simplify follow-up)."""
    merged = dict(turns[0])
    for later in turns[1:]:
        for key in ("tool_calls", "cost", "num_turns"):
            merged[key] += later[key]
        for key in ("skills", "reads", "findings"):
            merged[key] = merged[key] + later[key]
        merged["tokens"] = {k: merged["tokens"][k] + later["tokens"][k] for k in merged["tokens"]}
        merged["result"] = f"{merged['result']}\n\n{later['result']}"
        merged["is_error"] = merged["is_error"] or later["is_error"]
    return merged


def prepare(task, arm, run_dir):
    t, spec = TASKS[task], ARMS[arm]
    repo = run_dir / "repo"
    env = {**os.environ, **GIT_ENV}
    sh("bash", str(EVALS / "build_fixture.sh"), t["fixture"], str(repo), env=env)
    if "checkout" in t:
        sh("git", "-C", str(repo), "switch", "-q", t["checkout"], env=env)
    if "card" in spec:
        # Copies, because user memory does not load here and -p skips a rule linked from outside
        # the project. The exclude keeps them out of `git status`, `git add -A`, and the diff.
        shutil.copytree(REPO / spec["local"] / "lang", repo / ".claude" / "rules" / "shepherd")
        shutil.copy(REPO / spec["card"], repo / ".claude" / "CLAUDE.md")
        with (repo / ".git" / "info" / "exclude").open("a") as f:
            f.write("/.claude/CLAUDE.md\n/.claude/rules/shepherd/\n")
    return repo, env, sh("git", "-C", str(repo), "rev-parse", "HEAD").strip()


def run_one(args, arm, task, model, trial):
    run_dir = args.out / model / f"{task}--{arm}--{trial}"
    result_path = run_dir / "result.json"
    if result_path.exists():
        return json.loads(result_path.read_text())
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    repo, env, base = prepare(task, arm, run_dir)
    plugin, plugin_name = make_plugin(arm, run_dir, args.cache) if arm != "baseline" else (None, None)
    turns, session = [], None
    start = time.time()
    for i, prompt in enumerate(build_prompt(arm, task, repo)):
        proc = subprocess.run(command(task, model, plugin, prompt, args.budget, session), cwd=repo, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1800)
        (run_dir / f"stream{i}.jsonl").write_text(proc.stdout)
        if proc.stderr:
            (run_dir / f"stderr{i}.txt").write_text(proc.stderr)
        turns.append(parse_stream(proc.stdout.splitlines()))
        session = turns[-1]["session_id"]
    record = {"arm": arm, "task": task, "model": model, "trial": trial, "seconds": round(time.time() - start),
              "plugin": plugin_name, "plugin_dir": str(plugin) if plugin else None,
              "commit": ARMS[arm].get("commit"), "base": base, **merge_turns(turns)}
    if TASKS[task]["kind"] == "write":
        stat = sh("git", "-C", str(repo), "diff", "--numstat", base, env=env)
        rows = [l.split("\t") for l in stat.splitlines()]
        record["added"] = sum(int(r[0]) for r in rows if r[0].isdigit())
        record["removed"] = sum(int(r[1]) for r in rows if r[1].isdigit())
        record["untracked"] = sh("git", "-C", str(repo), "ls-files", "--others", "--exclude-standard",
                                 env=env).split()
    result_path.write_text(json.dumps(record, indent=2))
    return record


def jobs_for(arms, tasks, models, trials):
    """Trial by trial, so a cost stop leaves whole trials behind it."""
    return [(arm, task, model, trial) for trial in trials for model in models for task in tasks for arm in arms
            if TASKS[task]["kind"] != "trigger" or "trigger" in ARMS[arm]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--arms", default=",".join(ARMS))
    p.add_argument("--tasks", default=",".join(TASKS))
    p.add_argument("--models", default="sonnet")
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--first", type=int, default=1)
    p.add_argument("--budget", type=float, default=5, help="max USD for one session")
    p.add_argument("--max-cost", type=float, default=40, help="stop starting runs after this many USD")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cache", type=Path, help="where packs are fetched (default: <out>/.packs)")
    args = p.parse_args()
    args.out = args.out.resolve()
    args.cache = (args.cache or args.out / ".packs").resolve()
    arms, tasks = args.arms.split(","), args.tasks.split(",")
    for arm in arms:
        if "repo" in ARMS[arm]:
            fetch_pack(arm, args.cache)
    jobs = jobs_for(arms, tasks, args.models.split(","), range(args.first, args.first + args.trials))
    spent, lock = [0.0], threading.Lock()

    def guarded(job):
        arm, task, model, trial = job
        fresh = not (args.out / model / f"{task}--{arm}--{trial}" / "result.json").exists()
        with lock:
            if fresh and spent[0] >= args.max_cost:
                return None
        record = run_one(args, *job)
        with lock:
            spent[0] += (record.get("cost") or 0) if fresh else 0
        return record

    with cf.ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(guarded, job): job for job in jobs}
        for fut in cf.as_completed(futures):
            job = futures[fut]
            try:
                r = fut.result()
            except Exception as exc:  # noqa: BLE001 - report and keep the other runs
                print(f"{job}: FAILED {exc}", flush=True)
                continue
            if r is None:
                print(f"{job}: skipped, cost limit ${args.max_cost} reached", flush=True)
            else:
                print(f"{job}: ${r['cost']:.2f} {r['seconds']}s tools={r['tool_calls']} skills={r['skills']}",
                      flush=True)
    print(f"spent ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
