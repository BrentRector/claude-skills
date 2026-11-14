# Flakes, CI after the push, standards, project hooks

## Flakes and attribution

- **Never call something a flake without naming the test and the cause.** Get the name, run it on its own
  (serially if the suite runs in parallel), and then decide. A flake verdict needs a clean isolated re-run of
  **that** test. The fact that other suites passed is not evidence.
- **Attribute every red before calling it yours, and before calling it someone else's.** Check it against the
  commit the batch started from (a detached worktree at the base, `git worktree add --detach <path> <base>`;
  `git log -S "<symbol or message>"`). A
  red that was already there before your batch **still blocks the merge**. Attribute it honestly and file it.
  Don't step around it.

## After the push or enqueue: CI is the final authority

Local green is evidence about one host, one OS and one build configuration. CI runs a clean checkout, often
other operating systems and a Release build. Tests that depend on file locks, ACLs, path separators, locale or
timing can pass locally and fail there.

- **Under a merge queue**, the deciding run is the one on the merge group. Read the pull request's queue state and
  checks: `gh pr view <n> --json mergeQueueEntry,statusCheckRollup,state`. A red bounces only that pull request (the
  queue re-tests the rest). Before changing anything, classify it against the branch's gate record: the merged tree
  (a merge red), another OS, another configuration, the runner or infrastructure, a flake, or a case the local gate
  should have run. A red the branch caused is fixed on its branch before re-enqueue; a red in a case the local gate
  ran green, or should have run, is also a defect of the local gate: find why (a missing leg, an unpinned tool, a
  setting CI has and the local run lacks) and fix that in the same change. A red the branch did not cause is the
  next section's.
- **Otherwise**, read the run for **the exact commit you pushed**:
  `gh run list --commit <sha> --json databaseId,status,conclusion` → `gh run watch <id> --exit-status`, and
  `gh run view <id> --log-failed` on a red run.
- **Reproduce a CI red locally before fixing it**, on the OS that failed (a clone built there:
  `cross-platform`'s `references/platform-facts.md`), then fix it at the root.
- A status lookup that FAILS (an API timeout, an empty or unknown conclusion) is **no verdict**: retry it, and report
  it as its own outcome - never as red, never as green. *Why: a push script read a transient TLS timeout as an empty
  conclusion and reported "CI is red" on a green run.*
- A red CI run on the default branch blocks further work. Attribute it by job, step and test, and land the fix on
  its own before the next change.

## A red the branch did not cause: root-fix first, re-run at most once

- **The fix goes first.** A red that main carries, or a flake in a test the branch does not reach, is root-fixed at
  once as its own change, and the fix reaches the build ahead of the work queued behind it: hold or dequeue the
  queued changes the red will hit, stop enqueueing more, land the fix first (a merge queue's jump to the front,
  where the queue and the project allow it), then re-land what was held. Re-queueing the bounced change and
  waiting for main to move is not a fix. *Why: every landing behind the red meets it. In one project one test's
  flake went through three re-queues and 18 merge groups before its fix reached main, 13 hours after the first red.*
- **A second re-run of one cause is refused.** A red with no observation (a killed runner, an infrastructure
  failure) may be re-run once. A second red of the same case, on any branch, is a defect of the test or of the
  pipeline: file it with the case name, the runs and its rate, and fix it at its root before anything re-runs it.
  Count re-runs per CASE, not per branch: two branches each re-queued once on the same flaky test is the second
  re-run. *Why: re-running in place of a root fix cost about one extra local gate per landing in one project, and
  three of its five repeating runner reds were never filed because each branch saw only its own.*
- **A retry loop in a test is the same failure in code.** A test that retries until it passes keeps the cause and
  hides its rate; one such retry, added for a file race, cost a whole red gate three months later.

## Re-run only what changed

A gate does not re-run a test whose inputs are unchanged since its last recorded pass. Key each target's pass by
everything it reads (its sources and data files, the build, the toolchain, the configuration), and at the next gate
report a target whose key is unchanged as reused, naming the record, instead of running it. Before any re-gate, a
re-run or a wait, ask what it can show that is not already known: a re-gate at an unchanged tree, a full gate after
a commit no test reads, and a gate on a branch that must merge main again before it lands each show nothing. A key
that misses an input is a false green; when in doubt about an input, it is in the key. *Why: one non-observed case
once cost a 58-minute re-run of every passed case at the same tree.*
- If behaviour can differ between Debug and Release, run a local Release leg before pushing. Better still,
  don't write code whose behaviour depends on the build configuration.

## CI and the local gate are different builds: survey them, pin them, map every job

A red in a case the local gate ran green is a difference between the two builds, and each such difference is the
next CI-only red until it is settled.

- **Survey the differences once and settle each one** as identical, reproduced locally, or irreducible with its
  reason recorded: runner image, SDK, JDK and shell patch versions, Debug against Release, locale and time zone,
  compile caches, shard composition, the files a job's checkout contains, and jobs or audits with no local
  counterpart. The operating-system facts among them (pinning the image, a tool's default charset) are the
  `cross-platform` skill's.
- **Map every CI job to a local leg, or to a recorded reason it cannot run locally,** with a drift test seen to fail
  once on a planted gap. Derive what a job reads by running it and tracing the files it opens, not by parsing its
  imports: a drift test that checked a sparse checkout's imports passed while a job read a data file the checkout
  did not contain. *Why: two finished changes were dropped from landings in one day for failures only CI could see
  (a charset, and a guard job that ran only on CI), each a ~30-minute round trip.*

## Standards

At the gate the bar means:

- A red is fixed at its root cause. Never weaken an assertion, widen a tolerance, add a skip, re-baseline an
  expected value, or edit valid input to make it pass.
- Never scope a test to the bug. Tests verify the complete behavior the spec or design requires; a test that
  covers only the reproduced case leaves the siblings (and the other arm of the dispatch) unguarded.
- A green test that pins wrong behavior is a defect, not a decision. Check rejections and "fails loud" tests
  against the authority.
- Expected values come from the authority, not from copying the current output.
- Every new guard or drift test is seen to fail once, for the right reason, before its green counts.

## Project hooks

This skill is generic. The commands belong to the repository. Look for them, and record them if they're
missing, in the project's `CLAUDE.md` under a **"Testing"** section (or `CONTRIBUTING.md`, or the CI workflow
file):

- the build command (which solution or workspace) and each tier's exact test commands
- the **baseline counts** for each suite (total / passed / skipped), so a vanished population can be seen
- which legs are slow, which ones rebuild, and which have to run alone
- a wrapper script, if one exists, that expands filter shorthand and fails on a missing verdict line; prefer it
  over raw commands
- which CI check is required on the default branch, whether a merge queue gates it, and how pushes or queued
  pull requests are verified against it
- which tests are host-only witnesses (the trait), and which audits are reused when their inputs are unchanged
- where the gate record lives (which target passed at which inputs) and where reds are recorded per test case, so
  "reused" and "second re-run of one cause" can be checked rather than remembered
