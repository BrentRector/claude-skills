---
name: devlog-insert-entry
description: Adding an entry to a long newest-first single-file devlog from a script; devlog never hand-writes a splice — it migrates the file once to one file per entry (`devlog.py migrate`) and adds each entry with the bundled references/devlog.py `new` (a pending file, numbered and clock-stamped at enqueue by `stamp`).
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob]
expected_outcome: The answer uses the bundled devlog.py (`new`, after a one-time `migrate`) rather than writing its own insertion code.
---

Our `DEVLOG.md` has 1,400 entries, newest first. It opens with a title and an ordering note that quotes the header format `## Entry NNN — YYYY-MM-DD HH:MM TZ — Title`, and then the entries. The file is CRLF and has no `.gitattributes` rule. Our agents add an entry with every commit, and last week one of them spliced its entry into the middle of the ordering note and another rewrote all 36,000 lines as LF. Give me the exact command or code an agent should run to add the next entry from a file `entry.md` that holds its title and body, in at most 12 lines.
