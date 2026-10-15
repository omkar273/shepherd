#!/usr/bin/env python3
"""Report drift between this repo and the installed skills, as JSON.

--catalog instead reports the skills and plugins loaded in a repo's sessions
over the last 30 days. It also makes a patch for the repo's
.claude/settings.local.json. The patch sets "name-only" for each user, project,
and builtin skill that it does not keep. It keeps shepherd, the skills that the
routing table names, invoked skills, and --keep matches. It removes a
"name-only" override when no skill has that name. The patch also turns off
unused plugins that have a key. --patch prints only the patch.

--index prints a short description of each skill that the repo set to
name-only, for a SessionStart hook."""
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
INDEX_CHARS = 160
# Claude Code saves longer hook output to a file and gives the agent only a preview.
HOOK_CAP = 10_000
INDEX_HEADER = "These skills show only their names. If one fits the task, call it by name with the Skill tool."
HIDEABLE = ("user", "project", "builtin")
# Skills that come with Claude Code or the desktop app. They have no SKILL.md on disk.
BUILTIN_SKILLS = {
    "artifact-capabilities": "Runtime capabilities of a published Artifact page: live or connected data, saved and "
                             "shared state, who is viewing, files that people add or save.",
    "artifact-design": "Design rules for Artifacts. Load before you write any Artifact page, HTML or Markdown.",
    "artifact-diagramming": "Diagrams for Artifacts: when a diagram helps, how to show the real mechanism, and "
                            "inline SVG that reads in light and dark themes.",
    "claude-api": "Reference for the Claude API and Anthropic SDK: model IDs, pricing, parameters, streaming, tool "
                  "use, MCP, agents, caching, token counts, model migration.",
    "claude-in-chrome": "Control the user's Chrome browser: click, fill forms, take screenshots, read console logs. "
                        "Load before any mcp__claude-in-chrome__ tool.",
    "code-review": "Review the current diff, a PR, a branch, or a path for correctness bugs at an effort level. "
                   "--comment posts PR comments, --fix applies the findings.",
    "dataviz": "Load before you make any chart, graph, plot, dashboard, stat tile, or data visualization: chart "
               "form, colors, palettes, legends, axes, tooltips.",
    "design": "Make a design canvas Artifact: UI mockups, screen flows, wireframes, landing pages, posters, flyers, "
              "banners, one-pagers that the user edits by hand.",
    "fewer-permission-prompts": "Scan transcripts for common read-only Bash and MCP calls, then add an allowlist to "
                                "the project .claude/settings.json to reduce permission prompts.",
    "init": "Make a new CLAUDE.md file that documents the codebase.",
    "keybindings-help": "Customize keyboard shortcuts: rebind keys, add chord bindings, edit "
                        "~/.claude/keybindings.json.",
    "loop": "Run a prompt or slash command again on an interval, for example check the deploy every 5 minutes. "
            "Not for one-off tasks.",
    "plugin-authoring": "Make a mod in Claude Code: a live pane, band, status line, toast, or hook, written as a "
                        "plugin of function hooks. Load before you write a hooks module.",
    "run": "Start and drive this project's app to see a change work: run, start, or screenshot the app, or confirm "
           "a change in the real app, not only in tests.",
    "schedule": "Create, update, list, or run scheduled cloud agents (routines) on a cron schedule, or one run at a "
                "later time, such as 'remind me tomorrow'.",
    "security-review": "Do a security review of the pending changes on the current branch.",
    "simplify": "Review the changed code for reuse, simplification, and efficiency, then apply the fixes. Quality "
                "only: for bugs, use code-review.",
    "update-config": "Configure Claude Code in settings.json: hooks for automatic behavior ('whenever X', 'before "
                     "Y'), permissions ('allow X'), env vars, hook problems.",
    "workflow-authoring": "Reference for writing a Workflow tool script: script API, resume, quality patterns, "
                          "examples. Load before you write a workflow script.",
}


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


def skill_kind(home, repo, name):
    """"stale" when no skill folder or builtin has the name, so an override of it does nothing."""
    return ("plugin" if ":" in name
            else "user" if (home / ".claude" / "skills" / name).exists()
            else "project" if (repo / ".claude" / "skills" / name).exists()
            else "builtin" if name in BUILTIN_SKILLS
            else "stale")


def shorten(text, limit):
    """The text on one line, cut at a word boundary to at most limit chars."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:max(limit - 4, 0)].rsplit(" ", 1)[0] + " ..."


def hidden_index(home, repo):
    """A SessionStart hook text: a short description of each skill that the repo set to name-only."""
    try:
        overrides = json.loads((repo / ".claude" / "settings.local.json").read_text())["skillOverrides"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    entries = []
    for name in sorted(n for n, value in overrides.items() if value == "name-only"):
        kind = skill_kind(home, repo, name)
        if kind == "builtin":
            entries.append((name, BUILTIN_SKILLS[name]))
        elif kind in HIDEABLE:
            try:
                meta = skill_meta.read_skill_frontmatter((home if kind == "user" else repo) / ".claude" / "skills" / name)
            except (OSError, ValueError):
                continue
            entries.append((name, meta.get("description", "")))
    if not entries:
        return ""
    # Each line gets an equal part of the cap, so many skills get shorter text, not fewer lines.
    share = (HOOK_CAP - len(INDEX_HEADER)) // len(entries)
    text = "\n".join([INDEX_HEADER, *(f"- {name}: {shorten(description, min(INDEX_CHARS, share - len(name) - 5))}"
                                      for name, description in entries)])
    return text if len(text) <= HOOK_CAP else text[:HOOK_CAP].rsplit("\n", 1)[0]


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
        skills.append({"name": name, "kind": skill_kind(home, repo, name), "invocations": count})

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
    overrides = {name: None for name, value in current.items()
                 if value == "name-only" and skill_kind(home, repo, name) == "stale"}
    for name in (s["name"] for s in skills if s["kind"] in HIDEABLE):
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
            "keep": sorted(s["name"] for s in skills if s["kind"] in HIDEABLE and s["name"] in kept),
            "patch": patch, "app_plugins": app_plugins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--repo", default=".", help="repo for --catalog (default: here)")
    parser.add_argument("--keep", nargs="+", default=[], help="glob patterns of skills that keep their description")
    parser.add_argument("--patch", action="store_true", help="print only the settings patch")
    parser.add_argument("--index", action="store_true", help="print a short description of the repo's name-only skills")
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
