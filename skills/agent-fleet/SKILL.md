---
name: agent-fleet
description: Use before dispatching more than a couple of parallel subagents or a multi-agent workflow on a long-running engineering campaign — so a session-limit kill costs at most one step, a restart never repeats work, and the token budget is spent where it moves the needle.
---

# Agent fleet: restart-safe, budget-aware orchestration

A fleet of parallel agents can burn a session window in minutes and then die all at once when the window closes.
Everything here serves three goals:

1. **A kill costs at most one step.** Work is checkpointed to disk per unit, never held only in a transcript.
2. **A restart never repeats work.** Fresh agents read the checkpoint and skip what is already decided.
3. **Tokens go where they move the metric.** Cost is measured per unit, and work is routed to the cheapest lane.

Roles: the **orchestrator** (your session) plans, dispatches, reconciles, gates and commits. Every other job
(probe, implement, file leads as work items, validate, adversarial review, finish a bounced branch) is a subagent,
and landing itself is a deterministic script. The orchestrator keeps its own transcript
short: reports and briefs are **files**, and the conversation carries only paths to them.

## 1. The cost law, which drives the other rules

An agent re-reads its whole context on every turn, so **its token cost grows roughly quadratically with its turn
count**. A long transcript is not a little more expensive. It is usually the largest line item in the campaign.
In one measured campaign, the ~8 % of agents that ran 250+ turns burned ~39 % of all tokens, and capping them at
150 turns would have cut that cost by almost half. *(Practice — not yet validated: this law and the caps below: the curve was refit on a newer model with different coefficients, and the saving from splitting, net of the successor's orientation, was never measured.)*
The law also condemns any role that does everything: in one measured campaign (2026-10-10) a lander that merged,
gated the whole population twice, reviewed, fixed, logged and pushed took 10 agents to land 6 trains, and 41 % of its
567 minutes were local gate runs that CI repeated on free runners. *(Validated 2026-10-11 (measurement); the redesign
in section 6, which replaces the lander with a script, is not yet measured.)*

- **Set a hard turn cap per role**, for example ~150–160 for read-only agents and ~220 for implementers. At the
  cap the agent checkpoints, reports what it decided, names what it didn't, and returns `SPLIT`.
  *Why: a fresh agent starting from a checkpoint pays the low early-turn cost. Extending the old one pays the
  steep late-turn cost.*
- **Split a job that will not fit. Never extend it.** *Why: same curve.*
- **Resuming a long transcript is often more expensive than starting fresh.** *Why: the resumed agent re-reads
  its entire history on every new turn.* *(Practice — not yet validated: resuming versus starting fresh from a checkpoint was never measured head to head; resuming wins when only a few turns remain.)*
- **Command chaining: targeted rules, not a ban.** (a) Never chain anything after a VERDICT command (build, test,
  gate, a landing script) with `&&`, `||` or `;`: run it alone to a log and read its summary line; to keep the
  status in the same call, append `; echo "EXIT=$?"`. (b) Don't join steps that must stop on failure with `;`,
  and don't `cd` inside a chain (use absolute paths or `git -C`). (c) Send INDEPENDENT commands as parallel tool
  calls in ONE turn. (d) Short `&&` chains of read-only or fail-fast steps are fine. Enforce (a) with a guard
  hook (`automating-agent-guardrails`, rule `no-chain-after-verdict`).
  *Why: a chain's exit status is its last command's, so `test && git commit` commits on a verdict nobody read.
  But a blanket "never chain" rule turns every chain into extra turns, and turns are the quadratic cost; parallel
  tool calls get the separation without the turns.* *(Rule (a) validated 2026-09-28. The targeted form instead of a
  blanket ban is practice, not yet validated: no production count of blocks, false positives or turns saved.)*

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
- Reconcile the returns against the expected worklist by item identity, then re-run only the missing slices.
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

*Why: un-checkpointed refuters lost 100 % of their decisions to a single session kill.* *(Practice — not yet validated: the loss is recorded, but a reliable checkpoint is not yet shown: 3 of 14 finished branches still ended with a stale `STATUS.md`.)*

- Never use `git stash` for WIP (including `--autostash`); commit it instead.
- Keep checkpoint files out of landings: gitignore them and unstage them explicitly.
- Assert on conflict markers between staging and committing, reading the OUTPUT of both commands, not their exit codes.
- Stamp the handoff: `STATUS.md` line 1 is `STATUS-AT: <sha>`, written after the checkpoint commit; a resuming agent first runs `references/status_delta.py <worktree>` (CURRENT, STALE by N, UNSTAMPED or DIVERGED).
- Design workflow stages to read their inputs from disk.

Read `references/checkpointing.md` before writing the checkpoint and resume block of a brief, and before resuming a worktree or merging a predecessor's branch.

## 5. The concurrency budget and stopping before the limit

- Default budget: ~3-6 implementers + a reviewer per DONE branch + one read-only chunk ~4 wide; finishers as bounces arrive; run big fan-outs as `parallel()` chunks in a loop.
- A fleet of more than ~40 agents means you split the work. Keep a running tally; at ~75 % dispatch only finishers, at ~85-90 % stop gracefully.

- **Use a graceful STOP file.** Every dispatch prompt includes: *"Before each new step, check for
  `{SCRATCH}/STOP`. If it exists, checkpoint-commit, write STATUS.md NEXT, and return status SPLIT. Never
  start a build or gate once STOP exists."* To stop, create the file, wait for the agents to return, and only
  then kill any stragglers. *Why: workflow agents can't be messaged, and a hard kill lands mid-step.* *(Validated 2026-09-28.)*

- Judge a background workflow's liveness by its processes and its journal, never by transcript file times.
- Run `references/stall_watch.py <workflow transcript dir>` in the background next to EVERY fleet workflow; stop it when the completion notice arrives.
- A stalled agent: let the others finish, then stop the workflow and dispatch the remainder by hand.
- Late in a window dispatch short jobs close to done; early in a window dispatch long ones.
- An agent never ends its turn while its own background job runs: block with `timeout 580 bash -c 'until grep -q "<verdict>" <log>; do sleep 5; done'`, never `tail -f <log> | grep -m1`.

Read `references/concurrency-and-watchdog.md` before sizing a fleet, before starting a background workflow, and before deciding that an agent is stalled or dead.

## 6. Land finished work before starting new work

- Land finished work first, as **one pull request per finished branch through a merge queue** on the protected branch (a ruleset: PRs required, merge commits so branch commits stay ancestors, the required check on the merge group, enforced for administrators). No lander, no train, no lease.
- Every change's local gate is the TARGETED leg (its own tests, the likely reds, the cases its diff reaches, and the host-only witnesses), run natively and then, under the same gate slot, in a clone on the other OS the project supports, fail-fast native first; CI's merge-group run is the whole-population regression net and the only whole-population run (CI's full legs run locally only to reproduce a CI red).
- The landing step is a deterministic **enqueue** script (fetch, rebase, the targeted gate under the gate-slot cap, stamp the log entry, the landing checks, open the PR, queue it); dispatch a **finisher** only for a rebase conflict or a queue bounce.
- **Finished work is never held.** A branch reviewed CLEAN is enqueued at once, successor or not; a same-file successor merges its predecessor's REVIEWED head and its pull request merges on top. The landing order is communicated, never enforced by holding.
- Review each branch the moment it is DONE, inside the wave, with a read-only reviewer; a finding goes back to a finisher, never to the landing step. Round 1 reviews the whole branch; a re-review reads ONLY the finisher's diff since the last reviewed head. Critical and high findings block; medium blocks until the round cap, then becomes a lead; low never blocks and is written as a lead.
- "Does this branch carry unanswered blocking findings?" has ONE source of truth, the findings file's last verdict, read by ONE function from the wave and the landing survey alike, never from a report stamp. A torn findings file holds every branch it names until a person repairs it.
- Fill a freed implementer slot in the same turn, with the rolling wave (`references/rolling-wave.js`), never a barrier.
- Keep landing files conflict-free: one log file per entry, generated views out of the tree, one line-ending format (LF).
- Watch CI for every run that decides something; a red on the default branch is a blocking fix, landed alone. Run the comprehensive battery in its own detached worktree. Assert on conflict markers before every commit.
- Measure per landing (DONE → enqueued → merged, bounces and causes, CI wall) and compare with the measurement before the change.

Read `references/landing.md` before scripting a wave, writing or running the enqueue step, dispatching a finisher, running the battery, or changing CI or the ruleset.

## 7. Group related fixes for each implementer

- The unit for a slot is a group: the top-ranked item plus every open item sharing its source files or rule family; compute groups with `references/fix_clusters.py`, never by hand.
- A file with more open items than the cluster cap gets same-file successors (`after`), not an independent second group.
- A successor starts once its predecessor's review loop has ended and merges the predecessor's REVIEWED head (the finisher's, when one ran), so every link carries the review fixes before it; nothing waits for a successor to land.
- Fill parallel slots with one group per subsystem; cluster leads by root cause; never put two unrelated mechanisms in one transcript.

Read `references/grouping-fixes.md` before filling implementer slots or assigning defects.


## 8. Allocate ids centrally

The orchestrator allocates every id an agent might mint (work-item ids, error-code ranges, report filenames,
log entry numbers) in the dispatch brief. Agents never pick their own. A sequence number that must follow landing order
(a log entry's number) is stamped by the enqueue step, after the final rebase, never by the implementer.
*Why: five id collisions in one day each cost a renumbering pass. Parallel landing agents overwrote each other's
reports.* *(Practice — not yet validated: collisions recurred whenever a second allocator existed, or when ids were taken from a snapshot instead of
the tree.)*

## 9. Isolation, the frozen tree, and the completion signal

- **Analysis fleets probe a pinned, read-only worktree** (`git worktree add --detach <path> <sha>`, built once
  there). *Why: a landing that rebuilds the main tree swaps binaries under running probes.* *(Practice — not yet validated: no before/after measure of contaminated results.)*
- **While a fleet or long gate is running, the tree it reads is frozen**: no edits and no builds. If the fix
  can't wait, stop the fleet. *Why: probes against a moving binary produce results you must disclaim. A
  "file locked by another process" build error is the alarm, not a transient.* *(Practice — not yet validated: the written freeze was broken repeatedly, and its effect was never measured.)*
- **Work through the freeze in the scratchpad.** Draft the next landing to apply-ready precision: full edited
  files, expected values, commit message. *Why: the freeze blocks only edits and builds, and ending the turn
  "waiting" wastes the time.* *(Practice — not yet validated: no measured benefit.)*
- **Never poll a running fleet's output directory.** Wait for the harness's completion notification.
  *Why: stage-1 and stage-2 outputs can share a filename and a shape. An adversarial stage 2 only ever removes
  confidence, so an early read is biased toward a result that looks better than the truth. One early merge
  moved 10 of 55 results.* If you must read early, have each stage write to a different path. *(Validated 2026-09-28.)*
- **Measure inline before you fan out.** Dispatch a fleet only for real parallel breadth or independent
  adversarial judgement, never to "confirm in parallel" something a shell loop already answered. *(Practice — not yet validated: no later measured saving.)*

## 10. Adversarial refuters on closing verdicts

- Any verdict that closes something permanently goes to a second, independent agent told to overturn it, seeing only the claim and the evidence, in chunks ~4 wide checkpointed per item.
- Keep verdicts per claim AND per piece of evidence; key the integration on (claim, evidence).

## 11. Measure cost per unit and route to the cheapest lane

- Measure tokens per closed unit for each lane and route each item to the cheapest lane that moves the reported metric.
- The model follows the ROLE, set in the role definition, never per call; a premium model is a per-item escalation, never a default, and where a person owns the quota each premium dispatch needs their explicit approval.
- Precompute discovery; self-review before a large review fleet.

Read `references/refuters-and-routing.md` before dispatching a refuter, and before choosing a lane or a model for a role.

## 12. After a fleet, and on restart

- After any fleet that could touch the tree, run `git status --short` and account for every path before `git add -A`.
- For a long or unattended campaign, run the orchestrator as a supervisor of short units with deterministic scripts doing the planning (`references/orchestrator-loop.md`, validated in live runs of one campaign). Three rules from those runs: the SUPERVISOR owns each unit's lifetime (a one-shot `claude -p` terminates background tasks 600 s after its model ends a turn; start the unit with `--input-format stream-json` and keep stdin open, closing it only when the model is idle with no background task); write frequent handoffs (a supervisor-written checkpoint, model milestone lines, and a handoff synthesized when a unit dies); and make STOP a wind-down that checkpoints the fleet, never a kill. Measure where the tokens go first; the reference also lists the published techniques that bear on a campaign.
- On restart: read the reset time, check each dead agent's worktree and `STATUS.md`, run `references/status_delta.py` on each worktree, re-run the enqueue step for every DONE branch not yet queued, and dispatch fresh agents from the checkpoints in priority order.

## Standards

- Every implementer brief carries the quality bar and names the project's own rules; forbid the smallest-diff fix that contradicts the bar.
- The report states what was swept and which invariants or drift tests were added; refuters check the standards too.

Read `references/restart-and-standards.md` after a fleet, on restart, and before writing an implementer brief's quality bar.


## Brief template

`references/brief-template.md` is a copy-and-fill dispatch brief that already carries the checkpoint, STOP,
turn cap, blocking-gate and report rules. Point each agent at a rendered copy; don't paste it.
