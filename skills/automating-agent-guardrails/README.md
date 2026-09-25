# automating-agent-guardrails

Rules for Claude agents usually start as prose: "never `git stash`", "only the landing script pushes to main",
"refuters are read-only", "ask me before installing anything". Prose gets forgotten under pressure, and a subagent
dispatched from a workflow may never see it. This skill has Claude set a project up so those rules are
**structural**, enforced by Claude Code hooks and role definitions, and **automatic**, checked at the start of
every session, with anything that needs your permission turned into a question instead of skipped.

The full procedure is in [`SKILL.md`](SKILL.md). This page explains what gets installed, why each piece exists, and
what you have to do yourself.

## When Claude uses it

The skill's description tells Claude to load it when a project's agent rules keep getting broken or skipped, or
when setting up or auditing guard hooks, `.claude/agents` role definitions, a session-start readiness check,
OpenTelemetry cost tracking or LSP navigation. Asking "make the no-stash rule a hook", "set up role agents for the
fleet" or "check our Claude tooling is actually in use every session" is usually enough. You can also name it.

## What it installs

Everything is copied into your repository (under `.claude/`), so CI and cloud sessions run the same files. Every
script needs only Python 3 and the standard library, runs as `python <script>`, and has a `--selftest`.

| Piece | What it does |
|---|---|
| **Guard hook** (`guard_commands.py` + `guard-rules.json`) | A PreToolUse hook on every shell tool (Bash and PowerShell). It blocks the commands your rules forbid and tells the agent what to do instead. Rules are JSON: a regex, the reason, the alternative, plus example commands that must be blocked and legitimate neighbours that must pass. |
| **Role agents** (`.claude/agents/*.md` + `readonly_guard.py`) | Implementer, lander, refuter, analyst and chore roles, each with its own model, effort, turn cap and (for roles that wait on gates) a 1-hour prompt cache. Read-only roles carry a hook in their own definition that refuses writes inside any git tree (file tools, repo-changing git, and shell redirections such as `>` or `Out-File`) but allows scratch files. |
| **Readiness check** (`readiness_check.py` + `readiness.json` + `session_start.py`) | Runs at every session start. It checks each adopted capability and prints OK, REPAIRED, N/A, TODO or ASK-OWNER. A `CLAUDE.md` section tells Claude to ask you about every ASK-OWNER line at the start of the session. |
| **Cost telemetry** (`otlp_sink.py` + `usage_report.py`) | A local OpenTelemetry receiver on `127.0.0.1:4318` and a report of tokens and cost per agent, skill and model. It is enabled per machine only. |
| **LSP check** | Confirms that the language-server plugin and its server binary are both installed before Claude is told to navigate code with the LSP tool. It asks before installing anything. |

## Why it works this way

The skill was written against a measured baseline: capable agents asked to build these pieces without it. Each
contract item closes a mistake they made.

| Rule | The failure it prevents |
|---|---|
| The guard **fails open** (any internal error allows the call) | A baseline guard failed closed on purpose. Malformed input blocked the call, and a crash or missing Python would have blocked every tool call in every session. Branch protection and CI are the real backstop. A regex hook is a guardrail, not a security boundary. |
| Repository policy rules are **scoped to this repo** (same git common dir as the project, following `cd`, `Set-Location` and `git -C`) | A baseline push rule matched only the branch name, so it blocked `git push origin main` in unrelated repositories. It also refused all pushes in repos without its pre-push setup. |
| Every rule has block **and** allow examples, and a self-test in CI runs them, including from an unrelated repo | A guard is trusted only once its failure branch has fired. A scope test that uses two checkouts of one repo can't see a scope bug. |
| UTF-8 stderr; every shell tool | On Windows the first real block message arrived mangled. A Bash-only rule is bypassed by the first PowerShell call. |
| Read-only is a hook **in the role's own definition** | A project-wide hook that reads `agent_type` from the hook input treats a call with no such field as the main session, and allows the write. |
| **Every** role has a turn cap | A baseline capped one role of five. An agent's cost grows with its turns, and a fresh agent from a checkpoint is cheaper than a long transcript. |
| Roles that wait on gates use a **1-hour prompt cache** | With the default 5-minute cache, every wait longer than 5 minutes ends with the whole context written to the cache again. The telemetry measures whether that trade pays off for your roles. |
| **Restart, then a live smoke dispatch** per role | Agent definitions load at session start. A new or edited role does nothing until a restart, and until one runs, nobody knows whether its read-only hook fires. |
| An **N/A** status and cloud/CI detection | Without them, a cloud session would try to start a local receiver and ask you to install tools on a throwaway VM. |
| The ask-the-owner rule lives in **`CLAUDE.md`**, not only in hook output | A rule that exists only in hook output disappears on the day the hook fails. |
| The readiness check **fails open at every level**, including config loading | A baseline check crashed with a traceback on a corrupt config and asked nobody anything. |
| Telemetry env only in `settings.local.json` | In committed settings, every clone, CI run and cloud session would export to a port with no receiver. |

## Installing it in a project

Ask Claude to "set up the agent guardrails for this repo" with the skill installed. It follows `SKILL.md`:

1. Copy the scripts to `.claude/hooks/`, the role templates to `.claude/agents/`, and merge
   [`templates/settings.json`](templates/settings.json) into `.claude/settings.json`.
2. Edit `guard-rules.json` for your rules. Replace the example landing command `bash scripts/land.sh` and the
   protected branch names.
3. Edit `readiness.json`: delete the sections you have not adopted, and list your roles, languages and recurring
   owner steps.
4. Paste [`templates/CLAUDE-guardrails.md`](templates/CLAUDE-guardrails.md) into your `CLAUDE.md` and fill in your
   review step and trigger-bound owner steps.
5. Add to CI:
   ```
   python .claude/hooks/guard_commands.py --selftest --settings .claude/settings.json
   python .claude/hooks/readonly_guard.py --selftest
   python .claude/hooks/readiness_check.py --ci
   ```

## Verifying it

- Every script's self-test prints a GREEN or RED verdict line and exits non-zero when RED:
  `guard_commands.py --selftest` (add `--rules <file>` to test a rules file elsewhere), `readonly_guard.py
  --selftest`, `readiness_check.py --selftest`, `usage_report.py --selftest`.
- `readiness_check.py` with no arguments prints the same report the session sees.
- After a restart, the readiness check's TODO line walks Claude through the smoke dispatch that proves the roles.

## What needs you

The readiness check asks these as questions at session start. None of them happen silently.

| When | What you decide or do |
|---|---|
| First session on a machine | Whether to enable local cost telemetry. On yes, Claude runs `readiness_check.py --enable-telemetry`, and it takes effect next session. |
| A language server is missing | Whether to enable the LSP plugin (`/plugin install ...`) and install its server binary. |
| A recurring owner-only command is due (for example a weekly `/skill-doctor`) | Run it yourself. Claude then records the date with `--stamp`. |
| At a trigger you configured (for example `/code-review ultra` before a landing push, paid evals before a skill push) | Whether to run the billed or owner-only step. |
| After role definitions change | Restart Claude Code, so the smoke dispatch runs against the new definitions. |
| A committed hook or role file is broken | Approve the fix. The check reports it but does not edit committed files on its own. |

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The procedure and contracts Claude follows |
| [`scripts/guard_commands.py`](scripts/guard_commands.py) | PreToolUse guard for shell tools; `--selftest [--settings]` |
| [`scripts/readonly_guard.py`](scripts/readonly_guard.py) | Frontmatter hook for read-only roles; `--selftest` |
| [`scripts/readiness_check.py`](scripts/readiness_check.py) | Session-start readiness check; `--hook`, `--ci`, `--stamp`, `--enable-telemetry`, `--selftest` |
| [`scripts/otlp_sink.py`](scripts/otlp_sink.py) | Loopback OTLP/HTTP-JSON receiver; `--ensure`, `--status`, `--stop` |
| [`scripts/usage_report.py`](scripts/usage_report.py) | Tokens and cost per agent, skill, model; `--keys`, `--selftest` |
| [`templates/guard-rules.json`](templates/guard-rules.json) | Example rules: no stash, no autostash, land via script, no escapes in heredocs |
| [`templates/settings.json`](templates/settings.json) | The SessionStart and PreToolUse hook registrations |
| [`templates/readiness.json`](templates/readiness.json) | Readiness check config with every section |
| [`templates/session_start.py`](templates/session_start.py) | SessionStart hook: your project probe plus the readiness check |
| [`templates/agents/`](templates/agents/) | Implementer, lander, refuter, analyst and chore role definitions |
| [`templates/CLAUDE-guardrails.md`](templates/CLAUDE-guardrails.md) | The `CLAUDE.md` section that makes Claude act on blocks and ASK-OWNER lines |
| `README.md` | This page |

Related skills: [`agent-fleet`](../agent-fleet/README.md) (the orchestration rules these roles serve),
[`claude-cloud-sessions`](../claude-cloud-sessions/README.md) (why cloud sessions get N/A), and
[`review`](../review/README.md) (the pre-landing review step).
