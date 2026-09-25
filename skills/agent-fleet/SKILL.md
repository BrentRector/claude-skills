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
(probe, implement, validate, adversarial review, land) is a subagent. The orchestrator keeps its own transcript
short: reports and briefs are **files**, and the conversation carries only paths to them.

## 1. The cost law, which drives the other rules

An agent re-reads its whole context on every turn, so **its token cost grows roughly quadratically with its turn
count**. A long transcript is not a little more expensive. It is usually the largest line item in the campaign.
In one measured campaign, the ~8 % of agents that ran 250+ turns burned ~39 % of all tokens, and capping them at
150 turns would have cut that cost by almost half.

- **Set a hard turn cap per role**, for example ~150–160 for read-only agents and ~220 for implementers. At the
  cap the agent checkpoints, reports what it decided, names what it didn't, and returns `SPLIT`.
  *Why: a fresh agent starting from a checkpoint pays the low early-turn cost. Extending the old one pays the
  steep late-turn cost.*
- **Split a job that will not fit. Never extend it.** *Why: same curve.*
- **Resuming a long transcript is often more expensive than starting fresh.** *Why: the resumed agent re-reads
  its entire history on every new turn.*

## 2. Inputs: one agent, one self-contained input file

- **Give each agent its own input file** that holds ONLY its slice, or put a small slice directly in the prompt.
  Never write "read the shared list and process element k".
  *Why: agents miscount indices. One fan-out double-processed four items and skipped five.*
- **Write slices programmatically**, not by retyping. *Why: hand-copied data (especially Unicode) drifts.*
- **Point the agent at the brief file instead of pasting the brief into the prompt.**
  *Why: a file can be re-read after a restart. A prompt is gone with its transcript.*
- **Give an implementer an apply-ready contract instead of a discovery brief**: code sites (`file:line`), the
  repro, the governing rule, and the gate command.
  *Why: search and read turns are the largest share of implementer tokens. Rediscovering a subsystem costs more
  than fixing it.*
- **Every lead an agent reports carries its repro and code site.** *Why: otherwise the triager and the next
  implementer each find the same fact again.*
- **Tell the implementer to ask the structural rules before editing.** When the repo encodes invariants as drift
  tests, the brief says: run the rule query for the files you will touch (`engineering-standards/references/rule_index.py --tests "<glob>" <files>`, or the repo's own) and honor every specific rule it prints; if you keep a checker for your briefs, make it fail a brief
  that drops the line. *Why: the rules live in the tests, so an agent that is not pointed at them learns each one only by tripping it
  at the gate — a full gate cycle per rule.*
- **Don't put a fact in a brief that you haven't verified in this session** (a spec clause number, an API name,
  a path). *Why: agents inherit a confident wrong citation and carry it into code.*
- **Reconcile the returns against the expected worklist** before you act: which items came back, which came
  back twice, which are missing. Then re-run only the missing slices.
  *Why: silent gaps in coverage look like a clean result.*
- **Prefer idempotent outputs** (an agent writes its whole artifact) over blind appends to a shared file.
  *Why: an accidental double run is harmless with last-write-wins and corrupts data with appends.*

## 3. State the bar, not just the output format

Before dispatching, ask what would make a returned artifact **worthless even though it is well-formed**, and say
so in the prompt. Then encode that in the schema or the validator.

*Why: agents optimize for the criterion you actually wrote down. A shape validator passes worthless-but-valid
work, and the defect arrives already validated.* Example: a prompt that says "cite a covering test that exists
on disk" will get tests that exist. A prompt that says "…derived from the specification, not a differential
against another implementation" gets tests that count.

When a batch looks uniformly right, spot-check the **substance** of the results with the biggest consequences
(the ones that close something permanently), not the format of all of them.

## 4. Checkpoint to disk after every unit of work

| job | checkpoint | resume unit |
|---|---|---|
| implementer (own worktree) | a WIP commit on its branch after each mechanism and each gate, plus `STATUS.md`: `DONE` · `NEXT` (the exact next step) · `BLOCKED` · `GATE` (last verdict line + command) · ids used | one mechanism |
| workflow stage (analyze / refute / draft / validate) | one JSON line per decided item appended to `<out>/<stage>-<slug>.jsonl` **the moment it is decided**; on start, read the file and skip items already there; the final result goes to a separate `out-<slug>.json` | one item |
| lander | a commit in its worktree after each numbered step, plus `STATUS.md` | one step |
| orchestrator | briefs and reports are files under a scratch directory; the conversation holds pointers | — |

*Why: un-checkpointed refuters lost 100 % of their decisions to a single session kill.*

- **Never use `git stash` for WIP; commit it instead** - and that includes the implicit stash of
  `git rebase --autostash` / `git pull --autostash`. *Why: the stash stack is shared by every linked worktree, so one
  agent's `stash pop` can take another agent's work.*
- **Keep checkpoint files out of landings**: add them to `.gitignore` and unstage them explicitly before
  committing. *Why: a checkpoint that reaches main conflicts with the next agent's checkpoint.*
- **Design workflow stages to read their inputs from disk** (`out-<slug>.json`). *Why: then a rewritten or
  resumed script never re-runs completed stages.*

## 5. The concurrency budget and stopping before the limit

- **Default budget: 1 lander + a handful of implementers (~3–6) + one read-only chunk ~4 wide.** Run big
  fan-outs as `parallel()` chunks inside a loop, not as one very wide pipeline.
  *Why: in one measurement, ~28 concurrent agents burned ~20 % of a session window in 11 minutes, and ~50
  exhausted a window in ~2.5 h.*
- **Tokens are what the quota rations, not slots.** The turn caps control spend. The budget is for containing
  errors. *Why: a few long agents cost more than many short ones.*
- **A fleet of more than ~40 agents means you should split the work.** Don't wait it out.
- **Keep a running tally** of subagent tokens since the window began. At ~75 % of the working budget, dispatch
  only finishers and landers of nearly finished work. At ~85–90 %, stop everything gracefully.
  *Why: the limit kills every live agent at once, including landers partway through a landing.*
- **Use a graceful STOP file.** Every dispatch prompt includes: *"Before each new step, check for
  `{SCRATCH}/STOP`. If it exists, checkpoint-commit, write STATUS.md NEXT, and return status SPLIT. Never
  start a build or gate once STOP exists."* To stop, create the file, wait for the agents to return, and only
  then kill any stragglers. *Why: workflow agents can't be messaged, and a hard kill lands mid-step.*
- **Late in a window, dispatch short jobs that are close to done. Early in a window, dispatch long ones.**
  *Why: that way a burst can't exhaust the window before anything is finished.*
- **An agent never ends its turn while its own background job is running.** It starts the job with output to a
  log, then blocks in the foreground (for example `timeout 580 bash -c 'tail -f <log> | grep -m1 "<verdict>"'`),
  reissuing that until the verdict prints. *Why: an agent that returns early gets its background gate killed,
  and it reports "PENDING".*

## 6. Land finished work before starting new work

- **Land finished work first**, and queue read-only fleets behind landings. *Why: when a limit hit, work that
  was ready still sat waiting on a serialized lander.*
- **One lander on main at a time, and one landing per lander transcript.** *Why: ordering. Also, four landings
  in one transcript cost about twice as much as four fresh landers.*
- **Batch 4–6 finished clusters per landing**, with one commit per cluster so a red result bisects cleanly.
  *Why: a landing is mostly fixed cost (merge, build, gate, push). Per-cluster cost roughly halves from k=1 to
  k=5, and beyond ~6 the gate becomes hard to attribute.*
- **The lander gates the WHOLE test suite, unfiltered**, not the union of the implementers' filters.
  *Why: the tests that no filter names are exactly the ones that go red in CI.*
- **Implementers gate narrowly** (their own tests plus drift and unit checks) at low process priority.
  *Why: when many implementers run the full suite, they triple the lander's gate time.*
- **Fill a freed implementer slot in the same turn it frees**, from a standing queue of apply-ready contracts.
  *Why: idle slots behind landings once held a fix lane under 15 % utilization for days.*
- **Watch CI for every pushed head.** A red run is a blocking fix, landed alone.

## 7. Group related fixes for each implementer

- **The unit you fill a slot with is a group**: the top-ranked item plus every open item that shares its source
  files or rule family (3–4 items, one branch, one gate, one report with a section per item). Inside the group,
  each item is still fixed at its root and checkpointed separately.
  *Why: separate implementers on the same files produced merge conflicts and composition defects that neither
  could see.*
- **Fill parallel slots with one group per subsystem**, not the next N items down the rank list.
  *Why: consecutive items in one area serialize on conflicts.*
- **Cluster leads by root cause before dispatching.** *Why: one mechanism, one fix, one agent.*
- **Don't put two unrelated mechanisms in one transcript.** *Why: the second mechanism costs more than a
  whole fresh implementer.*

## 8. Allocate ids centrally

The orchestrator allocates every id an agent might mint (work-item ids, error-code ranges, report filenames,
log entry numbers) in the dispatch brief. Agents never pick their own. Sequence numbers that must be contiguous
(changelog entries) are read from the file at landing time, after the final rebase.
*Why: five id collisions in one day each cost a renumbering pass. Parallel landers overwrote each other's
reports.*

## 9. Isolation, the frozen tree, and the completion signal

- **Analysis fleets probe a pinned, read-only worktree** (`git worktree add --detach <path> <sha>`, built once
  there). *Why: a landing that rebuilds the main tree swaps binaries under running probes.*
- **While a fleet or long gate is running, the tree it reads is frozen**: no edits and no builds. If the fix
  can't wait, stop the fleet. *Why: probes against a moving binary produce results you must disclaim. A
  "file locked by another process" build error is the alarm, not a transient.*
- **Work through the freeze in the scratchpad.** Draft the next landing to apply-ready precision: full edited
  files, expected values, commit message. *Why: the freeze blocks only edits and builds, and ending the turn
  "waiting" wastes the time.*
- **Never poll a running fleet's output directory.** Wait for the harness's completion notification.
  *Why: stage-1 and stage-2 outputs can share a filename and a shape. An adversarial stage 2 only ever removes
  confidence, so an early read is biased toward a result that looks better than the truth. One early merge
  moved 10 of 55 results.* If you must read early, have each stage write to a different path.
- **Measure inline before you fan out.** Dispatch a fleet only for real parallel breadth or independent
  adversarial judgement, never to "confirm in parallel" something a shell loop already answered.

## 10. Adversarial refuters on closing verdicts

Any verdict that **closes** something permanently (an item fixed, a requirement met, a finding dismissed) goes
through a second, independent agent told to **overturn** it, and that agent sees only the claim and the evidence.
Run refuters in small chunks (~4 wide) that are checkpointed per item.
*Why: the first agent's framing is contagious. Only an agent looking for a counter-example finds the
well-formed-but-wrong result.* Refuters check the **substance** of the evidence (for example, was the expected
value derived from the authority), not its format.
- **Keep verdicts per claim AND per piece of evidence.** When one piece of evidence (a test, a golden) supports several
  claims, a refuter's overturn of one claim must not withhold that evidence from the sibling claims it upheld, and
  evidence the refuter never judged must never be recorded because its claim was upheld on something else. Key the
  integration on (claim, evidence); withhold evidence from EVERY claim only when the refuter says the evidence itself is
  invalid (for example, the test input is non-conforming). *Why: pooling overturns by claim silently dropped valid
  evidence and recorded unjudged evidence, and each lander had to hand-check every row.*

## 11. Measure cost per unit and route to the cheapest lane

- **Measure tokens per closed unit for each lane** (items closed per agent, cache-read per item) from the
  transcripts, and re-measure at each milestone. *Why: across lanes, cost per unit can differ by ~10×.*
- **Route each item to the cheapest lane that moves the metric you actually report.** For example, writing a
  witness test for already-correct behavior beats re-running a full review fleet. *Why: a large review fleet
  can burn billions of tokens for single-digit movement.*
- **Precompute discovery.** If most of a fleet's turns are spent searching, build a dossier once and hand it to
  every agent.
- **Self-review before a large review fleet.** *Why: a large share of what the fleet finds are defects that the
  same wave introduced.*

## 12. After a fleet, and on restart

**After any fleet that could touch the tree:** run `git status --short` and account for every unexpected path
**before** `git add -A`, or stage explicit paths. *Why: agents drop files into the repo root despite
scratch-only ground rules. The prompt constrains intent, not effects.*

**On restart after a cutoff:**
1. Read the reset time from the limit message. It is not a fixed hour.
2. Run `git status` on main. A dead lander may already have applied its patch, so finish from its NEXT step and
   never re-apply.
3. Run `git worktree list`, then check each worktree's dirty files and `STATUS.md` to see which agents are near
   done.
4. Dispatch **fresh** agents from the checkpoints, in landing order. Resume an agent in place (with its context
   intact) only if it is within a step of finishing. A workflow resumes from its run id, and completed stages
   replay from their on-disk outputs.

## Standards

The bar is the **engineering-standards** skill, and agents only meet the bar their brief states. So:

- **Every implementer brief carries the quality bar** (production quality, root cause, complete to spec, one
  mechanism, sibling sweep, docs current) and names the project's own rules. *Why: agents optimize against the
  criterion written down.*
- **Forbid the smallest-diff fix that contradicts the bar.** A brief's scope is an estimate; when the correct fix
  needs restructuring, the agent either does it or stops and reports the real size. It never ships a workaround
  to stay inside the estimate.
- **The report states what was swept** (the pattern and the search) and which invariants or drift tests were
  added, and each one was seen to fail once.
- **Refuters check the standards too:** a fix that papers over a symptom or leaves a sibling is overturned even
  when its tests pass.

## Brief template

`references/brief-template.md` is a copy-and-fill dispatch brief that already carries the checkpoint, STOP,
turn cap, blocking-gate and report rules. Point each agent at a rendered copy; don't paste it.
