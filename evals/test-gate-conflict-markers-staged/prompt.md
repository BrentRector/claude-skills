---
name: test-gate-conflict-markers-staged
description: A pre-commit check against committed conflict markers; test-gate says to assert, between git add and git commit, on the staged content with git grep --cached and on the OUTPUT of git diff --cached --check (grepped for "conflict marker", never its exit code), backed by a repo-wide marker test seen to fail once.
tags: [test-gate, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The check runs on what is STAGED (git grep --cached for the marker lines) and reads the output of git diff --cached --check for "conflict marker" instead of trusting its exit code.
---

My agents commit WIP checkpoints in their worktrees with `git add -A` then `git commit -m "WIP"`, and they resolve merge conflicts by hand when they merge another agent's branch. Last week a script with unresolved conflict hunks was committed and three green test runs let it through, because no test imports that script. I want a check each agent runs after `git add` and before `git commit` so this can't happen again. Give me the exact commands, at most 5 lines. Use the `test-gate` skill.
