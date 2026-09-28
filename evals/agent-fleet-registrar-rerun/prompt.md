---
name: agent-fleet-registrar-rerun
description: Briefing the agent that files leads from implementer reports as work notes; agent-fleet says this registrar runs each lead's given repro ONCE on its own build and records the result before filing, writes a fresh probe only for a lead without a repro or code site, and never copies a measurement or quoted citation forward unverified.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: The procedure runs each lead's given repro once on the agent's own build and records the result before filing, probes fresh only when a lead lacks a repro, and verifies quoted citations rather than copying them forward.
---

After each wave, one agent reads the six implementer reports and files every "lead" in them (a defect the implementer noticed but did not fix) as a work note in `docs/issues/`. Each lead carries a repro command, a `file:line` code site, and often a quoted clause from the spec. There are about 40 leads per wave, and I want this agent cheap. Write the procedure section of its brief, at most 6 lines. Use the `agent-fleet` skill.
