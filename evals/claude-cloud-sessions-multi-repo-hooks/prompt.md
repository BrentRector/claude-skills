---
name: claude-cloud-sessions-multi-repo-hooks
description: With two repos attached, a cloud session starts in /home/user and loads no repo's hooks; claude-cloud-sessions supplies the measured cause and the user-level SessionStart shim written by the setup script.
tags: [claude-cloud-sessions, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: Explains that multi-repo sessions start in the parent (/home/user) and load no repo .claude/settings.json hooks, and fixes it with a user-level SessionStart hook shim written into the VM's ~/.claude/settings.json by the environment setup script.
---

In Claude Code on the web (cloud sessions) I have a SessionStart hook in `app-repo/.claude/settings.json` that initializes a submodule. It works when `app-repo` is the only repository attached. When I attach a second repository (`shared-lib`) to the same session, the hook never runs: the submodule stays empty and two tests go red. Why, and what's the fix that keeps the hook per-session? Answer in under 120 words.
