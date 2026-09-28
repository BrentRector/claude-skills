---
name: devlog-commit-hook
description: Registering a PreToolUse hook that catches a commit without a staged devlog entry; devlog registers it with NO `if` filter, because a `Bash(git commit*)` if-filter misses chained commits such as `git add -A && git commit`, and the hook ASKS for confirmation rather than denying.
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The registration has no `if` filter (the script itself finds `git commit` anywhere in the command) and the hook's decision is ask, not deny; the answer ends with IF-FILTER NONE and DECISION ASK.
---

Our agents are supposed to add a `DEVLOG.md` entry with every commit, and they keep forgetting. I want a Claude Code PreToolUse hook (a Python script) that catches a commit with no devlog change staged. To keep it cheap, register it with the hook `if` field so it only runs for commit commands. Give me the `.claude/settings.json` hooks block and say in at most 5 bullets what the script does. End with exactly these two lines filled in:

IF-FILTER: <the value of the `if` field you registered, or NONE>
DECISION: <DENY or ASK>   (what the hook returns when no devlog change is staged)
