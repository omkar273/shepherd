import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gen_catalog
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[3]
README = SKILLS_DIR.parent / "README.md"

MATT = {
    "ask-matt", "codebase-design", "domain-modeling", "grill-with-docs", "implement",
    "implement-spec", "improve-codebase-architecture", "pr", "prototype", "research",
    "retro", "setup-matt-pocock-skills", "to-spec", "to-tickets", "triage", "wayfinder",
    "wizard", "grill-me", "grilling", "handoff", "teach", "to-questionnaire", "wait-what",
    "writing-for-agents", "git-guardrails-claude-code", "setup-pre-commit",
}
OTHERS = {"frontend-design", "ui-ux-pro-max", "graphify"}


