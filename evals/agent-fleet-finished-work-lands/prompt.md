---
name: agent-fleet-finished-work-lands
description: Finished same-file work in a rolling fix lane; agent-fleet enqueues a predecessor reviewed CLEAN at once (no hold, no landing "through" its successor), has the successor merge the REVIEWED head, applies the severity threshold at the round cap (a medium finding is a lead there, not a block), and treats a torn findings file as holding every branch it names instead of reading its last whole verdict.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: A is enqueued as its own pull request now (never held to land through B); B merges A's reviewed head c3d4e5f; X's capped round, with only a medium and a low finding, is CLEAN with two leads; Q's torn findings file (a truncated last line) holds R, whatever the whole records before the tear say. The old answers (hold A for B, block on the medium at the cap, read the last whole verdict of a torn file) fail.
---

My fix lane runs implementer groups from one queue; every finished branch becomes its own pull request through a merge queue, and each DONE branch is reviewed on the branch, with up to two finisher rounds. Three situations:

1. `Parser.cs` had too many defects for one group, so group A takes five and group B (`after: A`) the rest. A's implementer returned DONE at `a1b2c3d`; a finisher fixed its review findings at `c3d4e5f`, and the next round came back CLEAN at `c3d4e5f`. B has not started. My wave script holds A so that it lands through B's pull request, which will contain it.
2. Group X used both finisher rounds. Its third review round recorded exactly two findings: one `medium` (a misleading log message) and one `low` (a variable name).
3. Group Q's findings file, which our landing survey reads to decide whether Q's successor R may land (R is reviewed CLEAN and contains Q's head), has these lines; the file ends right after the last character shown:
```
{"kind":"start","round":1,"branch":"q","head":"9f8e7d6"}
{"kind":"verdict","round":1,"verdict":"CLEAN","findings":0}
{"kind":"start","round":2,"branch":"q","head":"5a4b3c2"}
{"kind":"finding","round":2,"sever
```

Use the `agent-fleet` skill. Answer briefly, then end with exactly these four lines, choosing one option on each:
`A: ENQUEUE-NOW` or `A: HOLD-FOR-B`
`B-MERGES: <sha>`
`X-ROUND-3: CLEAN` or `X-ROUND-3: FINDINGS`
`R: LANDS` or `R: HELD`
