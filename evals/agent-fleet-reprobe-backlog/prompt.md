---
name: agent-fleet-reprobe-backlog
description: The first steps of an implementer brief over stale backlog items; agent-fleet says the implementer first re-runs each item's repro on its own build, and an item that no longer reproduces is DISCHARGED with the evidence (command, output, commit) and sent to a refuter like any closing verdict, not fixed or silently skipped.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: The implementer re-runs each item's repro on its own build before fixing; a non-reproducing item is discharged with recorded evidence (command, output, commit) and that discharge goes to an independent refuter.
---

I'm dispatching one implementer agent at five defect notes from our backlog. They were filed three to six weeks ago, each with a repro command and a code site, and several fix waves have landed since. Write the "First steps" section of the implementer's brief, at most 5 lines. End with exactly one line of the form `IF IT NO LONGER REPRODUCES: <what happens to that note>`. Use the `agent-fleet` skill.
