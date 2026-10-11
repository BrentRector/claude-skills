---
name: devlog-commit-hook
description: Registering a PreToolUse hook that catches a pull request whose branch adds no devlog entry; devlog registers it with NO `if` filter, because a `Bash(gh pr create*)` if-filter misses chained commands such as `git push -u origin HEAD && gh pr create`, and the hook ASKS for confirmation rather than denying.
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The registration has no `if` filter (the script itself finds `gh pr create` anywhere in the command) and the hook's decision is ask, not deny; the answer ends with IF-FILTER NONE and DECISION ASK.
---

Our agents are supposed to add one devlog entry file (under `devlog/`) with every pull request, and they keep forgetting. I want a Claude Code PreToolUse hook (a Python script) that catches `gh pr create` on a branch that adds no devlog entry. To keep it cheap, register it with the hook `if` field so it only runs for `gh pr create` commands. Give me the `.claude/settings.json` hooks block and say in at most 5 bullets what the script does. End with exactly these two lines filled in:

IF-FILTER: <the value of the `if` field you registered, or NONE>
DECISION: <DENY or ASK>   (what the hook returns when the branch adds no devlog entry)
