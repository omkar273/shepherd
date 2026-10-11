#!/usr/bin/env python3
"""Report drift between this repo and the installed skills, as JSON."""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[2]
RUNTIMES = {"claude": Path(".claude/skills"), "agents": Path(".agents/skills")}


def remote_head(url):
    out = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=20)
    return out.stdout.split()[0] if out.returncode == 0 and out.stdout else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    home = Path(args.home).expanduser()
    skills = sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists())
    report = {"missing": [], "broken": [], "shadowed": [], "behind": [],
              "uncommitted": [], "days_since_update": None}

    for runtime, rel in RUNTIMES.items():
        runtime_dir = home / rel
        for skill in skills:
            target = runtime_dir / skill.name
            if not os.path.lexists(target):
                report["missing"].append(f"{runtime}/{skill.name}")
            elif Path(os.path.realpath(target)) != skill:
                report["shadowed"].append(f"{runtime}/{skill.name}")
        if runtime_dir.is_dir():
            report["broken"] += [f"{runtime}/{p.name}" for p in sorted(runtime_dir.iterdir())
                                 if p.is_symlink() and not p.exists()]

    if args.remote:
        heads = {}
        for skill in skills:
            origin = skill_meta.read_origin(skill)
            url = origin.get("source_repo", "")
            if sync_skill.is_remote(url):
                heads.setdefault(url, remote_head(url))
                ref = origin.get("source_ref", "")
                if heads[url] and ref and not heads[url].startswith(ref):
                    report["behind"].append(skill.name)

    porcelain = subprocess.run(["git", "-C", str(SKILLS_DIR.parent), "status", "--porcelain"],
                               capture_output=True, text=True)
    report["uncommitted"] = [line[3:] for line in porcelain.stdout.splitlines()]

    try:
        state = json.loads((home / ".claude" / "shepherd.json").read_text())
        report["days_since_update"] = (datetime.date.today()
                                       - datetime.date.fromisoformat(state["last_update"])).days
    except (OSError, ValueError, KeyError, TypeError):
        pass

    counts = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    report["summary"] = ", ".join(f"{k}: {n}" for k, n in counts.items()) + \
        f", days since update: {report['days_since_update']}"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
