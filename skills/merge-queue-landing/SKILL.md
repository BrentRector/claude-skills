---
name: merge-queue-landing
description: Use when landing finished branches through a merge queue - writing or running the enqueue step, reading a branch's gate record before it lands, reviewing a branch before it is enqueued, sending a merge conflict or a merge-queue bounce to a finisher, keeping landing files conflict-free, or changing the CI triggers or branch ruleset behind the queue. Applies to any change landed through a queue, with or without an agent fleet.
---

# Merge-queue landing

**Every finished branch reaches the default branch as its own pull request through a merge queue, with no agent in
the landing step and nothing finished left waiting.** Check it per landing: the times from DONE to enqueued to
merged, every bounce with its class and cause, and no branch reviewed CLEAN left unenqueued, compared with the
measurement taken before the pipeline last changed.

## The pipeline, in order

1. **Implement and gate** in an isolated worktree. The gate runs at the branch head as the `test-gate` skill says and
   leaves a record naming that head. The branch writes its own log entry file without a number (the `devlog` skill).
2. **Review the branch the moment it is DONE**, with a read-only reviewer (below). A blocking finding goes to a
   finisher; a branch reviewed CLEAN goes to the enqueue step at once.
3. **Enqueue**, a deterministic script: fetch; refuse a head no green gate record covers; merge the default branch in
   (a conflict stops it, names the conflict, and the branch waits for a finisher); stamp the log entry's number; run
   the landing checks; open the pull request (title = the branch's one-line subject, body = the forensic message); add
   it to the queue. It runs no gate and waits for no CI: the merge group is the first run of the merged tree.
4. **The merge queue** runs the full CI matrix on the merge group, gated by one required check. A red bounces only the
   pull request that caused it; the bounce is handled as below, and the fixed branch is enqueued again.
5. **On the default branch**, the merged commit is the tree the merge group tested.

## The landing step is a script

The enqueue step decides nothing that needs judgment, so it costs no tokens and cannot drift. An agent enters only
for an exception: a **finisher**, one branch per agent, for a merge conflict, a queue bounce or a reviewer's confirmed
findings. It fixes the cause at the root, gates the new head (the `test-gate` skill), and the branch is enqueued
again. A finisher never assembles several branches, never runs the whole population and never reviews; the landing
step never reviews and never fixes.

## Classify every bounce before anything changes

Read the bounce from the queue (`gh pr view --json mergeQueueEntry,statusCheckRollup`), compare the red with the
branch's gate record, and name its class in the branch's report:

| Class | What it is | What happens |
|---|---|---|
| INFRA or RUNNER | the runner, the network or a service failed; the tree did not | a red the branch did not cause: the branch is held for that cause's root fix, not re-run (below) |
| MERGE | the branch is green at its head and red only merged with the queue's other changes | a finisher fixes it on the branch |
| GENUINE | the branch's own red | a finisher fixes it at the root; when the gate record covered the case green, also find why the gate missed it (a missing case, an unpinned tool, a setting CI has that the local run lacks) and fix that |
| FLAKE | one case fails and passes at one tree | a defect filed with its rate and fixed at its root, never retried inside the run |

A red the branch did not cause (a runner or infrastructure failure, or a red the default branch carries into every
merge group) is held for its root fix: the branch waits, the fix lands at the front of the queue, and the held
branches are enqueued again after it, because every branch queued behind the red meets it too. The rule for that red
itself (root-fixed first, a second re-run of the same failing case refused) is the `test-gate` skill's; this skill
only classifies the bounce and holds or re-enqueues the branch. Cancel merge-group runs a re-enqueue superseded, or
they hold runners.

## Review before landing

A read-only reviewer runs the `review` skill's branch form over `<default>...HEAD` as soon as the branch is DONE,
beside other work, for a fixed number of finisher rounds (two is a good default).

- **Round 1 reviews the whole branch; every later round reads ONLY the finisher's diff** since the head the last round
  reviewed (`git diff <reviewed head>..HEAD`; when the finisher merged a newer default branch, only its own commits)
  and its answers to the last findings. Whole-branch re-reviews re-read reviewed content and do not converge.
- **A severity threshold decides the verdict.** Every finding carries a severity (critical, high, medium, low, info),
  calibrated to what it does. Critical and high always block. Medium blocks while a finisher can still answer it, and
  at the round after the last finisher it becomes a lead. Low and info never block. A finding with no severity, or an
  unknown one, blocks. Every non-blocking finding is recorded as a LEAD for the work register.
- **Finished work is never held.** A branch reviewed CLEAN is enqueued at once, whether or not a successor follows it.
  A same-file successor merges its predecessor's REVIEWED head (the finisher's, when one ran), and its pull request
  merges on top. The landing order is told to the successor, never enforced by holding the predecessor back.
- **"Does this branch carry unanswered blocking findings?" has ONE source of truth: the findings file's last
  verdict**, read by one function that the wave and the landing survey both call, never from a report stamp (a
  finisher rewrites the report whatever it returns). A successor that contains a head whose last verdict is FINDINGS
  is enqueued only after they are answered. A damaged findings file never reads more permissively than the whole file
  would have: a tear holds every branch the file names and every branch containing a head it names, until a person
  repairs it, and the reader is proven by a test that cuts the file at every byte offset.

## Keep landing files conflict-free

The queue is only as parallel as the files are disjoint: two queued pull requests that insert at the top of one file
collide. A landing adds or edits files that are its own; anything derived is rendered on demand. The log is one file
per entry, numbered at enqueue (the `devlog` skill); generated indexes leave the tree; shared prose is edited only by
its own pull request; one line-ending format, LF (the `cross-platform` skill).

## CI and the ruleset

Watch every CI run that decides something; a red on the default branch is a blocking fix, landed alone. The protected
branch carries a ruleset: pull requests and the merge queue required, merge method **merge commit** (so a landed
branch's commits stay ancestors), the required check evaluated on the merge group, enforced for administrators. A
direct push is refused by the ruleset and, for agents, by a guard hook (`automating-agent-guardrails`). **Applying
the ruleset is an owner-attended step**: ask for an explicit go at that moment, because from then on the default
branch accepts only queued pull requests. Each step of a pipeline change lands through the pipeline current at that
step.

In an agent fleet, the fix lane fills a freed slot the moment its agent returns and enqueues each approved branch as
it finishes: the rolling wave, `agent-fleet/references/rolling-wave.js`.

Read `references/landing.md` before writing the enqueue script, the findings reader or the branch survey, or before
changing the CI triggers or the ruleset.
