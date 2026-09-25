## Agent guardrails

Paste this section into the project's `CLAUDE.md` and fill in the `<...>` parts. It is the rule half of the
guardrails. The hooks and the readiness check are the enforcement half, and their output only means something to a
session that has this rule loaded. It loads every session even when a hook fails.

- **A guard-hook block is the rule speaking.** Follow its `Instead:` line. Never rephrase, split, encode or move the
  command to get past the guard. If the rule looks wrong for this case, stop and ask the owner.
- **Session start: act on the readiness check.** It prints one line per capability: OK, REPAIRED, N/A, TODO or
  ASK-OWNER. For EVERY ASK-OWNER line, ask the owner one AskUserQuestion, before other work, offering the line's
  On-yes step. Never skip one silently. Do every TODO line this session. If the check says it FAILED to run, tell the
  owner and run it by hand.
- **Owner-only or billed steps are asked at their trigger, never skipped:** <`/code-review ultra` before pushing a
  landing of several commits>; <`claude plugin eval . --no-publish` before pushing a skill or agent edit>.
- **Dispatch subagents by role.** Use `agentType` in workflow scripts and `subagent_type` with the Agent tool. Never
  set model or effort per call: the role definition in `.claude/agents/` is their one home.
- **A new or edited role definition is live only after a restart.** Then prove it with a smoke dispatch (the
  readiness check's TODO line says how).
- **Navigate code with the LSP tool** (definition, references, symbols) before grep when the readiness check shows
  the language server OK.
- **Before a landing push, run the review step** <command or skill>. A finding blocks the push.
- **A skill or agent edit ships with its eval.** Run `claude plugin eval` for the changed cases before pushing, and
  treat a shrinking delta as a regression.
