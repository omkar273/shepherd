#!/usr/bin/env python3
"""shepherd's skill catalog: packs of skills pinned to exact commits, fetched on demand."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

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
    hash_cmd = sub.add_parser("hash", parents=[common])
    hash_cmd.add_argument("folder")
    args = parser.parse_args()
    home = Path(args.home).expanduser()

    if args.action == "hash":
        print(content_hash(args.folder))
    elif args.action == "list":
        print(json.dumps(list_packs(load(args.catalog), home), indent=2))
    else:
        errors = check(load(args.catalog), Path(args.catalog).resolve().parents[1])
        print("\n".join(errors) or "catalog ok")
        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
