# Flakes, CI after the push, standards, project hooks

## Flakes and attribution

- **Never call something a flake without naming the test and the cause.** Get the name, run it on its own
  (serially if the suite runs in parallel), and then decide. A flake verdict needs a clean isolated re-run of
  **that** test. The fact that other suites passed is not evidence.
- **Attribute every red before calling it yours, and before calling it someone else's.** Check it against the
  commit the batch started from (`git stash` / a worktree at the base, `git log -S "<symbol or message>"`). A
  red that was already there before your batch **still blocks the merge**. *(Practice — not yet validated: the record shows such reds later stepped around, so it is not yet shown to hold.)* Attribute it honestly and file it.
  Don't step around it.

## After the push: CI is the final authority

Local green is evidence about one host, one OS and one build configuration. CI runs a clean checkout, often
other operating systems and a Release build. Tests that depend on file locks, ACLs, path separators, locale or
timing can pass locally and fail there. *(Validated 2026-09-28.)*

- Read the run for **the exact commit you pushed**:
  `gh run list --commit <sha> --json databaseId,status,conclusion` → `gh run watch <id> --exit-status`, and
  `gh run view <id> --log-failed` on a red run.
- Until that run has finished green, report "local gates green; CI pending", never "all green".
- A status lookup that FAILS (an API timeout, an empty or unknown conclusion) is **no verdict**: retry it, and report
  it as its own outcome - never as red, never as green. *Why: a push script read a transient TLS timeout as an empty
  conclusion and reported "CI is red" on a green run.* *(Practice — not yet validated: the retry path has not been exercised yet.)*
- A red CI run blocks further work. Attribute it by job, step and test, and land the fix on its own before the
  next change.
- If behaviour can differ between Debug and Release, run a local Release leg before pushing. Better still,
  don't write code whose behaviour depends on the build configuration.

## Standards

The bar is the **engineering-standards** skill. At the gate it means:

- A red is fixed at its root cause. Never weaken an assertion, widen a tolerance, add a skip, re-baseline an
  expected value, or edit valid input to make it pass.
- Never scope a test to the bug. Tests verify the complete behavior the spec or design requires; a test that
  covers only the reproduced case leaves the siblings (and the other arm of the dispatch) unguarded.
- A green test that pins wrong behavior is a defect, not a decision. Check rejections and "fails loud" tests
  against the authority.
- Expected values come from the authority, not from copying the current output. *(Validated 2026-09-28.)*
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
- which CI check is required on the default branch, and how pushes get verified against it
