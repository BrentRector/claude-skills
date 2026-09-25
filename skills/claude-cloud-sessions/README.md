# claude-cloud-sessions

Claude Code can run sessions on Anthropic-hosted VMs (claude.ai/code, `claude --cloud`, routines). Getting real work
done there has traps the documentation doesn't warn about: setup work placed in the wrong layer silently vanishes,
multi-repo sessions skip your repo's hooks, private submodules fail to clone, and — measured — the surface you launch
from decides which meter you are billed against. This skill is a set of **measured field notes** (taken on
2026-09-24 while running cloud sessions for a large .NET compiler project) covering environment setup, repository
access, launching, billing, monitoring, and stopping a fleet cleanly before a credit or budget runs out. Where the
official docs say something different, the skill gives both.

The full notes are in [`SKILL.md`](SKILL.md). The platform changes; the skill itself says to treat every "measured"
line as something to re-check, and to re-measure anything a decision depends on, billing above all.

## When Claude uses it

The skill loads when you are running work in Claude Code cloud sessions: setting up a cloud environment, launching
or billing sessions, attaching several repos or private submodules, orchestrating subagents in the cloud, or
stopping before a credit runs out. Skills load automatically when the description matches the task, so asking
"set up a cloud environment for this repo" or "run this batch in cloud sessions" is enough. You can also name it
explicitly ("use the claude-cloud-sessions skill").

## What it does

The skill walks through the lifecycle of cloud work, one section per stage:

| Stage | What the skill says to do |
|---|---|
| 1. Mental model | Split work between the **environment setup script** (runs as root before Claude Code starts; its filesystem is snapshotted and reused) and the repo's **SessionStart hook** (runs every session, because the repo is re-cloned each time). Toolchains go in the script; anything inside the clone goes in the hook. |
| 2. Setup script | Keep the canonical copy in the repo and re-paste it into the environment's *Setup script* field on every edit; verify the paste by hash. Exit 0, finish in ~5 minutes, `set -uo pipefail` (never `-e`), tee a log to `/var/log/<project>-setup-env.log`, fix interpreter shadowing, and use Custom network access. Pick the environment explicitly. |
| 3. Multi-repo hooks | With two or more repos attached, no repo's hooks load. The setup script installs a **user-level** SessionStart hook shim on the VM that runs the repo's own hook. |
| 4. Repository access | The GitHub proxy serves only repos attached to the session, so attach a private submodule's repo too (or decide the session doesn't need it). Cloud sessions commit only on `claude/*` branches; land them from a local orchestrator. |
| 5. Launching and billing | Choose among the web page, `claude --cloud` and routines knowing each one's repo limits, environment selection, TTY needs, sidebar visibility and billing. |
| 6. Monitoring | Watch a session's page read-only; anything typed becomes a queued message. Give each session a self-contained brief. |
| 7. Orchestrating and crash safety | Build once, then run up to ~6 subagents with their own tags, output dirs and branches. Checkpoint per unit, push every N units, push a draft before the refute phase, and arm a budget watcher that sends STOP with margin. |
| 8. Cost per unit | Run one calibration batch and divide dollars by units produced; plan the rest from that number. |

It ends with a six-item **checklist before a fleet**: environment selected and hash-verified, a smoke session all
green, every needed repo attached, the launch surface confirmed to bill where you intend, a self-contained brief
with per-unit checkpoints, and a budget watcher proven to fire.

### The setup-script template

[`references/setup-env-template.sh`](references/setup-env-template.sh) is a generic, commented Bash template
implementing sections 1–3. Set its placeholder variables (`PROJECT`, `REPO_NAME`, `HOOK_REL`, `HOOK_CMD`, `PYVER`,
`PIP_DEPS`), fill in the commented examples, commit it to your repo (the skill suggests
`scripts/cloud/setup-env.sh`), and paste its text into the environment's *Setup script* field. In order it:

1. Tees all output to `/var/log/$PROJECT-setup-env.log` so a session can read what happened.
2. Refreshes the apt index in the background while downloads run.
3. Installs toolchains the image lacks (an example shows the .NET SDK with a distro-package fallback).
4. Installs the Python version you need with `uv` and points both `python` and `python3` in `/usr/local/bin` at
   it, then installs any pip dependencies.
5. Writes an `/etc/profile.d/$PROJECT.sh` for environment variables.
6. Pre-caches large per-clone downloads under `/opt/$PROJECT-cache/`, pinned by URL and SHA-256, so the hook can
   copy them into each fresh clone.
7. Installs the user-level SessionStart shim and **merges** its entry into `~/.claude/settings.json` without
   overwriting keys the platform wrote.
8. Logs tool versions for a smoke session to check, and exits 0.

A trailing comment shows the repo side: in your SessionStart hook, do per-clone work only when
`CLAUDE_CODE_REMOTE=true` (submodule update, copying cached files in) and never raise.

## Why it works this way

| Rule | The failure it prevents |
|---|---|
| Toolchains in the setup script, per-clone work in the hook | The repo is re-cloned every session, so anything the script writes inside the clone is lost; the script also doesn't re-run on resume. |
| Never `set -e`; `\|\| true` on optional steps | A non-zero exit fails the session start. |
| Tee the setup log to `/var/log` | Measured: setup stdout appears nowhere a session can read, so no session can tell whether a step worked. |
| Verify the pasted script by hash (field + `"\n"`) | The platform runs only the pasted text, and trims the final newline on save. |
| Install your own interpreter and symlink both names | Measured: the image's `/usr/local/bin/python{,3}` pointed at 3.11, ahead of `/usr/bin` on PATH, and broke scripts using newer syntax. |
| Select the environment explicitly | Measured: the `Agent` tool's `isolation: "remote"` has no environment parameter and lands in Default, bypassing the one you built. |
| User-level hook shim | Measured: with 2+ repos the session starts in `/home/user`, logs `Found 0 total hooks in registry`, and submodules stay uninitialized (two unit tests went red unnoticed). The shim restored the hook. It skips itself in the single-repo case so the hook doesn't run twice. |
| Attach every repo the work needs | The GitHub proxy authorizes only attached repos; a private submodule elsewhere fails with a credentials prompt error. |
| Choose the launch surface deliberately | Measured: routine-launched sessions billed the plan's usage meters, while web-page and interactive `claude --cloud` sessions drew a promotional cloud-session credit. The docs describe no separate credit. Confirm with a one-line test and the meter. |
| Unique tag at the start of every prompt | Sidebar titles come from the prompt's opening words; routine run titles come from the routine name. |
| Don't open "See detailed breakdown" from a working session | Measured: it posts `/usage` into the session you are viewing. |
| Checkpoint per unit, push every N, draft before refute | A session can end abruptly, and background subagents are not restored when it is reopened. The refute phase is the longest stretch with nothing durable written. |
| A budget watcher, tested once | The stop signal must arrive with enough margin for the final push. Non-interactive `claude -p … --cloud` was measured failing, so the verified channel is the session's web page. |

The skill's *Standards* section adds that the cloud changes where work runs, never how good it must be: cloud
agents get the same briefs as local ones, their results land through the project's normal gate and review, and
unverified findings stay labeled as leads.

## Using it in your project

- **Your project's specifics.** The skill uses a placeholder `<PROJECT>` and the template uses placeholder
  variables and hosts; you supply your toolchains, extra network hosts, hook path and cache files. The repo-wide
  convention (see the [top-level README](../../README.md#adapting-to-your-project)) is that your `CLAUDE.md`
  supplies commands and tightens rules, and wins on conflict.
- **Prerequisites.** Access to Claude Code cloud sessions, a repo on GitHub, a SessionStart hook in the repo if you
  have per-clone work, and a way to read your usage or credit meter. The template targets Bash on the Ubuntu 24.04
  x86_64 image and uses Python 3 to merge the settings file.
- **Composes with:**
  - [`agent-fleet`](../agent-fleet/SKILL.md) — the general restart-safe, budget-aware orchestration rules; this
    skill applies them to cloud VMs.
  - [`engineering-standards`](../engineering-standards/SKILL.md) — the quality bar cloud agents are held to.
  - [`test-gate`](../test-gate/SKILL.md) — the local gate that cloud results land through.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The measured notes Claude follows, with the docs' differing statements alongside |
| [`references/setup-env-template.sh`](references/setup-env-template.sh) | Commented setup-script template: logging, toolchains, interpreter fix, pre-cache, and the user-level hook shim |
| `README.md` | This page |
