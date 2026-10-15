#!/usr/bin/env python3
"""Report drift between this repo and the installed skills, as JSON.

--catalog instead reports the skills and plugins loaded in a repo's sessions
over the last 30 days. It also makes a patch for the repo's
.claude/settings.local.json. The patch sets "name-only" for each user, project,
and builtin skill that it does not keep. It keeps shepherd, the skills that the
routing table names, invoked skills, and --keep matches. The patch also turns
off unused plugins that have a key. --patch prints only the patch.

--index prints keywords for each skill that the repo set to name-only, for a
SessionStart hook."""
import argparse
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[2]
RUNTIMES = {"claude": Path(".claude/skills"), "agents": Path(".agents/skills")}
USAGE_DAYS = 30
COMMAND_NAME = re.compile(r"<command-name>/([^<\s]+)</command-name>")
USAGE_MARKERS = ('"skill_listing"', '"tool_use"', "<command-name>")
INDEX_KEYWORDS = 6
STOPWORDS = set("a about an and any are as asks be by for from in is it its of on or that the this to "
                "use used user uses when wants with you your".split())


def remote_head(url):
    out = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=20)
    return out.stdout.split()[0] if out.returncode == 0 and out.stdout else ""


def scan_transcript(path, loaded, used):
    """Add the skill names a transcript loaded, and what it invoked, to the sets."""
    with open(path, encoding="utf-8", errors="replace") as lines:
        for line in lines:
            if not any(marker in line for marker in USAGE_MARKERS):
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            attachment = entry.get("attachment") or {}
            if attachment.get("type") == "skill_listing":
                loaded.update(attachment.get("names") or [])
            message = entry.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if entry.get("type") == "user" and isinstance(content, str):
                used.update(COMMAND_NAME.findall(content))
            if entry.get("type") != "assistant" or not isinstance(content, list):
                continue
            for block in content:
                tool, tool_input = block.get("name", ""), block.get("input") or {}
                if tool == "Skill":
                    used[tool_input.get("skill")] += 1
                elif tool in ("Agent", "Task"):
                    used[tool_input.get("subagent_type")] += 1
                elif tool.startswith("mcp__plugin_"):
                    used[tool] += 1


def routed_skills():
    """shepherd, and the skills that the routing table in its SKILL.md sends work to."""
    text = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()
    table = text.split("| Situation |", 1)[1].split("\n\n", 1)[0]
    return {"shepherd", *re.findall(r"`([a-z0-9-]+)`", table)}


def hidden_index(home, repo):
    """A SessionStart hook text: keywords for each skill that the repo set to name-only."""
    try:
        overrides = json.loads((repo / ".claude" / "settings.local.json").read_text())["skillOverrides"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    lines = []
    for name in sorted(n for n, value in overrides.items() if value == "name-only"):
        folder = next((base / name for base in (home / ".claude" / "skills", repo / ".claude" / "skills")
                       if (base / name / "SKILL.md").exists()), None)
        if not folder:
            continue
        try:
            description = skill_meta.read_skill_frontmatter(folder).get("description", "")
        except (OSError, ValueError):
            continue
        words = re.findall(r"[a-z][a-z0-9-]+", description.lower())
        keywords = list(dict.fromkeys(w for w in words if w not in STOPWORDS))[:INDEX_KEYWORDS]
        lines.append(f"- {name}: {', '.join(keywords)}")
    if not lines:
        return ""
    return "\n".join(["These skills show only their names. If one fits the task, call it by name with the Skill tool.",
                      *lines])


def usage_report(home, repo, keep=()):
    """Names and counts only: no transcript text leaves this function."""
    projects = home / ".claude" / "projects"
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo))
    folders = [projects / slug, *projects.glob(f"{slug}--claude-worktrees-*")]
    cutoff = time.time() - USAGE_DAYS * 86400
    files = [f for folder in folders for f in folder.glob("**/*.jsonl") if f.stat().st_mtime >= cutoff]
    loaded, used = set(), Counter()
    for path in files:
        scan_transcript(path, loaded, used)

    skills = []
    for name in sorted(loaded):
        bare = name.split(":", 1)[-1]
        count = used[name] + (used[bare] if bare != name and bare not in loaded else 0)
        kind = ("plugin" if ":" in name
                else "user" if (home / ".claude" / "skills" / name).exists()
                else "project" if (repo / ".claude" / "skills" / name).exists()
                else "builtin")
        skills.append({"name": name, "kind": kind, "invocations": count})

    try:
        installed = json.loads((home / ".claude" / "plugins" / "installed_plugins.json").read_text())
        keys = {key.split("@")[0]: key for key in installed["plugins"]}
    except (OSError, ValueError, KeyError, TypeError):
        keys = {}
    plugins = []
    for plugin in sorted({s["name"].split(":")[0] for s in skills if s["kind"] == "plugin"}):
        count = sum(s["invocations"] for s in skills if s["name"].startswith(f"{plugin}:"))
        # Plugin agents (plugin:agent) and MCP tools (mcp__plugin_<plugin>_...) count too.
        count += sum(n for key, n in used.items() if key and key not in loaded
                     and (key.startswith(f"{plugin}:") or key.startswith(f"mcp__plugin_{plugin}_")))
        plugins.append({"name": plugin, "key": keys.get(plugin), "invocations": count})

    patterns = [*routed_skills(), *keep]

    def listed(name):
        return any(fnmatch.fnmatchcase(n, p) for p in patterns for n in (name, name.split(":", 1)[-1]))

    # Bare names, so that a used plugin skill also keeps a same-named copy.
    kept = {s["name"].split(":", 1)[-1] for s in skills if s["invocations"] or listed(s["name"])}
    try:
        current = json.loads((repo / ".claude" / "settings.local.json").read_text())["skillOverrides"]
    except (OSError, ValueError, KeyError, TypeError):
        current = {}
    overrides = {}
    for name in (s["name"] for s in skills if s["kind"] != "plugin"):
        if name in kept and current.get(name) == "name-only":
            overrides[name] = None
        elif name not in kept and name not in current:
            overrides[name] = "name-only"
    plugins_off, app_plugins = {}, {}
    for plugin in plugins:
        names = [s["name"] for s in skills if s["name"].startswith(f"{plugin['name']}:")]
        if plugin["invocations"] or any(map(listed, names)):
            continue
        if plugin["key"]:
            plugins_off[plugin["key"]] = False
        else:
            app_plugins[plugin["name"]] = len(names)
    patch = {key: value for key, value in (("skillOverrides", overrides), ("enabledPlugins", plugins_off)) if value}

    return {"repo": str(repo), "days": USAGE_DAYS,
            "sessions": sum(1 for f in files if f.parent in folders),
            "skills": skills, "plugins": plugins,
            "keep": sorted(s["name"] for s in skills if s["kind"] != "plugin" and s["name"] in kept),
            "patch": patch, "app_plugins": app_plugins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--repo", default=".", help="repo for --catalog (default: here)")
    parser.add_argument("--keep", nargs="+", default=[], help="glob patterns of skills that keep their description")
    parser.add_argument("--patch", action="store_true", help="print only the settings patch")
    parser.add_argument("--index", action="store_true", help="print the keywords of the repo's name-only skills")
    args = parser.parse_args()
    home = Path(args.home).expanduser()
    if args.index:
        print(hidden_index(home, Path(args.repo).resolve()), end="")
        return
    if args.catalog:
        report = usage_report(home, Path(args.repo).resolve(), args.keep)
        print(json.dumps(report["patch"]) if args.patch else json.dumps(report, indent=2))
        return
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

    report["packs_installed"] = catalog.installed_packs(home)
    report["packs_available"] = [p for p in catalog.load(catalog.CATALOG)["packs"]
                                 if p not in report["packs_installed"]]

    counts = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    report["summary"] = ", ".join(f"{k}: {n}" for k, n in counts.items()) + \
        f", days since update: {report['days_since_update']}"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
