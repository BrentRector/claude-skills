---
name: agent-fleet-brief-limits
description: Writing the limits block of a dispatch brief; agent-fleet supplies the measured turn cap (~150-160 for read-only agents, return SPLIT at the cap), per-item JSONL checkpoints written the moment each item is decided, and a graceful STOP file checked before each step.
tags: [agent-fleet, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The block sets a turn cap around 150-160 (checkpoint and return SPLIT at the cap), appends one JSONL line per decided item immediately and skips already-decided items on start, and checks a STOP file before each step.
---

I'm about to dispatch 30 read-only analysis subagents in a long campaign (each judges ~20 items). Write the "Limits and checkpointing" block of their dispatch brief: the turn cap, how they checkpoint, and how I stop them gracefully. At most 6 bullet lines, concrete numbers and file names, no preamble. Use the `agent-fleet` skill for this.
