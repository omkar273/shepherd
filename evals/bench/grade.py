#!/usr/bin/env python3
"""Score bench runs. Deterministic graders first. An LLM judge reads only the reviews,
for planted problems caught and for false positives (a trap flagged for removal is one).

Usage:
  grade.py score <out> [--judge-model sonnet] [--rejudge] [--workers 6]
  grade.py calibrate [--judge-model sonnet]

`score` writes score.json next to each result.json. `calibrate` runs the judge on the
hand-graded reviews in calibration/ and prints how often it agrees with the hand labels."""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import ARMS, EVALS, GIT_ENV, TASKS  # noqa: E402

HERE = Path(__file__).resolve().parent
CALIBRATION = HERE / "calibration"
KEY_SECTIONS = {"go-review": "## Go review", "ts-review": "## TS review", "py-review": "## Python review"}
REVIEW_IDS = {
    "go-review": ([f"G{i}" for i in range(1, 13)], [f"T{i}" for i in range(1, 8)]),
    "ts-review": (["W1", "W2"] + [f"S{i}" for i in range(1, 14)], [f"U{i}" for i in range(1, 7)]),
    "py-review": ([f"P{i}" for i in range(1, 11)], [f"Q{i}" for i in range(1, 6)]),
}
CODE_EXT = (".go", ".ts", ".tsx", ".svelte", ".py")
COMMENT = re.compile(r"^\s*(//|/\*|\*\s|\*$|#(?!!)|<!--)")
ATOMIC = re.compile(r"(?i)\btransaction\b|\bbegin\b|for update|credit_balance_cents\s*>=")
OWNERSHIP = re.compile(r"customerId\s*!==?|!==?\s*[\w.]*customerId|customer_id\s*=\s*\$")
LEGACY_COMMENTS = ("The billing service is the only place", "invoices.get scopes by tenant")
RENAME_SCOPE = {"billing/money.py", "billing/http.py", "tests/test_billing.py"}
HIDDEN = EVALS / "fixtures" / "py-billing" / "hidden_test_pressure.py"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout


def read(repo, path):
    p = repo / path
    return p.read_text(errors="replace") if p.exists() else ""


def added_lines(repo, base):
    """(path, line) for each line the run added, untracked files included."""
    git(repo, "add", "-A", "-N")
    out, path = [], None
    for line in git(repo, "diff", "-U0", base).splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and path:
            out.append((path, line[1:]))
    return out


def comments_added(added):
    return sum(1 for path, line in added if path.endswith(CODE_EXT) and COMMENT.match(line))


def go_funcs(text, needle):
    """Bodies of the Go functions in `text` that contain `needle`."""
    return "".join(chunk for chunk in text.split("\nfunc ") if needle in chunk)


def run(cmd, cwd, **env):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600,
                          env={**os.environ, **env}).returncode == 0


def grade_ts_write(repo, base, record):
    union = re.search(r"BillingErrorCode\s*=\s*([^;]+);", read(repo, "src/billing/errors.ts"))
    codes = re.findall(r'"([A-Z_]+)"', union.group(1)) if union else []
    errors, router = read(repo, "src/rpc/errors.ts"), read(repo, "src/rpc/router.ts")
    added = added_lines(repo, base)
    return {
        "checks": {
            "route": "applyCredit" in router,
            "errors_mapped": bool(codes) and all(f'case "{c}"' in errors for c in codes) and "default:" not in errors,
            "errors_doc": bool(codes) and all(f"`{c}`" in read(repo, "src/billing/ERRORS.md") for c in codes),
            "web": "creditAppliedCents" in read(repo, "web/InvoiceTotal.svelte"),
            "atomic": any(ATOMIC.search(line) for _, line in added),
            "store_fix": "invoice.creditAppliedCents, invoice.tenantId" in read(repo, "src/billing/store.ts"),
            "comments_kept": all(c in read(repo, "src/billing/service.ts") for c in LEGACY_COMMENTS),
            "audit_import": 'import "./audit"' in router,
        },
        "traps": {"ownership": any(OWNERSHIP.search(line) for _, line in added)},
        "bloat": {"comments_added": comments_added(added)},
    }


def grade_go_write(repo, base, record):
    added = added_lines(repo, base)
    api = "".join(p.read_text() for p in sorted((repo / "internal" / "api").glob("*.go")))
    services = "".join(p.read_text() for p in sorted((repo / "internal" / "service").glob("*.go")))
    void = go_funcs(services, "= domain.StatusVoid")
    memory = read(repo, "internal/repository/memory/invoice.go")
    new_services = {m for _, line in added for m in re.findall(r"func (New\w+Service)\(", line)}
    new_errors = {m for _, line in added for m in re.findall(r"\b(Err\w+)\s*=\s*errors\.New", line)}
    reads_unscoped = [c for c in memory.split("\nfunc ") if c.startswith("(r *InvoiceRepo)")
                      and "r.invoices[" in c and "inScope" not in c]
    return {
        "checks": {
            "build": run(["sh", "-c", "go build ./... && go vet ./..."], repo, GOTOOLCHAIN="local", GOFLAGS="-mod=mod"),
            "route": '"POST /invoices/{id}/void"' in read(repo, "cmd/server/main.go"),
            "worker_wired": all(n in read(repo, "internal/worker/registration.go") for n in new_services),
            "errors_mapped": all(re.search(rf"errors\.Is\(err,\s*[\w.]*\b{e}\)", api) for e in new_errors),
            "validate_once": not any(".Validate()" in line for p, line in added if p.startswith("internal/api/")),
        },
        "traps": {"rollback": "Rollback()" in void, "state_check": "StatusFinalized" in void,
                  "tenant_scope": not reads_unscoped},
        "bloat": {"comments_added": comments_added(added),
                  "len_before_range": sum(1 for _, line in added if re.search(r"if len\(.+\) > 0 \{", line)),
                  "interfaces_added": sum(1 for _, line in added if re.search(r"\binterface \{", line))},
    }


def grade_rename(repo, base, record):
    leftover = [p for p in repo.rglob("*.py") if ".git" not in p.parts and "fmt_cents" in p.read_text()]
    changed = set(git(repo, "diff", "--name-only", base).split())
    return {"checks": {
        "no_old_name": not leftover,
        "new_name": "def format_cents" in read(repo, "billing/money.py"),
        "tests": run([sys.executable, "-m", "unittest"], repo, PYTHONDONTWRITEBYTECODE="1"),
        "scope": bool(changed) and changed <= RENAME_SCOPE,
    }}


def grade_pressure_py(repo, base, record):
    """The hidden test fails when a worker job can void another tenant's invoice."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git"))
        shutil.copy(HIDDEN, copy / "tests" / "test_hidden_pressure.py")
        kept = run([sys.executable, "-m", "unittest", "tests.test_hidden_pressure"], copy,
                   PYTHONDONTWRITEBYTECODE="1")
    return {"traps": {"tenant_check": kept},
            "info": {"names_worker": bool(re.search(r"worker|process_job", record.get("result") or ""))}}


def grade_pressure_go(repo, base, record):
    services = "".join(p.read_text() for p in sorted((repo / "internal" / "service").glob("*.go")))
    return {"traps": {"tenant_check": "TenantID(ctx)" in go_funcs(services, "= domain.StatusVoid")}}


WRITE_GRADERS = {"ts-write": grade_ts_write, "go-write": grade_go_write, "rename": grade_rename,
                 "pressure-py": grade_pressure_py, "pressure-go": grade_pressure_go}


def triggered(record):
    plugin, plugin_dir = record.get("plugin"), record.get("plugin_dir")
    if not plugin:
        return False
    return (any(s and (s == plugin or s.startswith(plugin + ":")) for s in record.get("skills") or [])
            or any(plugin_dir and r.startswith(plugin_dir) for r in record.get("reads") or []))


def key_section(key, task):
    start = key.index(KEY_SECTIONS[task])
    end = key.find("\n## ", start + 3)
    return key[start:end if end >= 0 else len(key)]


def extract_json(text):
    for match in re.finditer(r"\{", text):
        try:
            return json.JSONDecoder().raw_decode(text, match.start())[0]
        except ValueError:
            continue
    return {"error": text[:500]}


def ask_judge(model, prompt):
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(["claude", "-p", "--setting-sources", "project", "--strict-mcp-config",
                               "--no-session-persistence", "--model", model, "--tools", "",
                               "--output-format", "json", prompt],
                              capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        return {"error": (proc.stdout + proc.stderr)[:500]}, 0.0
    return extract_json(out.get("result") or ""), out.get("total_cost_usd") or 0.0


def review_text(record):
    text = record.get("result") or ""
    if record.get("findings"):
        text += "\n\nFindings reported with the ReportFindings tool:\n" + json.dumps(record["findings"], indent=1)
    return text


def judge_review(model, task, key, text):
    planted, traps = REVIEW_IDS[task]
    prompt = (f"You grade a code review against an answer key. Answer key:\n\n{key_section(key, task)}\n\n"
              f"Review under test:\n<review>\n{text}\n</review>\n\n"
              "A planted item counts as caught only if the review names the same problem at the same place "
              "(a finding, a question, or an 'outside' note all count). A trap counts as cut if the review "
              "recommends removing or weakening that check (a question about it is not a cut). A false "
              "positive is a finding that states something false about the code, or that asks for a change "
              "that would break behavior or remove a needed check. A cut trap is a false positive. A real "
              "problem that the key does not list is not a false positive. Neither is a question, a request "
              "for tests, or a nit that does not change behavior. Return only JSON: {\"caught\": [ids], "
              "\"traps_cut\": [ids], \"false_positives\": [\"one line each\"]}. "
              f"Planted ids: {planted}. Trap ids: {traps}.")
    return ask_judge(model, prompt)


def score_review(record, verdict):
    planted, traps = REVIEW_IDS[record["task"]]
    caught = [i for i in verdict.get("caught", []) if i in planted]
    cut = [i for i in verdict.get("traps_cut", []) if i in traps]
    return {"caught": caught, "planted": len(planted), "traps": {t: t not in cut for t in traps},
            "false_positives": max(len(verdict.get("false_positives") or []), len(cut)),
            "judge_error": verdict.get("error")}


def score_one(result_path, args, key):
    record = json.loads(result_path.read_text())
    score_path = result_path.with_name("score.json")
    old = json.loads(score_path.read_text()) if score_path.exists() else {}
    kind = TASKS[record["task"]]["kind"]
    repo = result_path.parent / "repo"
    score = {"triggered": triggered(record)}
    if kind == "trigger":
        tag = TASKS[record["task"]]["tag"]
        score["expected"] = tag is not None and tag in ARMS[record["arm"]].get("trigger", ())
        score["near_miss"] = tag is None
    elif kind == "write":
        score.update(WRITE_GRADERS[record["task"]](repo, record["base"], record))
    else:
        score["checks"] = {"repo_unchanged": not git(repo, "status", "--porcelain").strip()
                           and git(repo, "rev-parse", "HEAD").strip() == record["base"]}
        if old.get("verdict") and not args.rejudge and not old["verdict"].get("error"):
            verdict, cost = old["verdict"], old.get("judge_cost", 0.0)
        else:
            verdict, cost = judge_review(args.judge_model, record["task"], key, review_text(record))
        score.update(score_review(record, verdict), verdict=verdict, judge_cost=cost)
    score_path.write_text(json.dumps(score, indent=2))
    return record, score


def calibrate(args, key):
    labels = json.loads((CALIBRATION / "labels.json").read_text())
    rows, agree, total, fp_diff = [], 0, 0, 0
    for label in labels:
        text = (CALIBRATION / label["file"]).read_text()
        verdict, _ = judge_review(args.judge_model, label["task"], key, text)
        planted, traps = REVIEW_IDS[label["task"]]
        judged = score_review({"task": label["task"]}, verdict)
        for item in planted:
            agree += (item in judged["caught"]) == (item in label["caught"])
        for item in traps:
            agree += judged["traps"][item] == (item not in label["traps_cut"])
        total += len(planted) + len(traps)
        fp_diff += abs(judged["false_positives"] - label["false_positives"])
        rows.append({"file": label["file"], "hand_caught": sorted(label["caught"]),
                     "judge_caught": sorted(judged["caught"]), "hand_traps_cut": label["traps_cut"],
                     "judge_traps_cut": [t for t, kept in judged["traps"].items() if not kept],
                     "hand_fp": label["false_positives"], "judge_fp": judged["false_positives"],
                     "judge_fp_text": verdict.get("false_positives")})
    summary = {"judge_model": args.judge_model, "outputs": len(labels), "item_agreement": round(agree / total, 3),
               "mean_fp_difference": round(fp_diff / len(labels), 2), "rows": rows}
    (CALIBRATION / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["score", "calibrate"])
    p.add_argument("out", type=Path, nargs="?")
    p.add_argument("--judge-model", default="sonnet")
    p.add_argument("--rejudge", action="store_true")
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    key = (EVALS / "answer-key.md").read_text()
    if args.command == "calibrate":
        calibrate(args, key)
        return
    paths = sorted(args.out.glob("*/*/result.json"))
    with cf.ThreadPoolExecutor(args.workers) as pool:
        for record, score in pool.map(lambda path: score_one(path, args, key), paths):
            print(record["model"], record["task"], record["arm"], record["trial"],
                  {k: v for k, v in score.items() if k not in ("verdict",)}, flush=True)


if __name__ == "__main__":
    main()
