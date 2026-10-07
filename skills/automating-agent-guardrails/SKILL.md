---
name: automating-agent-guardrails
description: Use when a project's rules for Claude agents keep getting broken or skipped (forbidden git commands, direct pushes to a protected branch, read-only reviewers that write, owner-approval steps nobody asks about), or when setting up or auditing Claude Code guard hooks, `.claude/agents` role definitions, a session-start readiness check, OpenTelemetry cost tracking or LSP code navigation for a repository.
---

# Automating agent guardrails

Agents forget rules they have to remember, especially under pressure or in a subagent that never saw the prose.
This skill makes a project's agent rules **structural**, so the harness enforces them through hooks and role
definitions, and **automatic**, so a check runs at every session start and anything that needs the owner becomes a
question instead of a silent skip.

Every item in the contracts below exists because a capable agent building the same piece without it got that item
wrong. **Violating the letter of a contract is violating its spirit.**

## What gets installed

Copy the scripts into the project (`.claude/hooks/`). Don't reference the plugin cache: CI and cloud sessions run
them from the clone. Every script runs as `python <script>` and has a `--selftest`.

| Piece | In the project | From this skill |
|---|---|---|
| Guard hook | `.claude/hooks/guard_commands.py`, `guard-rules.json`; PreToolUse in `.claude/settings.json` | `scripts/guard_commands.py`, `templates/guard-rules.json`, `templates/settings.json` |
| Role agents | `.claude/agents/*.md`, `.claude/hooks/readonly_guard.py` | `templates/agents/`, `scripts/readonly_guard.py` |
| Readiness check | `.claude/hooks/readiness_check.py`, `readiness.json`, `session_start.py`; SessionStart in settings; a `CLAUDE.md` section | `scripts/readiness_check.py`, `templates/readiness.json`, `templates/session_start.py`, `templates/CLAUDE-guardrails.md` |
| Cost telemetry | `.claude/hooks/otlp_sink.py`, `usage_report.py`; env in the USER settings `~/.claude/settings.json` (a project's settings cannot enable telemetry) | `scripts/` |

## 1. Guard hooks that block forbidden commands

- Encode only the rules the owner stated; a rule you think is missing is a proposal, so ask.
- One rule per forbidden command in `guard-rules.json`: `pattern`, `reason`, `instead`, `block` and `allow` examples.
- `"scope": "repo"` on every rule that encodes this repository's policy.
- Register the guard for every shell tool (`"matcher": "Bash|PowerShell"`), plain `python ...` command, no `|| exit 2`.
- The guard exits 2 with an `Instead:` message, **fails OPEN** on every internal error, writes UTF-8 stderr, and has a CI
  self-test that includes an unrelated repo.
- Run `python .claude/hooks/guard_commands.py --selftest --settings .claude/settings.json` until GREEN and add it to CI;
  report CI as unproven until you have seen a green run. Never use `permissions.deny` for these rules.

Read `references/guard-hooks.md` before writing or auditing any guard rule, hook registration or the guard's self-test (it holds the full contract and the reason for each item).

### A hook can also GRANT, within a scope a settings rule cannot express

A permission rule sees the command text, never the working directory or the resolved paths, so "allow `git rm -r`
inside an agent's worktree, nowhere else" cannot be a settings rule. A PreToolUse hook can return
`permissionDecision: allow` for exactly that shape — one command, run in a directory under the worktrees root, every
path inside it, no `--force` — and no decision for anything else, so the harness's own safety classifier and every
deny hook keep their say. The bar for a grant is the mirror of a guard's: its self-test must show every neighbour
that is NOT allowed (the main checkout, a path that escapes, a chain, `--force`), because its failure branch is a
permission that should not have been given. *Why: a safety classifier refused a subagent's whole-tree deletion as
irreversible — correct for an unscoped command, wrong on a branch where every removal is one commit from recovery —
and the alternative, a person performing the step per wave, cannot run unattended.* Pair it with the owner's
never-lose-work rule in the cleanup script: remove a worktree only when its work is committed and landed, never one
that is dirty, locked, recent or unlanded.

## 2. Role agent definitions

- Every role sets `model`, `effort` and `maxTurns`; mechanical roles (`chore`, read-only `locator`) get a cheaper model and lower effort.
- Every role that waits on gates, builds or CI sets `experimental:` / `cacheTtl: 1h`; roles that never wait keep the default.
- Read-only roles carry `readonly_guard.py` in their OWN frontmatter `hooks:`, never in project settings keyed on `agent_type`.
- Select roles by name (`agentType` / `subagent_type`); never set `model` or effort per call.
- Restart, then prove each role with a smoke agent and `--stamp roles-smoke`; roll a role back up if its quality metric drops.

Read `references/role-agents.md` before creating, editing or auditing any role definition, and before dispatching a role smoke test.

## 3. The session-start readiness check

- Every capability gets one status each session: OK, REPAIRED, N/A (with reason), TODO, or ASK-OWNER (with the exact On-yes step).
- Repair automatically only what needs no permission; anything else is ASK-OWNER.
- Paste `templates/CLAUDE-guardrails.md` into `CLAUDE.md`: every ASK-OWNER line becomes one AskUserQuestion at session start.
- Fail open at every level, including config loading; detect `CLAUDE_CODE_REMOTE=true` / `CI` and mark machine-local capabilities N/A.
- Recurring owner-only commands are `recurring` entries (`--stamp <id>` after the owner runs one); trigger-bound owner steps go in `ask_at_trigger`.

Read `references/readiness-check.md` before installing or changing the readiness check, its config or its CI run.

## 4-6. Telemetry, LSP navigation, regression gates

- Telemetry is enabled only in the USER settings, only after asking (`readiness_check.py --enable-telemetry`).
- Use the LSP tool before grep for definitions and references when the LSP line is OK; fix diagnostics on files you touched.
- Skill and agent edits ship with an eval case and a plugin eval run (ask first, it is billed); landings get a review step on the merged diff, and a finding blocks the push.

Read `references/telemetry-lsp-gates.md` before enabling telemetry, adding an `lsp` entry or running a regression gate.

## Common mistakes and rationalizations

Every contract item exists because a baseline agent without it got it wrong. Read `references/mistakes-and-rationalizations.md` when an excuse for skipping a rule sounds reasonable or when auditing an existing setup.

## Red flags

- `|| exit 2`, `except ...: return 2`, or "fails closed" anywhere in a guard or its settings entry
- A guard rule without `allow` examples, or scope tested only against a second checkout of the same repo
- A role file without `maxTurns`, a read-only role without its own `hooks:`, a gate-waiting role without `cacheTtl: 1h`
- "Definitions are in place" with no restart and no smoke dispatch
- A readiness status set without N/A, or a check that can crash the hook
- `CLAUDE_CODE_ENABLE_TELEMETRY` in a project's `.claude/settings.json` or `.claude/settings.local.json` (ignored
  there: telemetry is enabled only in the user settings)
- Routing around a block: rephrasing, splitting or encoding a command the guard refused
- A guard rule, trigger step or role the owner never asked for, installed without asking
- "CI runs the self-tests" with no CI run seen, or a readiness probe that exercises only one shell tool

## Standards

The bar is the **engineering-standards** skill. Here that means one home per rule: the rule text lives in
`guard-rules.json` or the role file, and `CLAUDE.md` states the rule without copying the pattern. Every guard has
a check that has been seen to fail (make each new rule's `block` example fire once before trusting its green). A
scope or fail-mode shortcut is reported as debt, not shipped.

## Project hooks

Your `CLAUDE.md` supplies the project half: the landing command named in the push rule's `instead`, the roles and
their gate commands, the review step, and the list of trigger-bound owner steps. Project rules win on conflict.

