---
name: devlog-correction-and-clock
description: Recording an overturned finding in a newest-first development log; devlog makes the correction a NEW entry that cites the old one (the old entry is never rewritten) and reads the header timestamp from the clock (`date`) instead of estimating it.
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The answer leaves entry 212 untouched and adds a new entry that names it as overturned, and takes the header time from the clock (a `date` command), not from "around 4:30"; it ends with OLD-ENTRY LEAVE and a TIMESTAMP line naming `date`.
---

Our repo keeps `DEVLOG.md`, newest entry first, headed `## Entry NNN — YYYY-MM-DD HH:MM TZ — Title`, one entry per commit. Entry 212, from last Tuesday, says the flaky upload test was caused by a race in the retry timer and was fixed by adding a lock. Today we proved that was wrong: the real cause is a temp directory shared between test runs, and the lock did nothing. I'm committing the real fix in a minute. It's around 4:30 in the afternoon here. My teammate says to fix entry 212 in place so nobody reads the wrong cause. Tell me exactly what to do to the devlog, in at most 8 lines, and end with exactly these two lines filled in:

OLD-ENTRY: <EDIT or LEAVE>   (what happens to entry 212's text)
TIMESTAMP: <exactly what goes in the new header's date-and-time field>
