## 3. The session-start readiness check

1. Copy `readiness_check.py`, `session_start.py` and `readiness.json`, deleting any config section you have not
   adopted, and register SessionStart (`templates/settings.json`). Run `readiness_check.py --ci` and `--selftest` in
   CI.
2. Every capability is checked each session, and each line ends in one status:
   - **OK**: present and working.
   - **REPAIRED**: fixed with no permission needed, such as starting the telemetry receiver.
   - **N/A**: does not apply here, with the reason.
   - **TODO**: needs no permission, so Claude does it this session.
   - **ASK-OWNER**: needs permission or an owner-only action, and carries the exact On-yes step.
3. Repair automatically only what needs no permission. Anything that edits committed files, installs software,
   changes user settings, or is owner-only or billed is an ASK-OWNER line.
4. **Put the asking rule in `CLAUDE.md`**: paste `templates/CLAUDE-guardrails.md`. Every ASK-OWNER line becomes
   one AskUserQuestion at session start, before other work, and none is skipped silently. Hook output alone is not
   enough, because a rule that exists only there disappears when the hook fails. *(Practice — not yet validated: no recorded silent skip or measured effect.)*
5. **It fails open at every level**, including config loading. Any failure becomes an ASK-OWNER line saying "run it
   by hand", never a traceback or a non-zero exit.
6. **It detects the environment.** With `CLAUDE_CODE_REMOTE=true` (cloud) or `CI` set, machine-local capabilities
   (telemetry receiver, LSP install, smoke proof, recurring owner commands) are N/A with the reason. They are never
   asked about and never "repaired" on a VM that is thrown away.
7. **Recurring owner-only commands**, such as a weekly `/skill-doctor`, are `recurring` entries with a timestamp
   stamp. When one is due it becomes ASK-OWNER. After the owner runs it: `--stamp <id>`.
8. **Owner-only or billed steps that belong to a trigger** (only those the owner named; the template's entries are
   examples), such as `/code-review ultra` before a landing push or
   paid plugin evals before pushing a skill edit, go in `ask_at_trigger`. They are listed every session and asked
   when the trigger arrives, never skipped.
