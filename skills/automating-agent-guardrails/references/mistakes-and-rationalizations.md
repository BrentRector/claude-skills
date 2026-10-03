## Common mistakes (each made by a baseline agent without this skill)

| Mistake | What happened | Instead |
|---|---|---|
| Guard fails closed (`except: return 2`, `\|\| exit 2`, "unparseable git command → block") | Malformed JSON blocked the call; a crash or a missing Python would block every tool in every session | Exit 0 on every internal error; `--selftest` asserts it |
| Push rule scoped to the branch name | `git -C <other repo> push origin main` blocked; a "pre-push guard not installed" check blocked feature pushes in unrelated repos | `scope: "repo"` (git common dir vs `$CLAUDE_PROJECT_DIR`); test with an unrelated repo |
| Read-only role enforced by a settings hook reading `agent_type` | Missing field → treated as main session → write allowed | `hooks:` in the role's own frontmatter |
| `maxTurns` on one role | Four of five roles had no turn cap | `maxTurns` on every role; `readiness_check.py --ci` fails without it |
| No 1-hour cache, or a checker that rejects it | Gate-blocked roles re-wrote their whole context after each wait | `cacheTtl: 1h` on every `long_wait` role; measure with §4, don't argue billing from memory |
| No restart and smoke dispatch | Role definitions shipped unproven; no one knew they load only at session start | Restart, one smoke agent per role, `--stamp roles-smoke` |
| No N/A status or environment detection | A cloud session would start a receiver and ask to install tools on a throwaway VM | Detect `CLAUDE_CODE_REMOTE` / `CI`; N/A with reason |
| The ask rule only in hook output | No `CLAUDE.md` rule; a failed hook would take the rule with it | The `CLAUDE.md` section from the template |
| Config loaded outside the try | Corrupt config → traceback, exit 1, no line asking anyone anything | Whole `main` inside the fail-open path |

## Rationalizations

| Excuse | Reality |
|---|---|
| "Failing closed is safer." | For a workflow guard, failing closed wedges the owner's whole Claude Code on one bug. The server and CI are the backstop. |
| "Blocking pushes to main anywhere is harmless." | It blocks legitimate work in every other repo the session touches, and it teaches agents to work around the guard. |
| "The 1-hour cache costs more per write." | It costs more per *write*. A role that waits past 5 minutes rewrites its whole context each time. Measure with telemetry, and roll back if cost per unit rises. |
| "A settings-level hook can work out the role." | Only if every dispatch path fills in `agent_type`. A frontmatter hook needs no identification. |
| "Every environment difference is a question for the owner." | A capability that cannot apply is N/A. Asking about it is noise the owner learns to ignore. |
| "The hook output already tells Claude to ask." | Only on the days the hook works. The rule belongs in `CLAUDE.md`. |
