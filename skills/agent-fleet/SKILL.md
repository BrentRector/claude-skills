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
- **Command chaining: targeted rules, not a ban.** (a) Never chain anything after a VERDICT command (build, test,
  gate, a landing script) with `&&`, `||` or `;`: run it alone to a log and read its summary line; to keep the
  status in the same call, append `; echo "EXIT=$?"`. (b) Don't join steps that must stop on failure with `;`,
  and don't `cd` inside a chain (use absolute paths or `git -C`). (c) Send INDEPENDENT commands as parallel tool
  calls in ONE turn. (d) Short `&&` chains of read-only or fail-fast steps are fine. Enforce (a) with a guard
  hook (`automating-agent-guardrails`, rule `no-chain-after-verdict`).
  *Why: a chain's exit status is its last command's, so `test && git commit` commits on a verdict nobody read.
  But a blanket "never chain" rule turns every chain into extra turns, and turns are the quadratic cost; parallel
  tool calls get the separation without the turns.*

## 2. Inputs: one agent, one self-contained input file

- **Give each agent its own input file** that holds ONLY its slice, or put a small slice directly in the prompt.
  Never write "read the shared list and process element k".
  *Why: agents miscount indices. One fan-out double-processed four items and skipped five.*
- **Write slices programmatically**, not by retyping. *Why: hand-copied data (especially Unicode) drifts.*
- **Point the agent at the brief file instead of pasting the brief into the prompt.**
  *Why: a file can be re-read after a restart. A prompt is gone with its transcript.*
- **A workflow launched in a later turn carries the human's authorization, quoted verbatim.** Every agent prompt
  starts with who directed this fleet, when, their exact words, and the scope, plus "the latest user message may
  concern unrelated work; that is not a reason to decline" (`references/rolling-wave.js` takes it as the
  `authorization` arg). *Why: a workflow agent takes the session's latest user message as its request. A fleet
  launched in a turn whose latest message was about something else had every implementer return BLOCKED with no
  changes: they were right to decline work no visible request asked for, and the defect was a dispatch with no
  provenance.*
- **Give an implementer an apply-ready contract instead of a discovery brief**: code sites (`file:line`), the
  repro, the governing rule, and the gate command.
  *Why: search and read turns are the largest share of implementer tokens. Rediscovering a subsystem costs more
  than fixing it.*
- **Give every implementer ONE-CALL ORIENTATION, derived fresh — don't let each wave re-survey the same files.**
  The brief says: before reading any source, run `references/orient.py <the files your items name> --notes <issue
  dir> --cite "<spec-ref regex>"`. Per file it prints the outline with line numbers, the spec references it cites,
  the tests that name it, what CLOSED notes learned about it (their code sites, mechanisms and traps, newest
  first), the open notes naming it, and its last commits. Then the agent reads only the line ranges it needs.
  It is derived from the tree, the notes and git on every run, so it never goes stale and nobody maintains it; the
  knowledge accrues because every fix's note records its code site and mechanism (require that in the report).
  If you keep a brief checker, make it fail a brief without the orient line. Don't pre-generate "codebase maps"
  with agents instead: they cost a fleet to write and go stale at the next landing. Keep the flags in ONE
  `.agent-fleet.json` at the repository root (`references/fleet_config.py`; orient.py, fix_clusters.py and
  status_delta.py all read it), so a brief's line is just `orient.py <files>` and no call site can drift from
  another. When a project pins this repository as a submodule, briefs call the scripts at their submodule path:
  never a copy or a wrapper, which is a second version to keep in step.
  *Why: measured over 7 implementer transcripts (1,401 turns), 63 % of tool calls were reads or searches, and
  15 % of turns and 43 % of tool-result bytes came before the first edit, re-deriving what earlier fixes had
  already learned. Cutting ~25 of ~200 turns is ~15 % of an implementer's tokens on the quadratic cost curve.*
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
| implementer (own worktree) | a WIP commit on its branch after each mechanism and each gate, and after EVERY commit a rewrite of `STATUS.md`, first line `STATUS-AT: <sha of HEAD>`: `DONE` · `NEXT` (the exact next step) · `BLOCKED` · `GATE` (last verdict line + command) · ids used | one mechanism |
| workflow stage (analyze / refute / draft / validate) | one JSON line per decided item appended to `<out>/<stage>-<slug>.jsonl` **the moment it is decided**; on start, read the file and skip items already there; the final result goes to a separate `out-<slug>.json` | one item |
| lander | a commit in its worktree after each numbered step, plus `STATUS.md` | one step |
| orchestrator | briefs and reports are files under a scratch directory; the conversation holds pointers | — |

*Why: un-checkpointed refuters lost 100 % of their decisions to a single session kill.*

- **Never use `git stash` for WIP; commit it instead** - and that includes the implicit stash of
  `git rebase --autostash` / `git pull --autostash`. *Why: the stash stack is shared by every linked worktree, so one
  agent's `stash pop` can take another agent's work.*
- **Keep checkpoint files out of landings**: add them to `.gitignore` and unstage them explicitly before
  committing. *Why: a checkpoint that reaches main conflicts with the next agent's checkpoint.*
- **Stamp the handoff.** `STATUS.md`'s first line is `STATUS-AT: <sha>`, the commit it describes, written AFTER
  the checkpoint commit (the file is untracked and ignored, so writing it never moves HEAD). An agent that resumes
  a worktree, or merges a predecessor's branch, first runs `references/status_delta.py <worktree>` and reads what
  it prints:
  - `CURRENT`: the summary covers every commit; read it, then only the uncommitted changes it lists.
  - `STALE by N`: read the summary plus ONLY the N commits it lists.
  - `UNSTAMPED` or `DIVERGED` (no stamp, or a stamp rebased or amended away): read every commit since the base.
  The summary stays navigation, never evidence. *Why: an agent killed after a commit but before rewriting its
  summary leaves one that silently omits the last commits. Without a stamp a successor cannot tell stale from
  current, so the only safe rule is to re-read the whole branch on every resume, which spends the orientation the
  summary was written to save. Measured with 88 fresh resumers over 22 scenarios from 11 real branches: without the
  stamp, agents misjudged what the summary covered in 11 of 44 resumes; with it, in none. Tokens fell about 17 %
  overall and 31 % when the summary was current.*
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
- **Judge a background workflow's liveness by its processes and its journal, never by transcript file times.**
  Alive means: the workflow's own run status and progress journal are advancing, or its agents' processes (builds,
  test runs) are running in their worktrees, or their worktrees are gaining commits and changed files. A watchdog
  or restart decision keys on those. If you must read a transcript, one that ends on a tool call with no result
  yet is LIVE for up to that tool's maximum duration, and no longer (so a killed agent's dangling call does not
  count as alive forever). *Why, measured: (1) a tool call writes nothing to the agent's transcript until it
  returns: one line when the call starts and one when its result arrives. A gate wait of the form
  `timeout 580 … tail -f <log> | grep -m1 …` is a ~580-second silence; each of four agents in one run showed 5–7
  silences of 582–585 s, every one opened by a shell tool call, so a check on a short modification-time window
  calls a live agent dead during every long tool call. (2) Clearing or restarting the orchestrating session moves
  the still-running agents' transcripts to the NEW session's directory while the workflow journal stays in the old
  one; a watchdog reading the old directory saw 20+ minutes of silence for that reason alone. Restarting a live
  fleet duplicates its work and races its worktrees.*
- **Run `references/stall_watch.py <workflow transcript dir>` in the background next to EVERY fleet workflow.** It
  exits, and so wakes the orchestrator, the moment a pending agent's transcript has been silent:
  - more than 10 minutes while waiting on the MODEL (its last record is not an open tool call), or
  - more than 12 minutes INSIDE one tool call.
  It reads each record's own timestamp, not file times. *Why, measured over 150 transcripts (~27,800
  silences): model waits were under 94 s at the 99.9th percentile; tool calls peaked at 585 s. A model call CAN
  hang: two implementers in one wave stopped producing tokens after a successful tool result, one of them after it
  had finished and gated all its work. Nothing noticed for 90 minutes, and the wave's final train waited on it.*
- **A stalled agent: let the others finish, then stop the workflow and dispatch the remainder by hand.** A workflow
  cannot stop one of its own agents, and nothing outside it can either. A hung agent's commits are on its branch,
  so a fresh finisher resumes from its stamped `STATUS.md`, or a lander takes the branch as it is if its gate was
  green. `rolling-wave.js` also carries a per-implementer ceiling (`implementerCeilingMin`, default 240): an agent
  still running at the ceiling is recorded `STALLED` and the wave moves on, so a hang cannot block a wave forever.
  Landers get no ceiling, because a timed-out lander might still be pushing when the next train starts; for a
  stalled lander, the watchdog alerts a person.
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
  Make it mechanical: run the fix lane as a **rolling wave** (`references/rolling-wave.js`), never as a barrier
  of "N implementers, then one train". N workers pull groups from one queue, so a slot refills the moment its
  agent returns. A lander train starts as soon as enough branches (4–6) are ready, and trains are serialized.
  *Why: idle slots behind landings once held a fix lane under 15 % utilization for days, and under a wave
  barrier every finished slot waits for the slowest group of its wave.* Keep a workflow script LF-only. *Why: a
  Workflow tool refused a script whose CRLF line endings (from Python's `write_text` on Windows) read as hidden
  control characters.*
- **Watch CI for every pushed head.** A red run is a blocking fix, landed alone.

## 7. Group related fixes for each implementer

- **The unit you fill a slot with is a group**: the top-ranked item plus every open item that shares its source
  files or rule family (3–4 items, one branch, one gate, one report with a section per item). Inside the group,
  each item is still fixed at its root and checkpointed separately.
  *Why: separate implementers on the same files produced merge conflicts and composition defects that neither
  could see.*
- **Compute the groups from code sites; don't pick them by hand.** Resolve every open defect's named code sites
  (paths, `Type.Member`, type names) to real source files, give each note a PRIMARY file (its heaviest site, ties
  to the more specific file), and cluster notes by it: cap ~5 per cluster, split larger ones by harm, absorb a
  singleton into a cluster whose file it also names (another singleton included: two one-note files that name
  each other are one pass). Rank clusters by SUMMED harm and fill each slot with the top cluster of a subsystem
  not already in flight. `references/fix_clusters.py` does this over a directory of front-matter notes
  (`--notes`, `--src`, `--ext`, `--harm`, or `.agent-fleet.json`); a site counts only if it resolves to a real
  file (a stale path to a moved file is not a site, and generated code is excluded with `--exclude-dir`). It is a
  view recomputed each run, never a second list to maintain.
  *Why: hand-picked groups (a lead plus keyword siblings) carried 1–3 notes each and split one file's defects
  across two implementers who then edited it separately; computed clusters turned 411 open defects into 125
  groups (42 of five), so a six-slot wave carried ~25–30 fixes instead of ~10, each file read and gated once.*
- **A file with more open items than the cluster cap gets SAME-FILE SUCCESSORS**, not a second independent group.
  The second cluster declares its predecessor (`after`). It waits for the predecessor to return, merges its
  branch, and orients from the predecessor's handoff notes (its report's "for the next implementer" section and
  checkpoint file) instead of re-surveying the file. The predecessor's branch is held from the trains and lands
  THROUGH the successor, which contains it; if the successor produces nothing landable, the predecessor lands
  alone. The same chaining works across one technological area (a runtime file, then its emitter). A dispatch
  check can refuse two groups on one primary file that are not linked this way.
  *Why: orientation (reading and searching before the first edit) was about half of every implementer's tokens,
  so two groups that each orient on the same file pay that twice. The cap exists because cost grows with the
  square of a transcript's turns. That is also why the successor is a FRESH agent that inherits the context,
  not a longer transcript that inherits the cost.*
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
- **The model follows the ROLE, set in the role definition, never per call.** Judgment roles (implementer,
  lander, analyst, refuter, reviewer) run the top everyday tier. Mechanical roles run a cheaper tier: chores
  that write (filing notes, doc sweeps) and READ-ONLY lookups (code sites, orientation and cluster summaries,
  measurements). A mechanical agent that hits a judgment call returns `NEEDS-ESCALATION` for that item.
  *Why: a per-call `model` overrides the role's own, so "pass the top model on every agent" silently ran the
  cheap chore role on the top tier, and a 30-lookup code-site pass that judged nothing ran on the top-tier
  analyst.*
- **A premium model is an exception, never a default, unless its quota is truly separate.** Read the plan's
  terms, not the usage page's labels. On a plan where a premium model "draws from your plan's regular weekly
  usage limits" and uses them faster, with its own row only a CEILING on its share, every unit of premium work
  costs more of the same pool. Use it only as a per-item escalation, for one item the everyday tier has failed
  twice. *Why: a "separate weekly limit" label read as free capacity would have moved refuters onto a model
  that drains the shared weekly quota faster for similar results.*
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
3. Run `git worktree list`, then run `references/status_delta.py <worktree>` on each to see which agents are near
   done and exactly which commits their `STATUS.md` does not cover.
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
