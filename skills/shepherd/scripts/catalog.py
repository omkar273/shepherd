#!/usr/bin/env python3
"""shepherd's skill catalog: packs of skills fetched on demand from their GitHub repos."""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_skills import RUNTIMES, backup_path

REPO = Path(__file__).resolve().parents[3]
CATALOG = REPO / "catalog" / "catalog.json"
FIELDS = ("name", "repo", "path", "license", "decision")


def load(catalog_path):
    return json.loads(Path(catalog_path).read_text())


def check(data, repo_root):
    repo_root = Path(repo_root)
    owner = {p.name: "core" for p in (repo_root / "skills").iterdir() if (p / "SKILL.md").exists()}
    retired = repo_root / "setup" / "retired.txt"
    for name in retired.read_text().split() if retired.exists() else []:
        owner.setdefault(name, "retired")
    errors = []
    for pack, spec in data.get("packs", {}).items():
        for skill in spec.get("skills", []):
            name = skill.get("name", "?")
            where = f"{pack}/{name}"
            missing = [f for f in FIELDS if not skill.get(f)]
            if missing:
                errors.append(f"{where}: missing {', '.join(missing)}")
            if name in owner:
                errors.append(f"{where}: duplicate name, already {owner[name]}")
            owner[name] = f"in pack {pack}"
            if skill.get("decision") and not (repo_root / skill["decision"]).exists():
                errors.append(f"{where}: decision record {skill['decision']} not found")
    return errors


def installed_packs(home):
    try:
        return json.loads((home / ".claude" / "shepherd.json").read_text()).get("packs", [])
    except (OSError, ValueError, AttributeError):
        return []


def record_packs(home, packs):
    path = home / ".claude" / "shepherd.json"
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state["packs"] = packs
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state) + "\n")


def list_packs(data, home):
    installed = installed_packs(home)
    return {pack: {"domain": spec.get("domain", ""), "skills": [s["name"] for s in spec.get("skills", [])],
                   "installed": pack in installed}
            for pack, spec in data.get("packs", {}).items()}


def fetch(repo, path, dest):
    """Copy `path` from the latest default branch of `repo` into `dest`; return the commit fetched."""
    with tempfile.TemporaryDirectory() as work:
        git = lambda *args: subprocess.run(["git", "-C", work, *args], capture_output=True)
        git("init", "-q")
        git("fetch", "-q", "--depth", "1", repo, "HEAD")
        archive = git("archive", "--format=tar", "FETCH_HEAD", path)
        if archive.returncode != 0:
            sys.exit(f"catalog: cannot read {path} from {repo}")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(work + "/out", filter="data")
        shutil.move(Path(work, "out", path), dest)
        return git("rev-parse", "FETCH_HEAD").stdout.decode().strip()


def cache_dir(home, skill):
    return home / ".shepherd" / "catalog" / skill["name"]


def install(pack, home, catalog_path):
    skills = load(catalog_path)["packs"][pack]["skills"]
    staged = []
    for skill in skills:
        stage = Path(tempfile.mkdtemp()) / skill["name"]
        commit = fetch(skill["repo"], skill["path"], stage)
        staged.append((skill, stage, commit))

    report = {"fetched": {}, "linked": [], "backed_up": []}
    for skill, stage, commit in staged:
        cache = cache_dir(home, skill)
        shutil.rmtree(cache, ignore_errors=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(stage, cache)
        report["fetched"][skill["name"]] = commit
        for runtime, rel in RUNTIMES.items():
            target = home / rel / skill["name"]
            if target.is_symlink() and Path(os.path.realpath(target)) == cache.resolve():
                continue
            if os.path.lexists(target):
                backup = backup_path(home, runtime, skill["name"])
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.rename(target, backup)
                report["backed_up"].append(f"{runtime}/{skill['name']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(cache, target_is_directory=True)
            report["linked"].append(f"{runtime}/{skill['name']}")
    record_packs(home, sorted(set(installed_packs(home)) | {pack}))
    return report


def uninstall(pack, home, catalog_path):
    cache_root = (home / ".shepherd" / "catalog").resolve()
    report = {"unlinked": []}
    for skill in load(catalog_path)["packs"][pack]["skills"]:
        for runtime, rel in RUNTIMES.items():
            target = home / rel / skill["name"]
            if target.is_symlink() and Path(os.path.realpath(target)).parent == cache_root:
                target.unlink()
                report["unlinked"].append(f"{runtime}/{skill['name']}")
    record_packs(home, [p for p in installed_packs(home) if p != pack])
    return report


def prune(home, catalog_path):
    packs = load(catalog_path)["packs"]
    keep = {s["name"] for p in installed_packs(home) if p in packs for s in packs[p]["skills"]}
    root = home / ".shepherd" / "catalog"
    removed = [d.name for d in sorted(root.iterdir()) if d.name not in keep] if root.is_dir() else []
    for name in removed:
        shutil.rmtree(root / name)
    return removed


def hint(data, home, catalog_path):
    """UserPromptSubmit: name each pack not installed whose cues match the prompt, once a session."""
    from context_hooks import session_dir
    prompt = data["prompt"].lower()
    installed = installed_packs(home)
    logs = session_dir(home, data)
    lines = []
    for pack, spec in load(catalog_path)["packs"].items():
        offered = logs / f"hinted-{pack}"
        if pack in installed or offered.exists():
            continue
        if any(re.search(rf"\b{re.escape(cue.lower())}\b", prompt) for cue in spec.get("cues", [])):
            offered.touch()
            skills = ", ".join(s["name"] for s in spec["skills"])
            lines.append(f"The {pack} pack ({skills}) fits this prompt. Offer `/catalog install {pack}` once.")
    if not lines:
        return None
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(lines)}}


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", default=str(Path.home()))
    common.add_argument("--catalog", default=str(CATALOG))
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("list", "check", "prune", "hint"):
        sub.add_parser(name, parents=[common])
    for name in ("install", "uninstall"):
        sub.add_parser(name, parents=[common]).add_argument("pack")
    fetch_cmd = sub.add_parser("fetch", parents=[common])
    for name in ("repo", "path", "dest"):
        fetch_cmd.add_argument(name)
    args = parser.parse_args()
    home = Path(args.home).expanduser()

    if args.action == "hint":
        try:
            result = hint(json.load(sys.stdin), home, args.catalog)
        except Exception:
            return
        if result:
            print(json.dumps(result))
    elif args.action == "fetch":
        print(fetch(args.repo, args.path, Path(args.dest)))
    elif args.action == "list":
        print(json.dumps(list_packs(load(args.catalog), home), indent=2))
    elif args.action == "install":
        print(json.dumps(install(args.pack, home, args.catalog), indent=2))
    elif args.action == "uninstall":
        print(json.dumps(uninstall(args.pack, home, args.catalog), indent=2))
    elif args.action == "prune":
        print(json.dumps(prune(home, args.catalog), indent=2))
    else:
        errors = check(load(args.catalog), Path(args.catalog).resolve().parents[1])
        print("\n".join(errors) or "catalog ok")
        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
