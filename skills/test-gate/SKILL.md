---
name: test-gate
description: Use before every commit, merge or push to choose and run the right test gate — a fast targeted gate per change versus the comprehensive suite per batch — and to read the result without producing a false green.
---

# Test Gate

A gate exists to catch regressions. It fails at that in two ways: running too much, so that every change waits
minutes for a suite it can't affect and people start skipping it, and running too little, so that it reports
green without having looked at what changed. This skill covers both.

**Self-check before any test command: is this one change, or a batch that is about to merge?** One change gets
the targeted gate. A batch gets the full suite. The CI run for the pushed commit has the final say either way.

## The three tiers

| Tier | When | What runs | Cost |
|---|---|---|---|
| **Targeted** | every commit | fresh build · the change's own tests and its neighbours · fast whole-suite smoke tests · one real end-to-end probe of the changed behaviour | ~minutes |
| **Comprehensive** | once per batch, before merge or landing | every affected test assembly or package, **unfiltered** · slow differential/integration legs | ~10–30 min |
| **CI** | after every push | whatever the pipeline runs: other OSes, Release config, clean checkout | final authority |

- **Size the gate to the blast radius, not to anxiety.** Running the full suite on every commit makes the slow
  gate the bottleneck, and a long run that gets waved off is where a real regression slips through as a "flake".
- **Serial work still gets one comprehensive gate.** If a batch has to be built one step at a time (a shared
  parser, a shared schema), run the targeted gate after each step and the comprehensive gate once at the end.
- **A landing gate covers the whole affected assembly, not a hand-picked union of filters.** Merging several
  changes behind `A|B|C|D`, one term per change, leaves out every test that no term names. That leftover set is
  where the breakage shows up, and adding one more term after each failure never covers it. The unfiltered run
  costs less than a red CI run plus a re-push.
- **The comprehensive gate will turn up tests that the targeted filters never loaded,** including tests that
  still encode behaviour someone deliberately changed. Fix the test so it asserts the new behaviour. Don't
  exclude it.

## Always first: build fresh

A no-build test run tests whatever binary was copied into the test output at the last full build.

- .NET: `dotnet build <Solution>.sln`, **the solution rather than one project**, then `dotnet test --no-build`.
  Building only the library does not re-copy it into the test projects' `bin`. Or just drop `--no-build`.
- Python: reinstall editable or compiled extensions (`pip install -e .`, rebuild the C extension) and clear
  stale `__pycache__` / `.pyc` only when you have a reason to think they're stale.
- JS/TS: rebuild workspace packages the tests import from `dist/` (`npm run build -w <pkg>`) before running.

The symptom: local stays green commit after commit while CI, which checks out clean and builds everything, has
been red since the first one.

## A filter that matches nothing is a silent green

The most common false green is a selector that selects nothing and still exits 0.

- **.NET `dotnet test --filter`: every OR/AND term needs its own property.**
  `--filter "FullyQualifiedName~Parser|FullyQualifiedName~Lexer"` works.
  `--filter "~Parser|~Lexer"` matches **nothing**, and so does the mixed form `"FullyQualifiedName~Parser|~Lexer"`.
  Both print "No test matches the given testcase filter" and **exit 0**.
- **pytest `-k`**: an expression that deselects everything exits **5** ("no tests collected"), and CI scripts
  often swallow that code (`|| true`, or `[ $? -eq 5 ]` treated as a pass). `-k` also matches substrings, so a
  typo can quietly pick a different, smaller set than you meant.
- **Jest / Vitest `-t`**: a name pattern that matches nothing still loads the files, marks every test skipped
  and exits 0. (A `testPathPattern` that matches no file does fail, unless `--passWithNoTests` is set, which
  many configs set.)

**Fix:** read the **count**, not just the pass/fail word. `Total: 0` or "0 passed, 312 skipped" means the gate
did not run. Better still, wrap the gate in a script that normalises the filter and **fails on a zero or missing
count**.

## Confirm the new tests actually ran, by name

A test that was written but never discovered (wrong attribute, missing `test_` prefix, a file outside the glob,
a data-driven source that yields no cases, a class that isn't public) passes by never running. It is a red
failure even though nothing printed red. After adding tests, search the run's output for **their names** or list
them (`dotnet test --list-tests`, `pytest --collect-only -q`, `jest --listTests`) and check that the count went up
by the number you added.

## Read the verdict line, not the exit code

1. **Redirect the full output to a file.** Never `| tail -N` it: that drops the failing test's name, which is
   the one thing you need. Then grep the file for the summary (`Passed!|Failed!|Total:`,
   `=== .* passed`, `Tests: `) and for crashes (`crash|abort|Segmentation|OutOfMemory|Failed: *[1-9]`).
2. **Never `&&`-chain `git commit` or `git push` onto a test run or its pipe.** In `test | tail && git push`,
   the exit code is `tail`'s. Read the verdict, then commit in a separate command.
3. **Never edit source while a gate is running.** Legs that compile from the working tree will pick up
   half-made edits and report failures that aren't real. Staging first doesn't protect you. Work on docs or the
   commit message while it runs.
4. **Run long legs one at a time** when one of them rebuilds. A rebuild in the middle of another leg's
   `--no-build` run leaves that leg with no verdict at all.
5. **Know which kind of failure you're looking at before you diagnose it.** A stack trace, a compile error, a
   validation or diagnostic message and a timeout (usually an infinite loop) are four different problems.

## A missing observation is not a negative one

A verdict needs the evidence it claims to have. "Passed" means the thing ran to completion and was checked. A
killed process leaves truncated output, and truncated output can compare exactly like a wrong answer, or like a
correct one. A non-zero exit with no reason attached is a **lost result**, not a failure you can reason about.
Anything like that is **no verdict**, and should be reported loudly as such, never folded into pass or fail.

- **Check the population, not only the failure count.** Pass, fail and no-verdict should add up to the declared
  set. A harness that only counts failures will report "all green" when a case disappears.
- **Compare against a committed baseline or manifest,** never a number someone remembers.
- **Compare differential or snapshot results case by case, never by totals.** Totals that barely move can hide
  one fix plus two regressions.
- **A filter, ranker or selector tells you about what it returned and nothing about what it dropped.** Before
  you trust one, look at its complement.
- Re-running something that produced no observation is legitimate. Re-running a failed assertion until it
  passes is not.

## A gate that has never failed proves nothing

Before trusting a new check, a new guard test or a watcher on a long job, **make it fail once**: restore the
defect, point it at an older revision, kill the process it watches. Make sure it fails **for the right reason**,
not because some unrelated problem had already turned it red. Then ask **what its scope leaves out** and whether
the reasoning behind each exclusion still holds. A guard can be green, correct, and aimed at the wrong
population. For long jobs, only positive evidence (the process exists, the log shows the expected phase line,
artifacts are growing) counts as proof that the job is alive. A broken monitor and a healthy job both look like
silence.

## Flakes and attribution

- **Never call something a flake without naming the test and the cause.** Get the name, run it on its own
  (serially if the suite runs in parallel), and then decide. A flake verdict needs a clean isolated re-run of
  **that** test. The fact that other suites passed is not evidence.
- **Attribute every red before calling it yours, and before calling it someone else's.** Check it against the
  commit the batch started from (`git stash` / a worktree at the base, `git log -S "<symbol or message>"`). A
  red that was already there before your batch **still blocks the merge**. Attribute it honestly and file it.
  Don't step around it.

## After the push: CI is the final authority

Local green is evidence about one host, one OS and one build configuration. CI runs a clean checkout, often
other operating systems and a Release build. Tests that depend on file locks, ACLs, path separators, locale or
timing can pass locally and fail there.

- Read the run for **the exact commit you pushed**:
  `gh run list --commit <sha> --json databaseId,status,conclusion` → `gh run watch <id> --exit-status`, and
  `gh run view <id> --log-failed` on a red run.
- Until that run has finished green, report "local gates green; CI pending", never "all green".
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
- which CI check is required on the default branch, and how pushes get verified against it
