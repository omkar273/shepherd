#!/usr/bin/env python3
"""SessionStart hook: one line when skills were last updated over 7 days ago.

Reads ~/.claude/shepherd.json. Silent when the state is fresh, missing or
unreadable. Never fails, never touches the network."""
import argparse
import datetime
import json
from pathlib import Path

STALE_AFTER_DAYS = 7


