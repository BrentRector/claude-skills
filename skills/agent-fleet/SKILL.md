---
name: agent-fleet
description: Use when deciding whether a long engineering campaign should run parallel subagents or a multi-agent workflow, when writing the brief an implementer, reviewer, refuter or lead-filing agent works from, and before dispatching one - so a session-limit kill costs at most one step, a restart never repeats work, and tokens go where they move the result. Covers checkpoints, stop and death handling, id allocation and model tiers; landing finished branches is merge-queue-landing.
---

# Agent fleet: restart-safe, budget-aware orchestration

**A long multi-agent campaign survives a session-limit kill: the kill costs at most one step, a restart re-decides
nothing, and tokens go to the work that moves the reported metric.** Check it after a kill: `references/status_delta.py`
reads CURRENT or STALE on every worktree, and the reconciled returns show no item decided twice; check the cost by
comparing tokens per closed item, per lane, with the last campaign.

## When a fleet pays, and when it does not

A subagent starts from an empty context: it reads its brief, orients on the code, and re-reads its whole transcript
on every turn, and what it returns enters the orchestrator's conversation. Subagents are usually most of a
campaign's spend. So the orchestrator does a job itself when it is a handful of tool calls, a lookup, or something it
already knows. A subagent earns its cost in three cases: **parallel breadth** (many independent items, each needing
its own reading), **isolation** (work whose context would swamp the orchestrator's, or that runs in its own
worktree), and **an independent judgment** (a refuter or reviewer that must not share the author's framing).
**Measure inline before you fan out:** when a shell loop or one script run answers the question, run it; a fleet
that only confirms it in parallel buys nothing. When a subagent does pay, brief it as section 2 says.

Roles: the **orchestrator** (your session) plans, dispatches, reconciles, gates and commits, and keeps its own
transcript small: briefs and reports are **files**, and the conversation carries only their paths. Implementers,
reviewers, refuters, registrars and finishers are subagents where the cases above apply. Landing is a deterministic
script, not an agent (the `merge-queue-landing` skill).

## 1. The cost law, which drives the other rules

An agent re-reads its whole context on every turn, so **its token cost grows roughly quadratically with its turn
count**. A long transcript is not a little more expensive. It is usually the largest line item in the campaign:
the few agents that run longest burn a large share of all tokens. The law also condemns any role that does
everything (merge, gate, review, fix, log, push): it runs long, pays the late-turn cost on every step, and needs
successors to finish. Give each role one job.

- **Cap turns per role in the harness, not in the brief**: the role definition's `maxTurns` (about 150–160 turns
  for read-only roles, 220 for implementers; `automating-agent-guardrails`'s `readiness_check.py` fails a role
  without one), or a supervisor that creates the agent's STOP file at its count, so the agent checkpoints and
  returns `SPLIT`. The brief shows the worker no turn number, because a budget shown to the model changes how it
  spends. The harness stops an agent wherever it is, so the checkpoint after every mechanism is what makes the cap
  safe. *Why: a fresh agent starting from a checkpoint pays the low early-turn cost. Extending the old one pays the
  steep late-turn cost.*
- **Split a job that will not fit. Never extend it.** *Why: same curve.*
- **Resuming a long transcript is often more expensive than starting fresh.** *Why: the resumed agent re-reads
  its entire history on every new turn.* Resuming wins when only a few turns remain.
- **Command chaining: targeted rules, not a ban.** (a) Never chain anything after a VERDICT command (build, test,
  gate, a landing script) with `&&`, `||` or `;`: run it alone to a log and read its summary line; to keep the
  status in the same call, append `; echo "EXIT=$?"`. (b) Don't join steps that must stop on failure with `;`,
  and don't `cd` inside a chain (use absolute paths or `git -C`). (c) Short `&&` chains of read-only or fail-fast steps are fine. Enforce (a) with a guard
  hook (`automating-agent-guardrails`, rule `no-chain-after-verdict`).
  *Why: a chain's exit status is its last command's, so `test && git commit` commits on a verdict nobody read.
  But a blanket "never chain" rule turns every chain into extra turns, and turns are the quadratic cost; parallel
  tool calls get the separation without the turns.*

## 2. Inputs: one agent, one self-contained input file

- Give each agent its own input file holding only its slice, uniquely named across every fan-out; write slices programmatically.
- Point the agent at a brief file; never paste the brief into the prompt.
- A workflow launched in a later turn carries the human's authorization, quoted verbatim, at the start of every agent prompt.
- Give an implementer an apply-ready contract (code sites, repro, governing rule, gate command), not a discovery brief.
- The implementer's first step is to re-run each item's repro on its own build; an item that no longer reproduces is DISCHARGED and goes to a refuter.
- Give every implementer one-call orientation: `references/orient.py <files> --notes <dir> --cite "<regex>"` before it reads any source.
- Every lead an agent reports carries its repro and code site; the registrar re-runs each lead's given repro once before filing it.
- Tell the implementer to run the repo's rule query before editing.
- Put no fact in a brief that you have not verified in this session.
- Reconcile the returns against the expected worklist by item identity, then re-run only the missing slices. Never dispatch an agent only to repeat a step whose inputs did not change (a gate at the same head, a probe at the same commit): its record already answers.
- Cap what an agent RETURNS (a summary of a few hundred characters, a short list of leads, a final text of a couple of dozen lines) and put the detail in a report file: everything returned enters the orchestrator's conversation and is re-read on every later turn. Read references/inputs-and-briefs.md for the reason.
- Prefer idempotent outputs over appends to a shared file.

Read `references/inputs-and-briefs.md` before writing any dispatch brief or input slice (it carries the reasons, the measurements and the exact brief wording).

## 3. State the bar, not just the output format

Say in the prompt what would make a returned artifact worthless even though well-formed, and encode it in the schema or validator; spot-check the substance of the results that close something permanently. Read `references/inputs-and-briefs.md` (section 3) when writing the prompt.

## 4. Checkpoint to disk after every unit of work

| job | checkpoint | resume unit |
|---|---|---|
| implementer (own worktree) | a WIP commit on its branch after each mechanism and each gate, and after EVERY commit a rewrite of `STATUS.md`, first line `STATUS-AT: <sha of HEAD>`: `DONE` · `NEXT` (the exact next step) · `BLOCKED` · `GATE` (last verdict line + command) · ids used | one mechanism |
| workflow stage (analyze / refute / draft / validate) | one JSON line per decided item appended to `<out>/<stage>-<slug>.jsonl` **the moment it is decided**; on start, read the file and skip items already there; the final result goes to a separate `out-<slug>.json` | one item |
| finisher (a conflict or a queue bounce) | a commit on the branch after each step, plus `STATUS.md` | one step |
| orchestrator | briefs and reports are files under a scratch directory; the conversation holds pointers | — |

*Why: a session kill takes every decision that is not on disk with it.*

- Never use `git stash` for WIP (including `--autostash`); commit it instead.
- Keep checkpoint files out of landings: gitignore them and unstage them explicitly.
- Assert on conflict markers between staging and committing, reading the OUTPUT of both commands, not their exit codes.
- Stamp the handoff: `STATUS.md` line 1 is `STATUS-AT: <sha>`, written after the checkpoint commit; a resuming agent first runs `references/status_delta.py <worktree>` (CURRENT, STALE by N, UNSTAMPED or DIVERGED).
- Design workflow stages to read their inputs from disk.

Read `references/checkpointing.md` before writing the checkpoint and resume block of a brief, and before resuming a worktree or merging a predecessor's branch.

## 5. The concurrency budget and stopping before the limit

- Default budget: ~3-6 implementers + a reviewer per DONE branch + one read-only chunk ~4 wide; finishers as bounces arrive; run big fan-outs as `parallel()` chunks in a loop.
- A fleet of more than ~40 agents means you split the work. Drive the stop thresholds from the real usage meter the project names: at ~75 % dispatch only finishers of nearly finished work, at ~85-90 % create STOP.

- **Use a graceful STOP file.** Every dispatch prompt includes: *"Before each new step, check for
  `{SCRATCH}/STOP`. If it exists, checkpoint-commit, write STATUS.md NEXT, and return status SPLIT. Never
  start a build or gate once STOP exists."* To stop, create the file, wait for the agents to return, and only
  then kill any stragglers. *Why: workflow agents can't be messaged, and a hard kill lands mid-step.*

- Verify every launch started: within a few minutes of a dispatch, each agent has a journal `started` record or a transcript. A spawn failure leaves neither, so no watchdog sees it.
- Run `references/stall_watch.py <workflow transcript dir>` in the background next to EVERY fleet workflow; stop it when the completion notice arrives. A death it reports (a journal `failed` record) is decided at once: a finisher resumes the branch from its checkpoint, or the branch is recorded as abandoned with the reason.
- A stalled agent: let the others finish, then stop the workflow and dispatch the remainder by hand.
- An agent never ends its turn while its own background job runs: block with `timeout 580 bash -c 'until grep -q "<verdict>" <log>; do sleep 5; done'`, never `tail -f <log> | grep -m1`.

Read `references/concurrency-and-watchdog.md` before sizing a fleet, before starting a background workflow, and before deciding that an agent is stalled or dead.

## 6. Land finished work before starting new work

Finished work lands before new work starts, one pull request per branch through the project's enqueue step. The
`merge-queue-landing` skill holds the landing: the enqueue step, the gate record it reads, review before landing,
finishers and bounces. Load it before scripting a wave or landing a branch.

## 7. Group related fixes for each implementer

- The unit for a slot is a group: the top-ranked item plus every open item sharing its source files or rule family; compute groups with `references/fix_clusters.py`, never by hand.
- A file with more open items than the cluster cap gets same-file successors (`after`), not an independent second group.
- A successor starts once its predecessor's review loop has ended and merges the predecessor's REVIEWED head (the finisher's, when one ran), so every link carries the review fixes before it; nothing waits for a successor to land.
- Fill parallel slots with one group per subsystem; cluster leads by root cause; never put two unrelated mechanisms in one transcript.

Read `references/grouping-fixes.md` before filling implementer slots or assigning defects.


## 8. No shared next slot: allocate ids centrally

Two branches must never be able to take the same slot. The orchestrator allocates every id an agent might mint
(work-item ids, error-code ranges, report filenames) in the dispatch brief, from ONE allocator that reads the truth
from the tree (the next id is one past the larger of what the tree holds and what is already reserved), never from a
snapshot. Agents never pick their own. A sequence number that must follow landing order (a log entry's number) is
stamped by the enqueue step, after it merges the default branch in, never by the implementer. A registry, table or
enum that parallel branches extend is keyed by name or kept as one file per entry, never by an ordinal the next
branch can also take. Each fleet's scratch directory, STOP file and logs are its own, so one fleet's STOP never stops
another's agents. *Why: each collision costs a renumbering pass and often a bounce, and parallel agents that pick
names overwrite each other's reports.*

## 9. Isolation and the frozen tree

- **Analysis fleets probe a pinned, read-only worktree** (`git worktree add --detach <path> <sha>`, built once
  there). *Why: a landing that rebuilds the main tree swaps binaries under running probes.*
- **While a fleet or long gate is running, the tree it reads is frozen**: no edits and no builds. If the fix
  can't wait, stop the fleet. *Why: probes against a moving binary produce results you must disclaim. A
  "file locked by another process" build error is the alarm, not a transient.* The freeze blocks edits and
  builds, not drafting in the scratchpad.

## 10. Adversarial refuters on closing verdicts

- Any verdict that closes something permanently goes to a second, independent agent told to overturn it, seeing only the claim and the evidence, in chunks ~4 wide checkpointed per item.
- Keep verdicts per claim AND per piece of evidence; key the integration on (claim, evidence).

## 11. Measure cost per unit and route to the cheapest lane

- Measure tokens per closed unit for each lane and route each item to the cheapest lane that moves the reported metric.
- Each role's definition fixes its tier and effort, in the three tiers [`role-agents.md`](../automating-agent-guardrails/references/role-agents.md) defines: the **worker tier** for implementers, finishers, reviewers and refuters (effort `medium`, raised only where a measurement shows a gain), the **mechanical tier** for filing, lookups and formatting (effort `low`), and the **orchestrator tier** for planning and hard judgment. A per-call model overrides the role's, so pass one only to a role that inherits, or as a recorded per-item escalation (the wave script's per-group `model`), the one exception `role-agents.md` item 4 allows.
- An orchestrator-tier dispatch is an escalation for one item the worker tier has failed twice, never a default, because it draws the same weekly pool faster. Where a person owns the quota, each such dispatch needs their explicit approval for THAT dispatch.
- Precompute discovery; self-review before a large review fleet.

Read `references/refuters-and-routing.md` before dispatching a refuter, and before choosing a lane or a model for a role.

## 12. After a fleet, and on restart

- After any fleet that could touch the tree, run `git status --short` and account for every path before `git add -A`.
- For a long or unattended campaign, run the orchestrator as a supervisor of short `claude -p` units, with deterministic scripts doing the planning. Read `references/orchestrator-loop.md` before writing or running that supervisor: it holds the unit-lifetime, handoff and stop mechanisms the CLI requires.
- On restart: read the reset time, check each dead agent's worktree and `STATUS.md`, run `references/status_delta.py` on each worktree, re-run the enqueue step for every DONE branch not yet queued, and dispatch fresh agents from the checkpoints in priority order.

## Standards

- Every implementer brief carries the quality bar and names the project's own rules; forbid the smallest-diff fix that contradicts the bar.
- The report states what was swept and which invariants or drift tests were added; refuters check the standards too.

Read `references/restart-and-standards.md` after a fleet, on restart, and before writing an implementer brief's quality bar.


## Brief template

`references/brief-template.md` is a copy-and-fill dispatch brief that already carries the checkpoint, STOP,
blocking-gate, finishing and report rules. Point each agent at a rendered copy; don't paste it.
