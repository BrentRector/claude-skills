# agent-fleet

Running many parallel Claude subagents on a long engineering campaign fails in predictable ways. The session
window closes and kills every live agent at once, so hours of work held only in transcripts disappear. A restart
repeats work that was already decided. And the token budget goes to long, expensive transcripts instead of to the
work that moves the result. This skill is a set of orchestration rules that make a fleet **restart-safe** (a kill
costs at most one step, a restart never repeats work) and **budget-aware** (tokens are spent where they move the
metric you report).

The full rules are in [`SKILL.md`](SKILL.md). This page explains what they are and why they exist.

## When Claude uses it

The skill's description tells Claude to load it **before dispatching more than a couple of parallel subagents or a
multi-agent workflow** on a long-running campaign. Skills load automatically when the description matches the
task, so asking Claude to "fan this out across agents", "run a fleet over these items" or "dispatch implementers
for these fixes" is usually enough. You can also name it explicitly ("use the agent-fleet skill").

## What it does

The skill splits the work into roles. The **orchestrator** (your own session) plans, dispatches, reconciles,
gates and commits. Every other job (probe, implement, validate, adversarial review, land) is a subagent. The
orchestrator keeps its own transcript short: briefs and reports are files, and the conversation carries only
their paths.

A campaign run under the skill looks like this:

1. **Write one brief per agent** from [`references/brief-template.md`](references/brief-template.md), rendered by
   a script into `{SCRATCH}/briefs/<wave>-<slug>.md`. Each brief holds only that agent's slice, an apply-ready
   contract (code sites, repro, governing rule, gate command), the "worthless even if well-formed" bar, and the
   ids allocated to it. The agent's prompt is a single line: *"Read and follow `{SCRATCH}/briefs/<file>`."*
2. **Dispatch within the concurrency budget**: by default 1 lander, a handful of implementers (~3–6) and one
   read-only chunk about 4 wide. Each implementer gets a *group* of related items (same files or rule family),
   and parallel slots get one group per subsystem.
3. **Agents checkpoint after every unit**: implementers make a WIP commit and update `STATUS.md`
   (`DONE` / `NEXT` / `BLOCKED` / `GATE` / ids used); workflow stages append one JSON line per decided item and skip
   items already on disk when they start.
4. **Agents obey the stop rules**: a hard turn cap per role (e.g. ~160 read-only, ~220 implementer), a graceful
   `{SCRATCH}/STOP` file checked before every step, and never ending a turn while their own background gate runs.
5. **Reconcile the returns** against the expected worklist (missing, duplicated, extra) and re-run only the gaps.
6. **Send closing verdicts to adversarial refuters**, small independent agents told to overturn the claim.
7. **Land finished work first**: one lander on main at a time, 4–6 finished clusters per landing with one commit
   each, gated on the whole unfiltered test suite, then watch CI for the pushed head.
8. **After the fleet**, run `git status --short` and account for every unexpected path before staging.

On restart after a cutoff, the skill's recovery procedure is: read the reset time from the limit message, check
`git status` on main (a dead lander may already have applied its patch), inspect each worktree's `STATUS.md`, and
dispatch **fresh** agents from the checkpoints in landing order.

### The brief template

[`references/brief-template.md`](references/brief-template.md) is a copy-and-fill dispatch brief. Its sections are:

| Section | What you fill in |
|---|---|
| Role | implementer, analyst, refuter or lander, plus the slug and wave |
| Your input | the items for this agent only, embedded or as a path to a file holding only this slice |
| Contract | code sites (`file:line`), exact repro, verified governing rule, narrow gate command |
| The bar | what would make the output worthless even though it is well-formed |
| Allocated to you | id ranges, code ranges, the report path — agents never mint their own |
| Checkpoint protocol | WIP commits + `STATUS.md` for worktree agents; JSONL-per-item for workflow stages |
| Stop rules | the STOP file, the turn cap, and blocking on background jobs with `timeout 580 bash -c 'tail -n +1 -f <log> \| grep -m1 "<verdict>"'` |
| Ground rules | write only in your worktree or scratch; every reported lead carries repro and code site |
| Report | 60 lines or fewer: status, one section per item, leads, NEXT if split |

Render copies with a script rather than by hand, and point each agent at its rendered copy instead of pasting it.

## Why it works this way

Every rule in the skill carries its own *Why*. The main ones:

| Rule | The failure it prevents |
|---|---|
| Hard turn caps; split a job, never extend it | An agent re-reads its whole context every turn, so cost grows roughly quadratically with turns. In one measured campaign, the ~8 % of agents that ran 250+ turns burned ~39 % of all tokens. A fresh agent from a checkpoint pays the cheap early-turn cost. |
| One self-contained input file per agent | Agents miscount indices into a shared list: one fan-out double-processed four items and skipped five. |
| Point agents at a brief file, not a pasted prompt | A file can be re-read after a restart; a prompt dies with its transcript. |
| Apply-ready contracts for implementers | Search and read turns are the largest share of implementer tokens; rediscovering a subsystem costs more than fixing it. |
| Only verified facts in a brief | Agents inherit a confident wrong citation and carry it into code. |
| State the bar, not just the format | Agents optimize the criterion you wrote down; a shape validator passes worthless-but-valid work. |
| Checkpoint to disk after every unit | Un-checkpointed refuters lost 100 % of their decisions to a single session kill. |
| Never `git stash` (including `--autostash`) | The stash stack is shared by every linked worktree, so one agent's `stash pop` can take another's work. |
| Concurrency budget and a token tally | ~28 concurrent agents burned ~20 % of a window in 11 minutes; ~50 exhausted a window in ~2.5 h. The limit kills landers mid-landing. |
| Graceful STOP file | Workflow agents can't be messaged, and a hard kill lands mid-step. |
| Land finished work first; batch 4–6 clusters | Ready work once sat behind a serialized lander when the limit hit. A landing is mostly fixed cost, so per-cluster cost roughly halves from 1 to 5 clusters. |
| The lander gates the whole suite | The tests no implementer's filter names are exactly the ones that go red in CI. |
| Group related fixes per implementer | Separate implementers on the same files produced merge conflicts and composition defects neither could see. |
| Central id allocation | Five id collisions in one day each cost a renumbering pass; parallel landers overwrote each other's reports. |
| Pinned read-only worktree; frozen tree during a fleet | A landing that rebuilds the main tree swaps binaries under running probes. |
| Never poll a fleet's output directory | An adversarial stage 2 only removes confidence, so an early read is biased upward. One early merge moved 10 of 55 results. |
| Adversarial refuters on closing verdicts | The first agent's framing is contagious; only an agent hunting a counter-example finds the well-formed-but-wrong result. |
| Verdicts keyed on (claim, evidence) | Pooling overturns by claim dropped valid evidence and recorded evidence nobody judged. |
| Measure cost per unit per lane | Cost per unit can differ by ~10× across lanes; a large review fleet can burn billions of tokens for single-digit movement. |
| `git status` before `git add -A` | Agents drop files into the repo root despite scratch-only rules; the prompt constrains intent, not effects. |

## Using it in your project

- **Your project's rules.** The skill tells every implementer brief to name the project's own rules alongside the
  quality bar, and the brief template leaves the gate commands, id ranges and paths as placeholders for you to
  fill. The repo-wide convention (see the [top-level README](../../README.md#adapting-to-your-project)) is that your
  `CLAUDE.md` supplies commands and tightens rules, and wins on conflict.
- **Prerequisites.** Git with worktree support (implementers and pinned analysis probes each use a worktree),
  a subagent or workflow tool, and a shell that can run `timeout`, `tail` and `grep` for the blocking-gate pattern.
- **Composes with:**
  - [`engineering-standards`](../engineering-standards/SKILL.md) — the quality bar every implementer brief must
    carry. Briefs also tell implementers to run that skill's rule query for the files they will touch
    (`engineering-standards/references/rule_index.py --tests "<glob>" <files>`, or the repo's own) before editing.
  - [`test-gate`](../test-gate/SKILL.md) — how implementers and the lander choose and read their gates.
  - [`review`](../review/SKILL.md) and [`spec-compliance-audit`](../spec-compliance-audit/SKILL.md) — fleets whose
    closing verdicts go through the refuter step described here.
  - [`claude-cloud-sessions`](../claude-cloud-sessions/SKILL.md) — the same restart-safety rules applied to fleets
    running on cloud VMs.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The rules Claude follows, each with its reason |
| [`references/brief-template.md`](references/brief-template.md) | Copy-and-fill dispatch brief carrying the checkpoint, STOP, turn-cap, blocking-gate and report rules |
| `README.md` | This page |
