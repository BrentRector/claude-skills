---
name: review
description: Reviews code for defects that survive an attempt to refute them. Use when asked for a code review, architecture review, performance review, or duplication/efficiency analysis of a diff, branch or PR, a whole-subsystem audit, or the read-only review of a finished branch before it lands. Every finding carries a concrete failure scenario and is adversarially verified, and every confirmed defect is swept for its siblings.
argument-hint: "[PR number/URL | branch | path | 'audit <subsystem>'] (optional, defaults to the local diff)"
---

# Review

**The result is a short list of defects that survived an honest attempt to refute them, each with a scenario that
reproduces it and a sweep for its siblings.** It is checked in the report: the `N candidates -> M survived` line,
a scenario per survivor, and the query and scope of every sweep. The four review dimensions (architecture, full
code review, performance, duplication and efficiency) say what to look for.

The premise: a plausible-but-wrong finding costs more than a missed one. It sends the author (or the next agent) to
rewrite working code, and it erodes trust in every later review. So this skill is built to *filter*, not to
generate volume. An empty review is a valid result.

Triage and calibration ideas from carlymr/carlys-claude-skills.

Detail lives in `references/`; each step says when to read which file.

## Step 1 - Establish the target

- No argument: local diff against the default branch (`git symbolic-ref refs/remotes/origin/HEAD`, never assume
  `main`), staged and unstaged. PR: `gh pr diff`, `gh pr view`. Branch or path: diff against the merge base.
  "Audit" / "be comprehensive" / a subsystem name: whole-source mode (see *Scale*).
- A PR that already carries a review: diff only the commits since, open with `Incremental review - changes since
  <timestamp>`, never re-raise an answered finding; no new commits, say so and stop.
- **Branch form** (a fleet's finished branch, before it is enqueued to land): ONE branch, ONE read-only reviewer, run
  when the implementer reports DONE, over `<default>...HEAD`. Write every confirmed finding to a findings file (its
  scenario, repro, code site and severity: critical, high, medium, low or info, calibrated, never raised to make it
  block) through the project's one writer, and compute the verdict from the file under the blocking severities the
  dispatch names (by default critical, high and medium; critical and high at the round after the last finisher; a
  finding with no or an unknown severity blocks). Each non-blocking finding is a LEAD: recorded, written into the
  branch's report, never dropped. Never edit the branch, and never edit or repair a findings file the writer refuses as
  torn: stop and say so. A finisher answers EACH blocking finding — fixed at the root with a regression test, or
  refuted with evidence written beside it — before the branch is enqueued. A RE-REVIEW reads ONLY the finisher's diff
  since the head the last round reviewed, plus its answers; the earlier content is reviewed and is not re-opened
  unless the diff touches it. The landing step never reviews and never fixes (the `merge-queue-landing` skill).

Empty diff → say so and stop.

Read `references/target-triage-calibration.md` before reviewing a PR that already carries a review, or a branch in
its branch form.

## Step 2 - Run the free checks first

Before spending judgment, run whatever the repo already mechanizes: the build, the linters/analyzers, the test
suite scoped to the change, and any invariant checkers (Semgrep rules, architecture tests, custom scripts named in
the project instructions). Anything a tool already catches needs no reviewer. And when the review later finds a
defect *class* a rule could catch, propose the rule, not only the instance.

## Step 3 - Triage: which dimensions apply

Skip dimensions that clearly cannot apply, and say which were skipped and why.

- Never skip Full code review, nor Duplication and efficiency for new files.

A genuinely trivial diff (typo, version bump, comment) gets a direct single-pass review with no agents and no
skeptic; state that a full review was not warranted.

Read `references/target-triage-calibration.md` (the triage table) before skipping Architecture, Performance or Duplication and efficiency.

## Step 4 - Calibrate: two independent axes

- Read CLAUDE.md/README first; an author's statement beats inference. Set scale and consequence independently; if
  unstated assume early users / standard, say so, and pass both axes to every agent.

Read `references/target-triage-calibration.md` before Step 4 for what each level changes.

## Step 5 - The four dimensions: one finder, or a fan-out the change pays for

What a review needs is all four dimensions applied by a reader of the surrounding code (a diff alone hides most
defects), and every candidate put to an independent skeptic (Step 6). How many agents that takes is a cost choice:

- **Each agent costs a full read of the change** and the code around it, in a context of its own, and returns only
  its summary. What it buys is a fresh context on one lens (more depth there, no anchoring on the other finders) and
  parallel wall time. A specialist adds the same cost for its one defect class.
- **An ordinary diff** (one subsystem, up to a few hundred lines, standard consequence): ONE finder takes all four
  dimensions, the session itself or one agent when the session's context should stay clean, and applies the
  checks of each specialist whose trigger matches (the specialist files are its checklists). Then ONE skeptic for
  all the candidates: two agents at most.
- **A large, cross-subsystem or high-consequence change**: one finder per selected dimension plus each specialist
  agent whose trigger matches, launched in one message so they run concurrently, then one skeptic. Add an agent
  where its lens is likely to find what one finder would miss, never for completeness.
- **An audit**: *Scale*.

Brief every finder, inline or delegated, with the diff (or subsystem), the changed-file list, the PR description,
the calibration, the project review rules (*Project hooks*) and its criteria. Two criteria every finder carries: a
fixed time limit in a test is a finding, and a performance finding names an input size. A change to I/O, storage,
sorting or concurrency code whose tests miss a failure path it can reach (a status it can return, a refused write
or sync, a crash point, contention) is a finding.

Read `references/dimensions.md` before Step 5: it holds each dimension's criteria and when each specialist applies.

### What every finding must carry

```
[SEVERITY] path/to/file.ext:L<start>-L<end> - <title>
Scenario: <inputs / state>  ->  <actual wrong result>  (expected: <correct result>)
Why: <the mechanism, pointing at the exact line>
Fix: <approach, and whether it is local or structural>
```

No scenario, no finding. "This could be cleaner" or "consider X" is a style opinion, not a defect; drop it unless
the calibration explicitly asks for suggestions. For duplication, the scenario is the divergence: *change rule R in
place A, and path B still does the old thing.*

## Step 6 - Adversarial verification

- Agent output is candidates: a skeptic tries to REFUTE each one, running the scenario when cheap. For a diff that is
  ONE skeptic agent for all the candidates; an audit gets 3-5 per finding (*Scale*). Uncertain means refuted; only
  survivors are reported; a null result is valid.
- Then de-duplicate, apply the calibration, rank critical, high, medium, low, info (the scale is in
  `references/report-and-scale.md`).

Read `references/verification-and-siblings.md` before spawning the Step 6 skeptics.

## Step 7 - Sweep for siblings

- For each survivor search the other arm of the same dispatch, the paired function, the copied neighbor, the same
  idiom elsewhere; report siblings under the parent and say how the sweep was done.
- The sweep's method is the `variant-analysis` skill; in C#, `roslyn-analysis`' `sweep-symbol.cs` lists every
  implementation, override and reference of the finding's symbol, and its output is the finding's evidence.
- When the change under review is itself a fix, two of its claims are checked, not taken on trust. A claimed sweep
  is a table (the structural or semantic query, what it matched and how each match was settled, and a calibration
  line showing the query hit the origin), never a sentence such as "swept, no others"; a sweep with no table, with
  no calibration line, or with no structural or semantic row where the mechanism has a symbol or a dispatch (the
  `variant-analysis` sweep table) is a finding. Each new test or witness was seen to fail against the defect or a mutation of it; one never seen red is
  a finding. *Why: a sibling arm left wrong is the largest class of defect a landed fix leaves behind, and sweeps
  recorded as a sentence or a textual grep missed renamed and escaped forms; a test that does not exercise its rule
  passes on a wrong implementation, the most common reason a first-pass verdict was overturned.*

Read `references/verification-and-siblings.md` before the Step 7 sweep.

## Step 8 - Report

- Nothing survives: say so plainly. Offer to file survivors in the project's tracker.
- Posting is confirm-first: ask before posting to a PR; never approve or request changes unless asked.

Read `references/report-and-scale.md` before writing the Step 8 report and before posting to a PR.

## Scale

- An ordinary diff: one finder for the four dimensions and one skeptic. A large or high-stakes change: up to four
  dimension finders, the specialists whose triggers match and one skeptic, at most nine agents. An audit: several
  finders per dimension, 3-5 skeptics per finding and a completeness critic, because a missed defect in a whole
  subsystem costs more than the fleet.

Read `references/report-and-scale.md` before an audit-sized run.

## Standards

Read `references/standards-and-hooks.md` before Step 2 when the repo carries engineering standards.

## Project hooks

A repository adds a `## Review rules` section to CLAUDE.md (or `.claude/review.md`): honor its extra dimensions,
banned rules, mechanical checks and tracker.

Read `references/standards-and-hooks.md` before Step 2 to read the repo's `Review rules` section.
