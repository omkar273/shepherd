---
name: catalog
description: List, install, or remove a pack of skills from the shepherd catalog. The user starts it with /catalog.
disable-model-invocation: true
---

# Catalog

A pack is a set of skills for one domain (SEO, design, video). The catalog
fetches a pack from its source repos and links it into `~/.claude/skills`.
A pack costs no context until you install it.

`<shepherd>` is `~/.claude/skills/shepherd`. The catalog needs the full clone.
First run `test -f <shepherd>/../../catalog/catalog.json`. If it fails, tell
the user that the catalog comes with the full setup in the README, and stop.

Run `python3 <shepherd>/scripts/catalog.py <action>`:

- **List:** `list` shows each pack, its skills, and whether the pack is
  installed.
- **Install:** say which skills the pack adds. Wait for a yes. Then run
  `install <pack>`, and report what it linked and backed up. If a new skill
  does not appear in the session, say: restart Claude Code to load it.
- **Remove:** `uninstall <pack>` removes only the links of the pack.
- **Clean the cache:** run `prune` only when the user asks.
- **Add or remove a catalog skill:** follow `<shepherd>/curate.md`.

A hook prints a line when a prompt matches the cues of a pack that is not
installed. Offer that pack once. Install it only if the user says yes.
