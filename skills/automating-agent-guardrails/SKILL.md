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
| Cost telemetry | `.claude/hooks/otlp_sink.py`, `usage_report.py`; env in `.claude/settings.local.json` | `scripts/` |

## 1. Guard hooks that block forbidden commands

1. Encode **only the rules the owner stated**. A rule you think is missing (a refspec rule, "PRs only") is a
   proposal: ask, never add it silently. Every extra rule blocks the owner's own work.
2. Write one rule per forbidden command in `guard-rules.json`: `pattern`, `reason`, `instead` (the right
   alternative, as a command), `block` examples, and `allow` examples. The allow list holds the rule's legitimate
   neighbours, for example `git stash list` for a stash rule, or a feature-branch push for a push-to-main rule.
3. Set `"scope": "repo"` on every rule that encodes this repository's policy: its landing route, protected
   branches, stash hygiene. Only rules about the harness itself, such as escapes in heredocs, stay `"any"`.
4. Register the guard for every shell tool (`"matcher": "Bash|PowerShell"`, see `templates/settings.json`), with a
   plain `python ...` command and no `|| exit 2`.
5. Run `python .claude/hooks/guard_commands.py --selftest --settings .claude/settings.json` until it is GREEN, and
   add the same command to CI. A workflow file that has never run is not a gate: until you have seen a green CI
   run, report CI as unproven.

**Contract.** Every item is required.

| The guard… | Why |
|---|---|
| exits 2 with a stderr message naming the rule and an `Instead:` command | A bare "no" invites the agent to rephrase the command; a named alternative gets followed. |
| covers every shell tool (Bash and PowerShell) | A rule on Bash alone is bypassed by the first PowerShell call. |
| **fails OPEN**: unparseable input, a missing or corrupt rules file, a git error or a crash all exit 0 (with a stderr note) | A guard that fails closed turns one bad field, a missing interpreter or a harness format change into a block on every shell call in every session and subagent. These rules are workflow conventions with real backstops (branch protection, CI). A security boundary belongs in permissions, a sandbox or the server. |
| writes stderr as UTF-8 | Windows otherwise writes the console code page, and the agent reads mojibake. |
| is **scoped to this repository**: a `repo` rule fires only when the command's working tree has the same git common dir as `$CLAUDE_PROJECT_DIR`, following `cwd`, `cd`/`Set-Location` and `git -C` | The same session also works in other repos, and each has its own rules. A push rule keyed on the branch name alone blocks `git push origin main` everywhere. |
| has a self-test in CI proving each rule fires on `block`, passes `allow`, and passes when the same command runs in an **unrelated** repo | A guard is only trusted once its failure branch has fired. Two checkouts of one repo don't test scope, because they share it. |

Don't use `permissions.deny` for these rules. Deny rules match a prefix, can't see which repository a command runs
in, and can't tell the agent what to do instead.

## 2. Role agent definitions

1. Copy `templates/agents/*.md` and adapt the roles. **Every** role sets `model`, `effort` and `maxTurns`: the
   quality gate (refuter) gets the highest effort, implementers and analysts get high, and mechanical chores get a
   cheaper model and lower effort.
2. **Every role that waits on gates, builds or CI** sets `experimental:` / `cacheTtl: 1h`. With the default 5-minute
   TTL, each wait longer than 5 minutes ends with the whole context written to the cache again. The 1-hour TTL
   turns those rewrites into cache reads. Roles that never wait keep the default.
3. **Read-only roles carry `readonly_guard.py` in their OWN frontmatter `hooks:`**, with matcher
   `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Don't put it in project settings keyed on the hook input's
   `agent_type`: when that field is missing, such a hook can't tell the role from the main session, and it allows
   the write. The guard blocks file-tool writes, repo-changing git and shell writes (`>`, `>>`, `tee`, `Out-File`,
   `Set-Content`) inside any git tree, resolves Git Bash paths (`/e/repo`), and lets scratch writes through. It
   cannot see a write made inside a script; say so in your report.
4. Select roles by name: `agentType: '<role>'` in workflow scripts, and `subagent_type: "<role>"` with the Agent
   tool. Never set model or effort per call.
5. **Restart, then prove each role.** The agent registry loads at session start, so a new or edited definition
   does nothing until a restart. Then send one short smoke agent per role. Each one reports its model and effort.
   Each read-only role tries a Write inside the repo, which must be BLOCKED, and a Write in scratch, which must
   pass. Record the proof with `python .claude/hooks/readiness_check.py --stamp roles-smoke`. The readiness check
   prints a TODO line until the proof matches the current files.
6. **Roll back on quality.** After lowering a role's model or effort, watch its quality metric: the refuters'
   overturn rate on its output, rework, or red CI. If the metric drops, move the role back up. Telemetry (§4)
   supplies the cost side.

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
   enough, because a rule that exists only there disappears when the hook fails.
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

## 4. Local cost telemetry

1. Ask first, and on a yes run `python .claude/hooks/readiness_check.py --enable-telemetry`. That writes
   `CLAUDE_CODE_ENABLE_TELEMETRY=1`, the OTLP `http/json` exporters and endpoint `http://127.0.0.1:4318` into
   `.claude/settings.local.json` and git-excludes it. Set it **per machine, never in the committed settings**:
   clones, CI and cloud sessions would all export to a port with no receiver. It takes effect in the next session.
2. `otlp_sink.py` is the loopback receiver. It is standard-library only and refuses protobuf with a 415. The
   readiness check starts it when it is down and reports REPAIRED.
3. `python .claude/hooks/usage_report.py [--by agent,skill,model] [--all]` reports tokens and cost per group. On
   the first real data, run `--keys` and add your Claude Code version's attribute names if a dimension shows only
   `-`.

## 5. LSP-first navigation

Add a `readiness.json` `lsp` entry per language: the plugin, the server binary, extra paths and the install
command. The line is OK only when both the plugin and the binary are present. Otherwise it is ASK-OWNER, and
nothing is installed without asking. When the LSP line is OK, find definitions, references and symbols with the LSP
tool before grep, and use grep for text.

## 6. Regression gates

- **Skill and agent edits:** plugin evals are the regression gate. Each changed rule ships with an eval case that
  beats the no-plugin baseline (this repo's `evals/README.md` explains the rule and how to read Δ). Run it before
  the push, and because it is billed, ask at that trigger.
- **Landings:** run a review step on the merged diff before the landing push (the lander template's step; the
  `review` skill or `/code-review`). A finding blocks the push.

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

## Red flags

- `|| exit 2`, `except ...: return 2`, or "fails closed" anywhere in a guard or its settings entry
- A guard rule without `allow` examples, or scope tested only against a second checkout of the same repo
- A role file without `maxTurns`, a read-only role without its own `hooks:`, a gate-waiting role without `cacheTtl: 1h`
- "Definitions are in place" with no restart and no smoke dispatch
- A readiness status set without N/A, or a check that can crash the hook
- `CLAUDE_CODE_ENABLE_TELEMETRY` in the committed `.claude/settings.json`
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
