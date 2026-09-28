---
name: devlog-insert-entry
description: Adding an entry to a long newest-first devlog from a script; devlog inserts with the bundled references/devlog.py `new` (number = top + 1, clock timestamp, line endings preserved, collision refused) instead of a hand-written splice.
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob]
expected_outcome: The answer uses the bundled devlog.py `new` subcommand to insert the entry rather than writing its own insertion code.
---

Our `DEVLOG.md` has 1,400 entries, newest first. It opens with a title and an ordering note that quotes the header format `## Entry NNN — YYYY-MM-DD HH:MM TZ — Title`, and then the entries. The file is CRLF and has no `.gitattributes` rule. Our agents add an entry with every commit, and last week one of them spliced its entry into the middle of the ordering note and another rewrote all 36,000 lines as LF. Give me the exact command or code an agent should run to add the next entry from a file `entry.md` that holds its title and body, in at most 12 lines.
