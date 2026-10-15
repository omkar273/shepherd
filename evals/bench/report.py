#!/usr/bin/env python3
"""Turn scored bench runs into markdown tables.

Usage: report.py <out> [--write README.md evals/README.md]
With --write, the tables replace the text between the bench markers in each file."""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import ARMS, TASKS  # noqa: E402

START, END = "<!-- bench:start -->", "<!-- bench:end -->"
REVIEWS = ("go-review", "ts-review", "py-review")
WRITES = ("ts-write", "go-write", "rename")


def load(out):
    runs = []
    for result in sorted(out.glob("*/*/result.json")):
        score = result.with_name("score.json")
        if score.exists():
            runs.append((json.loads(result.read_text()), json.loads(score.read_text())))
    return runs


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def fmt(value, spec):
    return "n/a" if value is None else format(value, spec)


def summarize(runs):
    """Metrics for one arm on one model."""
    main = [(r, s) for r, s in runs if TASKS[r["task"]]["kind"] != "trigger"]
    reviews = [(r, s) for r, s in main if r["task"] in REVIEWS]
    writes = [(r, s) for r, s in main if r["task"] in WRITES]
    by_task = defaultdict(list)
    for r, s in main:
        if s.get("traps"):
            by_task[r["task"]].append(s["traps"])
    checks = [ok for _, s in writes for ok in s.get("checks", {}).values()]
    trig = [s for r, s in runs if TASKS[r["task"]]["kind"] == "trigger"]
    in_scope = [s for s in trig if s["expected"]]
    near = [s for s in trig if s["near_miss"]]
    m = {
        "runs": len(main),
        "caught": pct(sum(len(s["caught"]) for _, s in reviews), sum(s["planted"] for _, s in reviews)),
        "fp": fmt(mean(s["false_positives"] for _, s in reviews), ".1f"),
        "traps_cut": sum(not kept for _, s in main for kept in s.get("traps", {}).values()),
        "pass_k": f"{sum(all(all(t.values()) for t in trials) for trials in by_task.values())}/{len(by_task)}",
        "checks": pct(sum(checks), len(checks)),
        "cost": mean(r["cost"] for r, _ in main),
        "total": sum(r["cost"] for r, _ in runs),
        "cache_write": mean(r["tokens"]["cache_write"] for r, _ in main),
        "seconds": mean(r["seconds"] for r, _ in main),
        "tools": mean(r["tool_calls"] for r, _ in main),
        "trigger": f"{sum(s['triggered'] for s in in_scope)}/{len(in_scope)}" if in_scope else "n/a",
        "near_miss": f"{sum(s['triggered'] for s in near)}/{len(near)}" if near else "n/a",
    }
    for task in REVIEWS:
        rs = [s for r, s in reviews if r["task"] == task]
        m[task] = f"{fmt(mean(len(s['caught']) for s in rs), '.1f')}/{rs[0]['planted']}" if rs else "n/a"
    for task in ("ts-write", "go-write"):
        m[task] = fmt(mean(r["added"] for r, _ in main if r["task"] == task), ".0f")
    for task in ("pressure-py", "pressure-go"):
        ps = [s for r, s in main if r["task"] == task]
        m[task] = f"{sum(s['traps']['tenant_check'] for s in ps)}/{len(ps)}" if ps else "n/a"
    rename = [r for r, _ in main if r["task"] == "rename"]
    m["rename"] = (f"${fmt(mean(r['cost'] for r in rename), '.2f')}, {fmt(mean(r['seconds'] for r in rename), '.0f')}s"
                   if rename else "n/a")
    return m


def render(runs):
    groups = defaultdict(list)
    for r, s in runs:
        groups[(r["model"], r["arm"])].append((r, s))
    arm_order = list(ARMS)
    keys = sorted(groups, key=lambda k: (k[0], arm_order.index(k[1])))
    rows = {k: summarize(groups[k]) for k in keys}
    trials = max(r["trial"] for r, _ in runs)
    versions = sorted({r.get("version") for r, _ in runs if r.get("version")})
    out = [f"{len(runs)} runs, up to {trials} trials for each arm, task and model. "
           f"Claude Code {', '.join(versions) or 'unknown'}. Cost is the CLI's `total_cost_usd`.", "",
           "**Quality**", "",
           "| Model | Arm | Planted caught | False positives per review | Traps cut | "
           f"Trap tasks kept (pass^{trials}) | Write checks passed | Pressure: check kept (Py / Go) | "
           "Trigger recall | Near-miss triggers |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for (model, arm), m in rows.items():
        out.append(f"| {model} | {arm} | {m['caught']} | {m['fp']} | {m['traps_cut']} | {m['pass_k']} | "
                   f"{m['checks']} | {m['pressure-py']} / {m['pressure-go']} | {m['trigger']} | {m['near_miss']} |")
    out += ["", "**Cost** (a mean for each run of the main tasks. Total $ includes the trigger prompts.)", "",
            "| Model | Arm | $ per run | Cache-write tokens | Wall time | Tool calls | Rename ($, time) | Total $ |",
            "|---|---|---|---|---|---|---|---|"]
    for (model, arm), m in rows.items():
        out.append(f"| {model} | {arm} | {fmt(m['cost'], '.2f')} | {fmt(m['cache_write'], ',.0f')} | "
                   f"{fmt(m['seconds'], '.0f')}s | {fmt(m['tools'], '.0f')} | {m['rename']} | {m['total']:.2f} |")
    out += ["", "**By task** (mean for each run)", "",
            "| Model | Arm | Go review caught | TS review caught | Python review caught | Lines added (TS / Go write) |",
            "|---|---|---|---|---|---|"]
    for (model, arm), m in rows.items():
        out.append(f"| {model} | {arm} | {m['go-review']} | {m['ts-review']} | {m['py-review']} | "
                   f"{m['ts-write']} / {m['go-write']} |")
    return "\n".join(out)


def write_between_markers(path, block):
    text = path.read_text()
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    path.write_text(f"{head}{START}\n\n{block}\n\n{END}{tail}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--write", type=Path, nargs="*", default=[])
    args = p.parse_args()
    block = render(load(args.out))
    print(block)
    for path in args.write:
        write_between_markers(path, block)


if __name__ == "__main__":
    main()
