#!/usr/bin/env python3
"""shepherd's skill catalog: packs of skills pinned to exact commits, fetched on demand."""
import argparse
import hashlib
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
FIELDS = ("name", "repo", "path", "ref", "sha256", "license", "decision")


def content_hash(folder):
    folder = Path(folder)
    files = [p for p in folder.rglob("*") if p.is_file() and ".git" not in p.relative_to(folder).parts]
    digest = hashlib.sha256()
    for file in sorted(files, key=lambda p: p.relative_to(folder).as_posix()):
        digest.update(file.relative_to(folder).as_posix().encode() + b"\0" + file.read_bytes() + b"\0")
    return digest.hexdigest()


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
            if not re.fullmatch(r"[0-9a-f]{40}", skill.get("ref", "")):
                errors.append(f"{where}: ref must be a 40-character commit sha")
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


def fetch(repo, ref, path, dest):
    with tempfile.TemporaryDirectory() as work:
        git = lambda *args: subprocess.run(["git", "-C", work, *args], capture_output=True)
        git("init", "-q")
        if git("fetch", "-q", "--depth", "1", repo, ref).returncode != 0:
            git("fetch", "-q", repo, "+refs/*:refs/remotes/source/*")
        archive = git("archive", "--format=tar", ref, path)
        if archive.returncode != 0:
            sys.exit(f"catalog: cannot read {path} at {ref} from {repo}")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(work + "/out", filter="data")
        shutil.move(Path(work, "out", path), dest)


def cache_dir(home, skill):
    return home / ".shepherd" / "catalog" / f"{skill['name']}@{skill['ref'][:7]}"


def install(pack, home, catalog_path):
    skills = load(catalog_path)["packs"][pack]["skills"]
    staged = []
    for skill in skills:
        cache = cache_dir(home, skill)
        if cache.is_dir() and content_hash(cache) == skill["sha256"]:
            continue
        stage = Path(tempfile.mkdtemp()) / skill["name"]
        fetch(skill["repo"], skill["ref"], skill["path"], stage)
        if content_hash(stage) != skill["sha256"]:
            sys.exit(f"catalog: {skill['name']} does not match its pinned hash; nothing installed")
        staged.append((stage, cache))

    report = {"fetched": [], "linked": [], "backed_up": []}
    for stage, cache in staged:
        shutil.rmtree(cache, ignore_errors=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(stage, cache)
        report["fetched"].append(cache.name)
    for skill in skills:
        cache = cache_dir(home, skill)
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
    keep = {cache_dir(home, s).name for p in installed_packs(home) if p in packs for s in packs[p]["skills"]}
    root = home / ".shepherd" / "catalog"
    removed = [d.name for d in sorted(root.iterdir()) if d.name not in keep] if root.is_dir() else []
    for name in removed:
        shutil.rmtree(root / name)
    return removed


def list_packs(data, home):
    installed = installed_packs(home)
    return {pack: {"domain": spec.get("domain", ""), "skills": [s["name"] for s in spec.get("skills", [])],
                   "installed": pack in installed}
            for pack, spec in data.get("packs", {}).items()}


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", default=str(Path.home()))
    common.add_argument("--catalog", default=str(CATALOG))
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list", parents=[common])
    sub.add_parser("check", parents=[common])
    sub.add_parser("prune", parents=[common])
    for name in ("install", "uninstall"):
        sub.add_parser(name, parents=[common]).add_argument("pack")
    hash_cmd = sub.add_parser("hash", parents=[common])
    hash_cmd.add_argument("folder")
    fetch_cmd = sub.add_parser("fetch", parents=[common])
    for name in ("repo", "ref", "path", "dest"):
        fetch_cmd.add_argument(name)
    args = parser.parse_args()
    home = Path(args.home).expanduser()

    if args.action == "hash":
        print(content_hash(args.folder))
    elif args.action == "fetch":
        fetch(args.repo, args.ref, args.path, Path(args.dest))
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
