# Landing finished work

The full text of agent-fleet section 6. Read it before scripting a wave, writing or running the enqueue step,
dispatching a finisher, running the comprehensive battery, or changing the CI workflow or the branch ruleset.

## The measurement this section is built from

The earlier pipeline had a **lander** agent merge 4–6 finished branches into a **train**, gate the whole test population
locally (and CI's other-OS legs locally too), then push under a **landing lease** and wait for CI. In one measured
campaign (2026-10-10) its 567 lander-minutes split like this:

- **41 % inside local whole-population gate runs**: 7–13 min each on a quiet host, 25–53 min under load, and 8 of 15
  runs RED, mostly from fixed time limits in tests that tripped under load;
- **16.5 % waiting for CI**, which had already run the same population on 20 free runners in 13 min;
- **10 landers for 6 trains** (turn caps, splits, a blocked push), and the first commit reached the default branch
  **6 h 49 min** after the day began;
- **review shards were 23 % of the landing tokens** and sat on the critical path between two gate runs;
- in the same day, a wave whose 18 implementer gates spent **246 of 294 gate-minutes on gates that ran no test leg** (a
  self-test pool timing out under its own load).

*(Validated 2026-10-11 (measurement); the redesign's effect is not yet measured.)*

The mechanisms, not the symptoms: **two gates for one population** (the host ran what CI runs, then waited for CI to run
it again); **load-sensitive checks inside the per-landing gate**; **a serial lease held through the CI wait**, which made
big trains rational, which made a red first run likely, after which every in-train fix re-gated every cluster; and **one
agent doing everything** (bring in, gate twice, review, fix, log, push, measure), so the cost law produced ten landers.

## The pipeline, in order

1. **Implement** in an isolated worktree. The implementer's gate is the **targeted** local leg (below); its report says
   `DONE`, and it writes its own **log entry file** without a number (the `devlog` skill).
2. **Review the branch the moment it is DONE**, inside the wave, by a read-only reviewer. A blocking finding goes back
   to a finisher; a branch reviewed CLEAN is enqueued at once, whether or not a successor follows it. The landing step
   never reviews and never fixes.
3. **Enqueue** — a deterministic SCRIPT, no agent: fetch; rebase the branch onto the default branch (a conflict stops it:
   the branch returns to waiting with the conflict named, and a finisher resolves it); run the targeted gate on the rebased
   head, on both hosts, under the shared gate-slot cap; stamp the log entry's number; run the landing checks (exactly one stamped entry,
   any file-set partition rule the project has); open the pull request (title = the branch's one-line subject, body = the
   forensic message); add it to the merge queue. Done: no lease, no local whole population, no waiting for CI.
   A file-set partition orders only INDEPENDENT work that touches the same file. In-flight work that DESCENDS from the
   landing branch (their merge-base lies beyond the default branch: a successor, a finisher or a carrier that merged
   some head of it) never blocks the landing, because it lands on top of it; and a worktree with no commit beyond the
   default branch blocks nothing. *Why: a successor that had merged an OLDER head of its predecessor "shared" six files
   with the predecessor's reviewed branch and stopped its landing three times, with both gates green; an empty finisher
   worktree in mid-merge did the same.* *(Validated 2026-10-18 on one campaign: those three stops; a self-test
   reproduces them with the rule switched off.)*
4. **The merge queue** builds a merge group (one or several queued pull requests on top of the default branch) and CI
   runs the **full matrix on the `merge_group` event**: every OS, every shard, the population check, the audits. One
   required check gates the queue. A red bounces only the pull request that caused it (the queue re-tests the rest); the
   loop reads the bounce (`gh pr view --json mergeQueueEntry,statusCheckRollup`), names the red in the branch's report and
   dispatches a **finisher**; the fixed branch is enqueued again.
5. **On the default branch** the merged commit is the tree the merge group tested. The `push` run keeps only a cheap
   record job; the `pull_request` run keeps only the cheap checks (audits, the log-entry and work-register checks), so
   twenty open pull requests do not queue eighty matrix jobs behind a public repository's concurrent-job limit.

## Local testing of the targeted change first; CI is the regression net

- **Every change's local gate is the targeted leg** — the change's own tests, the tests likely to go red for this diff,
  and the cases the diff reaches — for the implementer and the enqueue step alike. *Why: local runs are free and fast
  when narrow; the owner's rule was "local testing to confirm the targeted changes are correct; CI should primarily
  ensure no regression on the remaining codebase".* The `test-gate` skill says how to order and read it.
- **The targeted leg runs on BOTH hosts** the project supports: natively, then, under the same gate slot, the same
  targeted leg in a clone on the other OS (for a Windows host, a WSL clone), fail-fast native first. *Why both hosts: in the measured campaign 3 of 38 landed changes had reds only on the other OS, all in the changes' OWN tests (a locale golden whose text differs by OS, a lock-race fix red 10 of 10 on Linux, a path-length test), and each was caught by the other-OS run before a CI round trip. A targeted leg there costs the clone and build (about 1–2 min) plus the leg, not the 5–10 min of the whole legs.*
  *(Owner decision 2026-10-11; practice, not yet validated as a gate shape.)*
- **CI's merge-group run is the whole-population run, and the only one.** No local whole-population gate on either OS:
  running CI's FULL legs locally is what goes. *Why: the measurement above: the local copy cost 41 % of landing time and
  most of its reds were the host's load, not the change.* On a public repository the standard hosted runners are free;
  check your plan before assuming the same for a private one.
- **Keep the full other-OS legs as the tool that REPRODUCES a CI red** (the `cross-platform` skill), never as a gate.
- **Host-only witnesses stay local.** A test that reproduces only on the developer host — typically a filesystem property
  CI's runners lack (ReFS deletes differently from NTFS: a race reproduced locally in 20 of 7,200 probes may never
  reproduce on the runner) — carries a trait naming that property, and every test with the trait is in the targeted leg
  at every landing, whatever the diff. Membership is DERIVED from the trait, never listed, and a drift test asserts the
  witnesses carry it.
- **Audits are reused when their inputs are unchanged**, at every gate, and **no test carries a fixed time limit** (the
  top recurring red under load was a 120-second harness limit). See the `test-gate` skill.

## One pull request per finished branch, through a merge queue

- **One pull request per finished branch.** No trains. *Why: with a queue, a red bounces one branch while the others land;
  with a train, one red re-gated four.*
- **A ruleset on the protected branch** (classic branch protection has no merge queue): require a pull request; require
  the merge queue with merge method **merge commit**; the required check evaluated on the merge group; enforced for
  administrators (often the account that makes every push); a minimum group size of 1, a maximum of a handful, a check
  timeout about four times CI's wall. *Why merge commits, not squash: a squashed head is never an ancestor of the default
  branch, so every lifecycle tool that asks "is this branch landed?" (`git branch --merged`, `git cherry`, a prune script)
  would have to key on the merged-PR record instead. With merge commits the branch's commits stay ancestors, and
  `git log --first-parent` reads one merge commit per landing whose message is the forensic record.*
- **CI triggers:** the full matrix on `merge_group` and on manual dispatch; cheap checks on `pull_request`; a record run on
  `push` to the default branch. Keep one aggregate required job whose `needs:` lists every job, with a drift check that
  every job is wired into it.
- **A direct push to the protected branch is refused** by the ruleset and, for agents, by a guard hook
  (`automating-agent-guardrails`).
- **A bounce is a defect fixed on its branch before re-enqueue.** If the red was inside the targeted scope, the targeted
  gate missed it: find why (a missing leg, an unpinned tool, a setting CI has that the local run lacks) and fix that too.

## The enqueue step is a script; a finisher handles the exceptions

- **The landing step is deterministic**, so it costs no tokens and cannot drift. Dispatch an agent only for a rebase
  conflict or a queue bounce: a **finisher** (resolve the conflict or fix the red, re-run the targeted gate, re-enqueue).
  It is not a lander: it never assembles several branches, never runs the whole population, never reviews.
- **Concurrent enqueue gates share the gate-slot cap** that implementer gates use, so a burst of finished branches cannot
  saturate the host.
- **The orchestrator loop's landing unit becomes an enqueue unit**: for every waiting branch, in priority order, run the
  enqueue script; dispatch a finisher for each conflict or bounce; render the status view; hand off.

## Review the branch when it is DONE

A read-only reviewer runs the `review` skill's branch form over `<default>...HEAD` (correctness first, then the project's
drift rules, time limits in tests and a citation spot-check) as soon as the implementer returns DONE, inside the wave and
beside other implementers. A CONFIRMED blocking finding goes to a finisher, which fixes it at the root with a regression
test and a sibling sweep, or refutes it with evidence, and re-runs the targeted gate; the branch is then reviewed again,
for a fixed number of finisher rounds (two is a good default). A branch reviewed CLEAN is enqueued at once.
*Why: in the measured campaign the review sat on the critical path between two gate runs and cost 23 % of the landing
tokens; on the branch it runs in parallel, and the landing step stays a script.* *(Practice — not yet validated.)*

- **Finished work is never held.** A branch reviewed CLEAN lands at once, successor or not. There is no predecessor
  hold: a same-file successor merges its predecessor's REVIEWED head before its own review, and its pull request merges
  on top of the predecessor's. The landing order is communicated to the successor, never enforced by holding the
  predecessor back (`grouping-fixes.md`). *Why: the hold ("the predecessor lands through its successor") dates from
  trains; with one pull request per branch it only postponed. One six-link chain had six groups DONE over seven hours
  and none landed; one branch finished at 06:22 was held from 08:43 behind its successor, and another, finished at
  08:50, was reviewed only at 10:10, after its successor returned.* *(Validated 2026-10-18 on one campaign; the new
  rule's landing times are not yet measured.)*
- **Round 2 and later review only the diff.** Round 1 reviews the whole branch. A re-review reads ONLY the finisher's
  diff since the head the last round reviewed (`git diff <reviewed head>..HEAD`; when the finisher merged a newer
  default branch, only its own commits) and its answers to the last round's findings. The earlier content is reviewed
  and is not re-opened unless the diff touches it. *Why: three whole-branch rounds of one branch found 5, 2 and 1 NEW
  findings over 2.3 hours, each round re-reading content already reviewed, and the rounds never converged.*
  *(Validated 2026-10-18 on one campaign: that branch.)*
- **A severity threshold decides the verdict.** Every finding carries a severity (critical, high, medium, low, info),
  calibrated to what it does and never raised to make it block. Critical and high always block. Medium blocks while a
  finisher can still answer it, and becomes a lead at the round after the last finisher. Low and info never block. A
  finding with no severity, or an unknown one, blocks. Every finding stays recorded; each non-blocking one is a LEAD the
  reviewer writes into the branch's report and the wave returns, so the loop files it as a work item. Critical and high
  findings left at the cap keep the branch off the queue for its own next finisher. *Why: the round cap turned one LOW
  finding (a test theory's length class) into a decision for a human, and a finished branch did not land.*
  *(Validated 2026-10-18 on one campaign: that branch.)*
- **"Does this branch carry unanswered blocking findings?" has ONE source of truth: the findings file's last
  verdict.** One function reads it, and both the wave (deciding what a successor is told and whether to enqueue it) and
  the landing survey (deciding whether a branch waits) call that one function. Never read it from a report stamp: a
  finisher rewrites the branch's report for its own branch whatever it returns (BLOCKED, SPLIT, killed), so a hold read
  from the stamp released a successor at exactly the moment nobody had answered its predecessor's findings. A successor
  whose branch contains a head whose last verdict is FINDINGS is enqueued only after they are answered. *Why: deciding
  from the stamp, then from the result's head, each let a CLEAN successor carry its predecessor's unanswered findings to
  main in a reviewer's probe.* *(Validated 2026-10-18 on one campaign: two review rounds found it twice.)*

## The findings file's integrity rule

The findings file is the source of truth for a hold, so a damaged file must never read more permissively than the
whole file would have.

- **Find findings files by NAME only.** Discovery lists every file matching the naming pattern where the files live,
  plus every file a report stamp names, and never opens one to decide whether it is one. A filter that opens files drops
  exactly the damaged ones (a read denied, a byte-order mark from an editor) before the reader can hold them.
- **Any tear HOLDS every branch the file names**, until an operator repairs the file by hand. A tear is any content
  problem: no final newline, a line that is not JSON or not a record under the schema, bytes that are not UTF-8, a
  byte-order mark, a file with no record, a file that cannot be opened or read (gone, a directory in its place, a read
  denied), and a stamp naming a file that is missing. No verdict is read from a torn file, whatever its records say: the
  records before a tear can read CLEAN when the whole file reads FINDINGS (a FINDINGS record that lost only its
  newline, with the next record glued onto its line). The hold covers every branch the file names and every branch that
  contains a head it names; a file that names none holds the branches of the item its name binds it to.
- **Every writer refuses a torn file** before writing, naming the repair command, so nothing is ever glued onto a torn
  line. Only an operator runs the repair (it keeps a last record that only lost its newline, removes a byte-order mark
  and any other torn tail, and deletes a file left with no record); no wave, survey or reviewer does.
- **Nothing raises out of the survey or the lane.** The reader returns a torn reading (with the reason, file, line and
  byte offset) instead of an exception: an exception from one undecodable byte stops every landing.
- **One record schema**, shared by the writers and the reader: each record kind's required fields and their types.
  A writer refuses a record that fails it; the reader reads such a line as a tear; extra fields are allowed.
- **The command-line reader and the survey give one answer**: the CLI prints the same reading, torn included, and
  exits 0, so a caller reads the verdict from the reading, never from an exit code.
- **Prove it with a property test, not cases.** Take a sample findings file with several rounds and a non-ASCII
  character, cut it at every byte offset, alone and with a whole record glued after the cut, and assert that no cut
  reads more permissively than the whole: a cut inside a record reads TORN and holds; a cut at a record boundary reads
  exactly its records' verdict; the repaired bytes are accepted by every writer. Assert the strong form: "TORN or the
  whole records' verdict" passes a reader that drops a glued FINDINGS record. Add one case per discovery path (read
  denied, byte-order mark, empty file, directory, missing file) and one per schema mutation (each required field
  dropped, each given a wrong type).

*Why: the branch that introduced this rule took seven review rounds, the seventh CLEAN, and rounds 4 to 6 each found a
reading the previous fix had missed: one torn line dropped every hold in its file; then a torn line swallowed a whole
record and the prefix reader returned the CLEAN round before it; then discovery dropped a file it could not open, and
a record missing a field released the hold. After the second round on the same class the method changed from
case-by-case reasoning to the exhaustive property: against the round-4 reader it fails 2,519 of 3,453 cuts.*
*(Validated 2026-10-18 on one campaign: the property is red against each earlier reader and green against the final
one.)*

## The branch survey

A survey that gives every branch a lifecycle state (in flight, waiting for review, waiting to land, decision) reads
the review verdicts too.

- **A branch reviewed CLEAN at its tip keeps its own state, contained or not**: it is waiting to land, even when a
  successor's branch contains it.
- **A branch with no clean review at its tip that is contained in a reviewed or in-flight carrier** (one a finisher
  merged, an unfinished or unreviewed predecessor) is IN FLIGHT via that carrier: it lands through the carrier, and is
  neither a decision row nor a second review. Once the carrier lands, it reads landed and is deleted.
- **A branch waiting to land that carries another item's unanswered blocking findings** (its unlanded commits contain
  the head of a FINDINGS last verdict, or any head or name of a torn file) is IN FLIGHT, waiting on that item, until the
  findings are answered or that head is on the default branch. A finisher of the same item carries them on purpose and
  lands.

*Why: the survey's containment rule read a CLEAN predecessor inside its successor as in flight, so the landing step
would have held it even with the wave's hold gone; and reading an unreviewed predecessor as waiting for review sent a
second reviewer over content its successor's review already covered.* *(Validated 2026-10-18 on one campaign: self-test
cases for each arm.)*

## Conflict-free landing files: the tree holds sources, views are rendered

Two queued pull requests that both insert at the top of one file collide, and the second bounces; the queue is only as
parallel as the files are disjoint. A landing adds or edits files that are ITS OWN; anything derived is rendered on demand.

- **The log is one file per entry**, its number stamped at enqueue so number order is landing order; the descending view
  is rendered, never committed; a CI check asserts every landing adds exactly one stamped entry (the `devlog` skill).
- **Generated indexes leave the tree** (gitignored, rendered by their script on demand); CI's audits job fails when one no
  longer renders. A view DEFINITION (a saved query) is a source and stays.
- **Shared prose** (the live-state page, a plan's status section) is edited only by its own pull request, never inside a
  fix.
- **One line-ending format, LF, enforced** (the `cross-platform` skill): a Windows gate and a Linux gate must test the same
  bytes, and a workflow script with a carriage return may be refused as containing control characters.

## Measure per landing

Record, per pull request: DONE → enqueued → merged, the bounces and their causes, and CI's wall time. Summarize changes
landed per hour and minutes and tokens per landing, and compare against the measurement taken before the change. Judge the
pipeline by that comparison, not by the absence of complaints.

## Cutover

Each step of a pipeline change lands through the THEN-CURRENT pipeline. Applying the ruleset is an owner-attended step:
ask for an explicit go at that moment, because from then on the default branch accepts only queued pull requests.

## Kept from the earlier pipeline

- **Watch CI for every run that decides something** (every merge group and every push record). A red on the default
  branch is a blocking fix, landed alone. *(Validated 2026-09-28.)*
- **Run the comprehensive battery in its own detached worktree**, cut at a batch head (`git worktree add --detach <path>
  <sha>`), never in a checkout an enqueue step or an implementer builds in. *Why: the battery rebuilds mid-run, so on a
  shared checkout it once measured a half-finished edit, and nothing could land for its ~45 min; from the first worktree
  battery on, landings continued in parallel, slower while it shares the cores.* *(Validated 2026-09-28.)*
- **Fill a freed implementer slot in the same turn it frees**, from a standing queue of apply-ready contracts, by running
  the fix lane as a **rolling wave** (`references/rolling-wave.js`), never as a barrier. N workers pull groups from one
  queue, a slot refills the moment its agent returns, a reviewer checks each DONE branch, and each approved branch is
  enqueued. *Why: idle slots once held a fix lane under 15 % utilization for days.* *(Filling a freed slot in the same
  turn: validated 2026-09-28. The rolling-wave script: practice, not yet validated: no A/B against the barrier.)*
- **Implementers gate at low process priority**, inside the shared gate-slot cap. *(Practice — not yet validated.)*
- **Assert on conflict markers between staging and committing** at every checkpoint and every rebase (`checkpointing.md`).

## Retired on 2026-10-11, and why

- **The landing lease and the push-and-wait script**: the queue serializes; the lease was held 25–106 min per landing,
  mostly through CI.
- **Trains of 4–6 clusters**: rational only while each landing carried a large fixed cost; with a queue the fixed cost is a
  script run, and a red no longer re-gates its neighbours.
- **The lander's whole-suite local gate** (earlier rule: "the lander gates the WHOLE test suite, unfiltered", validated
  2026-09-28 against filtered gates): CI's merge-group run is that gate now, on runners that are not saturated.
- **Running CI's FULL other-OS legs locally before every push**: kept as the reproduction tool for a CI red, out of every
  gate. The TARGETED leg still runs on the other OS in every gate.
- **Fixing a review finding in the train**: review moved to the branch, before the enqueue step.
