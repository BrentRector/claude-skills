---
name: agent-fleet-orientation
description: Writing the orientation instruction of an implementer brief; agent-fleet says to orient in ONE call with the bundled references/orient.py (outline, covering tests, what closed notes learned about each file) before reading any source, derived fresh each run, instead of re-surveying or pre-generating agent-written codebase maps.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: The instruction tells the implementer to run the bundled orient.py on the files its defects name (with --notes pointing at the issue notes) BEFORE reading any source, explains that it surfaces what earlier closed fixes learned about each file, and does not propose agents writing a maintained codebase map.
---

Each wave, my implementer agents spend a large share of their turns re-reading and grepping the same files earlier waves already worked in. Issue notes live in `docs/issues/*.md` (front matter `id`, `status: open|landed`; landed notes describe the fix and its code site). Write the "Orientation" instruction for the implementer brief, in at most 5 lines, including the exact command. Use the `agent-fleet` skill.
