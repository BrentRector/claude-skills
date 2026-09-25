---
name: claude-cloud-sessions
description: "Use when running work in Claude Code cloud sessions (claude.ai/code, `claude --cloud`, routines/RemoteTrigger) — setting up an environment, launching and billing sessions, multi-repo and private-submodule access, orchestrating subagents in the cloud, and stopping cleanly before a credit or budget runs out."
---

# Claude Code cloud sessions: measured field notes

These facts were MEASURED on 2026-09-24 while running Claude Code cloud sessions (Anthropic-hosted VMs) for a
large .NET compiler project, the worked example called `<PROJECT>` below. Where the official docs
(code.claude.com/docs/en/claude-code-on-the-web, …/cloud-environments) say something different, both are given.
The platform changes, so treat every "measured" line as something to re-check, and re-measure anything a
decision depends on (billing above all).

## 1. The mental model: per-VM vs per-clone

A cloud session is a fresh Ubuntu 24.04 x86_64 VM (about 4 vCPU, 16 GB RAM, 30 GB disk) with your repo(s) cloned
into `/home/user/<repo>`. Work splits into two layers, and putting work in the wrong layer is the most common
mistake:

| Layer | Runs | Survives to the next session? | Put here |
|---|---|---|---|
| **Environment setup script** | as root, BEFORE Claude Code starts, only when the snapshot is (re)built | Yes: the filesystem is **snapshotted** and reused | toolchains, SDKs, CLIs, pip/npm globals, cached downloads, the user-level hook shim (§3) |
| **SessionStart hook** | after Claude Code starts, EVERY session (including resume) | No: the repo is **re-cloned per session** | anything inside the clone: submodules, git-ignored corpora, `npm install`, generated files |

- The snapshot is rebuilt when the setup script or the allowed network hosts change, or after about 7 days
  (docs). Resuming a session never re-runs it. Anything the script writes inside the clone is lost, because the
  clone is not in the snapshot you get next time. Per-clone work belongs in the hook.
- Background processes are not snapshotted, only files.
- Hooks run locally too, so gate the cloud-only branch on `CLAUDE_CODE_REMOTE=true`. A hook must never fail the
  session: catch everything and report it as context.
- Pre-cache big per-clone downloads in the setup script (outside the repo, e.g. `/opt/<project>-cache/`, pinned
  URL + SHA-256). The hook then copies the file in rather than downloading it again.

## 2. The environment setup script

- **Keep the canonical copy in the repo** (e.g. `scripts/cloud/setup-env.sh`). The platform runs only the text
  pasted into the environment's **Setup script** field (claude.ai/code, environment chip, hover the environment,
  gear icon, "Edit cloud environment"). When you edit the file, re-paste it in the same change set.
  Measured: the platform **trims the final newline** on save, so to confirm a paste, compare
  `sha256(field value + "\n")` with `sha256sum` of the file.
- Constraints: must **exit 0** (a non-zero exit fails session start) and finish in about 5 minutes. Use
  `set -uo pipefail`, never `-e`, and add `|| true` to any step that isn't critical. Run independent downloads
  in parallel (`&` + `wait`).
- **Tee its own log to `/var/log/<project>-setup-env.log`.** Measured: the setup script's stdout appears nowhere a
  session can read it, so without that copy no session can tell whether a step worked.
- **The image's own interpreters can shadow yours.** Measured: `/usr/local/bin/python{,3}` pointed at 3.11,
  ahead of `/usr/bin` on PATH, and broke PEP 701 f-string scripts. Install the version you need and symlink both
  names in `/usr/local/bin`. `uv python install` from PyPI works under the default allowlist.
- **Network:** use Custom access = the default package-manager list PLUS the extra hosts your installers use (for
  the .NET example: `builds.dotnet.microsoft.com`, and `ftp.gnu.org` for a test corpus). GitHub never goes through
  the allowlist; it goes through the separate GitHub proxy (§4).
- Choose the ENVIRONMENT deliberately. Measured: the `Agent` tool's `isolation: "remote"` has no environment
  parameter and lands in **Default**, which bypasses the environment you built.

`references/setup-env-template.sh` is a generic, commented template of all of the above.

## 3. Multi-repo sessions do not load repo hooks, so add a user-level shim

Measured: with **one** repo attached, the session starts IN the repo, and its `.claude/settings.json` hooks fire.
With **two or more** attached, it starts in their parent, `/home/user`. No repo's `.claude/settings.json` is
loaded, and the session log says `Found 0 total hooks in registry`. Submodules were left uninitialized and
per-clone fetches never ran (two unit tests went red and nobody noticed).
The docs confirm this ("a session with several repositories doesn't load hooks from any repository's
`.claude/settings.json`") and recommend doing the work in the setup script instead. That cannot work for per-clone
work (§1).

**Fix (verified):** the setup script writes a **user-level** SessionStart hook into the VM's
`~/.claude/settings.json` (`HOME=/root`). It merges the entry and never overwrites keys the platform put there.
The hook points at a shim that runs the repo's own hook only when `CLAUDE_PROJECT_DIR` is NOT the repo, so the
single-repo case doesn't run it twice. The settings file is part of the snapshot, so the hook fires in every session.
Measured: `hook_spawn_completed … "SessionStart" … exit_code 0`, the submodule got checked out, and the unit
suite went green.
*Docs contradiction:* the docs say user-level `~/.claude/settings.json` hooks should not be expected in the cloud
and that Anthropic-hosted sessions run hooks "from the repository and from your organization's server-managed
settings". That statement is about YOUR laptop's user settings. A user settings file written ON the VM by the
setup script was loaded (measured 2026-09-24).

## 4. Repository access: the GitHub proxy serves only ATTACHED repos

- Every git operation goes through a GitHub proxy that authorizes **only the repositories attached to the
  session**. A private submodule in another repo fails with `could not read Username … terminal prompts disabled`
  unless that repo is attached too. For a routine, list both repos in its `sources`.
- Ask what actually needs the second repo. Measured: in `<PROJECT>` the private submodule held only a licensed
  PDF used for rendering diagrams, and the searchable text lived in the main repo. So single-repo sessions were
  fine for most work, and the brief told agents to mark diagram-dependent conclusions as unverified.
- The session cannot push to a protected `main` whose required checks it can't satisfy. Have cloud sessions
  commit only on `claude/*` branches, and land them from a local orchestrator.

## 5. Launching sessions: surfaces differ in repos, environment, TTY, visibility, BILLING

| Surface | Repos | Environment | Notes (measured) |
|---|---|---|---|
| **claude.ai/code web page** (also desktop/mobile) | several ("+" beside the repo chip) | the environment chip | `https://claude.ai/code?repositories=owner/a,owner/b` pre-fills the repos. Shows in the sidebar |
| **`claude --cloud "<task>"`** | **ONE** (the cwd's GitHub remote at the current branch; push first) | your `/remote-env` pick (`remote.defaultEnvironmentId`) | Measured: **prints nothing for a minute or more — it looks hung; do not abort it** — then prints `Created cloud session`, `View: <url>` and `Resume with: claude --teleport <id>` and returns. **Needs a TTY**: it fails when run from an agent's shell tool. `--environment` accepts only self-hosted `ccpool_` ids |
| **Routines / RemoteTrigger** | its `sources` list | `job_config…environment_id` | Does **not** appear in the sidebar. Run titles come from the ROUTINE NAME, so rename the routine before each fire or every run looks identical. Debug with `list_runs` / `get_run_log` |

- **Sidebar titles** come from the opening words of the PROMPT, not the routine name. Start every prompt with a
  unique tag (`"Batch w2-s3 — …"`), and never start with an earlier run's number.
- Follow-ups: type into the session's own page on claude.ai/code (verified: a message sent while it works is
  queued and read at its next turn). The docs also describe `claude -p "msg" --cloud <session-id>`, but a
  non-interactive `--cloud` invocation was measured failing ("`--cloud requires an interactive terminal`",
  2026-09-24) — test it in your setup before relying on it for a stop signal (§7).

### Billing (measured 2026-09-24; re-measure before relying on it)

- Sessions launched by **routines / RemoteTrigger billed the PLAN** (the weekly/5-hour usage meters). Six
  routine runs (about $30; one alone showed "This session Cost $6.73") left a promotional cloud-session credit
  untouched.
- Sessions started **from the claude.ai/code web page** (and `claude --cloud` from an interactive terminal) **drew
  the cloud-session credit** immediately ($250 → $249 on a one-line test).
- Subagents inside a session bill to that session.
- *Docs:* the docs describe no separate credit at all. They say cloud sessions "share rate limits with all other
  Claude and Claude Code usage" and "there is no separate compute charge for the cloud VM". When a credit exists,
  **which surface you launch from decides what you spend.** Confirm with a one-line test session and the meter
  before starting a fleet.

## 6. Monitoring a session without disturbing it

- Watch read-only: open the session page and read it. Don't type into it, because anything sent becomes a
  message in the session's queue.
- Trap (measured): in the usage popover, **"See detailed breakdown" posts `/usage` INTO the session you're
  viewing**. Open it from a session you don't care about.
- The session can read its own id (`CLAUDE_CODE_REMOTE_SESSION_ID`). Put the transcript link in its commits and
  reports.
- A cloud session cannot see your local memory, browser, or scratch files. Give it a **self-contained brief**
  (the task note, the rules it is bound by, the exact commands) and require everything it produces to land on its
  branch and in its final message.

## 7. Orchestrating in the cloud, and crash safety

The VM is 4 cores, so share expensive work: **build once in the orchestrator, then spawn the subagents**, at most
about 6 in parallel, each with its own tag, output dir and `claude/<tag>` branch. A session can end ABRUPTLY
(credit exhausted, inactivity expiry, a limit), and background subagents are not restored when a session is
reopened (docs). Design so a kill costs at most one step:

- **Checkpoint per unit.** Append one JSONL line per decided item the moment it is decided (open, append,
  flush). Never batch the writes at the end.
- **Commit + push every N units** (e.g. every 5) on the session's branch, touching only its own directory.
- **Push a draft snapshot BEFORE the review/refute phase.** The refute phase is the longest step with nothing
  durable yet written.
- **Integrate and push per batch**, not once at the end of the whole run.
- **A budget watcher with margin.** Read the credit/usage meter on a schedule (e.g. a local loop, or a Monitor
  over the meter). At a threshold well before empty, send each live session a STOP message
  ("push what exists now and stop; start nothing new") — the verified channel is the session's web page (a browser
  automation step works); leave margin for the push itself, and click the session's Stop button as the last
  resort. Test the watcher's STOP branch once before relying on it.

## 8. Measure cost per unit, then plan with it

Take one calibration batch, then divide dollars by the units it produced. Worked example (`<PROJECT>`,
2026-09-24, Opus-class model, ~99 % cache hits): spec-adjudication of one conformance row **~$0.34–0.50/row**
(~20 rows per batch, 11–19 min); writing one documentation determination row **~$0.80/row**; writing one
spec-derived test golden **~$0.55–0.85/row**. These numbers are an example of the method, not a promise. Your
task mix, model and cache-hit rate decide your numbers. Re-measure after any change to the brief.

## Standards

The bar is the **engineering-standards** skill; the cloud changes where work runs, never how good it must be:

- Cloud agents get the same briefs as local ones — the quality bar, the complete-feature rule and the root-cause
  rule travel with every dispatch; a budget cut is a reason to stop and push, never to land a smaller, worse fix.
- Every result a cloud session produces lands through the project's normal gate and review; cloud-side gates are
  evidence to re-check locally, not a substitute.
- Findings a cloud agent could not verify stay labeled as leads until a probe confirms them — every bug is a
  pattern, so a confirmed one still gets its sibling sweep.

## Checklist before a fleet

1. The environment is selected explicitly (not Default), and the setup-script field matches the repo copy (hash).
2. A smoke session is ALL GREEN: `/var/log/<project>-setup-env.log` shows every toolchain, the hook fired, the
   submodules are checked out, and the test suite passes.
3. Every repo the work needs is attached (the submodules' repos too).
4. The launch surface bills where you intend (one-line test + the meter).
5. The brief is self-contained. Checkpoints are per unit, pushes per N, and there is a draft snapshot before refute.
6. The budget watcher is armed and has been proven to fire.
