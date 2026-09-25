---
name: automating-agent-guardrails-guard-design
description: Designing a guard hook for "no git stash / land main only via the script"; automating-agent-guardrails supplies the two decisions a baseline builder got wrong - the guard fails OPEN on its own errors, and a repo-policy rule is scoped to this repository (git common dir), so a push to main in another repo passes.
tags: [automating-agent-guardrails, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The design fails open (an internal error or unparseable input allows the call, with a stderr note) and scopes the push rule to this repository, so `git -C <another repo> push origin main` is allowed; the answer ends with ON-ERROR ALLOW and OTHER-REPO ALLOWED.
---

Agents in my repo keep breaking two rules: never run `git stash`, and only `bash scripts/land.sh` may update `main`. I want a Claude Code PreToolUse hook (Python, for Bash and PowerShell) that enforces both. Claude sessions here also work in other repositories now and then. Before any code, give me the design decisions in at most 8 bullets, and end with exactly these two lines filled in:

ON-ERROR: <ALLOW or BLOCK>   (what the hook does when it cannot parse the tool input, a config file is corrupt, or it crashes)
OTHER-REPO: <BLOCKED or ALLOWED>   (a session started in my repo runs `git -C D:/work/vendor-lib push origin main`)
