---
name: cross-platform-per-os-commands
description: "A helper translates Windows command strings to Linux by token substitution; cross-platform says write each OS's command explicitly instead, because a substitution covers only the tokens someone thought of."
tags: [cross-platform, skill]
runs: 3
max_turns: 10
timeout_seconds: 480
allowed_tools: [Skill, Read]
expected_outcome: "The answer does not extend the substitution table; it has each OS's command written out explicitly (separate per-OS scripts or command strings chosen by OS), and explains that translation misses tokens such as cmd's `exit /b`."
---

Our test harness stores each external check as a Windows command string, for example
`check_schema.exe data\in.xml >nul 2>&1 || exit /b 7`. To run the same checks on our new Linux CI, a helper
rewrites the string before running it with `sh -c`: it swaps `\` for `/`, `>nul` for `>/dev/null` and drops
`.exe`. On Linux one check now reports exit code 2 where Windows reports 7, so a failure is classified wrongly.
How should we fix the helper?
