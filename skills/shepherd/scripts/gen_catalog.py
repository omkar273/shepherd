#!/usr/bin/env python3
"""Regenerate the skill catalog table in README.md from every skill's
SKILL.md frontmatter and .origin.yaml. Replaces only the content between
the <!-- CATALOG:START --> and <!-- CATALOG:END --> markers."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

START_MARKER = "<!-- CATALOG:START -->"
END_MARKER = "<!-- CATALOG:END -->"


def collect_skills(skills_dir):
    skills_dir = Path(skills_dir)
    rows = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        frontmatter = skill_meta.read_skill_frontmatter(skill_dir)
        origin = skill_meta.read_origin(skill_dir)
        rows.append({
            "name": frontmatter.get("name", skill_dir.name),
            "description": frontmatter.get("description", ""),
            "origin": origin.get("origin", "vendored"),
            "source_repo": origin.get("source_repo", "local"),
        })
    return rows


def render_table(rows):
    lines = ["| Skill | Description | Source |", "| --- | --- | --- |"]
    for row in rows:
        description = row["description"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| `{row['name']}` | {description} | {row['source_repo']} |")
    return "\n".join(lines)


