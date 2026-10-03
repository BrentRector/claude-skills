---
name: review
description: Use when asked for a code review, architecture review, performance review, or duplication/efficiency analysis of a diff, branch or PR (or a whole subsystem audit) - runs the four review dimensions (architecture, full code review, performance, duplication and efficiency) as parallel agents, requires a concrete failure scenario for every finding, adversarially verifies each finding before reporting it, and sweeps every confirmed defect for its siblings.
argument-hint: "[PR number/URL | branch | path | 'audit <subsystem>'] (optional, defaults to the local diff)"
---

# Review

Four independent review dimensions, run in parallel, followed by an adversarial verification pass that tries to
kill every finding before it reaches the author. The output is a short list of defects that survived an honest
attempt to refute them, each with a scenario that reproduces it.

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

Empty diff → say so and stop.

Read `references/target-triage-calibration.md` before reviewing a PR that already carries a review.

## Step 2 - Run the free checks first

Before spending judgment, run whatever the repo already mechanizes: the build, the linters/analyzers, the test
suite scoped to the change, and any invariant checkers (Semgrep rules, architecture tests, custom scripts named in
the project instructions). Anything a tool already catches needs no reviewer. And when the review later finds a
defect *class* a rule could catch, propose the rule, not only the instance.

## Step 3 - Triage: which dimensions apply

Skip dimensions that clearly cannot apply, and say which were skipped and why.

- Never skip Full code review, nor Duplication and efficiency for new files.

A genuinely trivial diff (typo, version bump, comment) gets a direct single-pass review with no agents; state that
a full review was not warranted.

Read `references/target-triage-calibration.md` (the triage table) before skipping Architecture, Performance or Duplication and efficiency.

## Step 4 - Calibrate: two independent axes

- Read CLAUDE.md/README first; an author's statement beats inference. Set scale and consequence independently; if
  unstated assume early users / standard, say so, and pass both axes to every agent.

Read `references/target-triage-calibration.md` before Step 4 for what each level changes.

## Step 5 - The four dimensions, as parallel agents

Launch one agent per selected dimension **in a single message** so they run concurrently. Give each the diff (or
subsystem), the changed-file list, the PR description, the calibration, any project review rules (see *Project
hooks*), and its criteria below. Each agent reads surrounding code as needed - a diff alone hides most defects.

- The four dimensions are Architecture, Full code review, Performance, Duplication and efficiency.
- Specialist agents (`silent-failure-hunter`, `pr-test-analyzer`, `type-design-analyzer`, `comment-analyzer`) launch
  in the same message when the change matches and go through the same Step 6 skeptic.
- A fixed time limit in a test is a finding; a performance finding names an input size.

Read `references/dimensions.md` before launching the Step 5 agents: it holds the criteria to hand each agent and when each specialist applies.

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

- Agent output is candidates: spawn a skeptic per candidate to REFUTE it, running the scenario when cheap. Uncertain
  means refuted; only survivors are reported; a null result is valid.
- Then de-duplicate, apply the calibration, rank Critical, Warning, Suggestion.

Read `references/verification-and-siblings.md` before spawning the Step 6 skeptics.

## Step 7 - Sweep for siblings

- For each survivor search the other arm of the same dispatch, the paired function, the copied neighbor, the same
  idiom elsewhere; report siblings under the parent and say how the sweep was done.

Read `references/verification-and-siblings.md` before the Step 7 sweep.

## Step 8 - Report

- Nothing survives: say so plainly. Offer to file survivors in the project's tracker.
- Posting is confirm-first: ask before posting to a PR; never approve or request changes unless asked.

Read `references/report-and-scale.md` before writing the Step 8 report and before posting to a PR.

## Scale

- A diff gets one finder per dimension and one skeptic; an audit gets several finders, 3-5 skeptics per finding and a
  completeness critic.

Read `references/report-and-scale.md` before an audit-sized run.

## Standards

The bar is the **engineering-standards** skill; every rule there is a finding category here, even when every test passes.

Read `references/standards-and-hooks.md` before Step 2 when the repo carries engineering standards.

## Project hooks

A repository adds a `## Review rules` section to CLAUDE.md (or `.claude/review.md`): honor its extra dimensions,
banned rules, mechanical checks and tracker.

Read `references/standards-and-hooks.md` before Step 2 to read the repo's `Review rules` section.
