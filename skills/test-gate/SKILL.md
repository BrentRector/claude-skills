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
Size the gate to the blast radius, not to anxiety. Run the targeted gate after each step of serial work and one comprehensive gate at the end.
A landing gate covers the whole affected assembly, unfiltered, never a union of per-change filters.
A change that REJECTS input the tool used to accept runs the whole accepted-input corpus in its own gate.
Fix a test that encodes deliberately changed behaviour so it asserts the new behaviour; never exclude it.
Run the comprehensive gate in its own detached worktree cut at the batch head when other work goes on while it runs.

Read references/tiers-and-landing.md before sizing a landing gate, gating a change that rejects input, or starting a comprehensive run.

## Always first: build fresh

Build the whole solution or workspace fresh before any no-build test run, then confirm the build succeeded.

- .NET: `dotnet build <Solution>.sln` (the solution, not one project), then `dotnet test --no-build`; or drop `--no-build`.
- Python: reinstall editable or compiled extensions. JS/TS: rebuild workspace packages imported from `dist/`.

## A filter that matches nothing is a silent green

- .NET `--filter`: every OR/AND term needs its own property (`FullyQualifiedName~A|FullyQualifiedName~B`); a bare `~A|~B` matches nothing and exits 0.
- pytest `-k` exits 5 on nothing collected, and Jest/Vitest `-t` skips everything and exits 0.
- Read the COUNT, not the pass/fail word: `Total: 0` or "0 passed, N skipped" means the gate did not run. Check each OR'd term's own count.
- After adding tests, find their names in the run output or the test list, and check that the count rose by the number added.

Read references/build-and-filters.md before writing or changing a test filter, running a no-build gate, or adding tests.

## Read the verdict line, not the exit code

1. Redirect the full output to a file; never `| tail -N` it. Grep the file for the summary and for crashes.
2. Never chain anything after a test or build run with `&&`, `||` or `;`, above all never `git commit` or `git push`. Run the gate alone to a log, read the verdict, then take the next step in a separate command.
3. Never edit source while a gate is running.
4. Run long legs one at a time when one of them rebuilds.
5. Identify the kind of failure (stack trace, compile error, diagnostic, timeout) before diagnosing.
6. A missing observation is not a negative one: a killed process or a non-zero exit with no reason is NO VERDICT, reported loudly, never folded into pass or fail. Pass, fail and no-verdict must add up to the declared set; compare against a committed baseline, and differential results case by case, never by totals.
7. A gate that has never failed proves nothing: make a new check, guard test or watcher fail once, for the right reason, before trusting it.

Read references/verdict-and-evidence.md before reading a gate's result, handling a killed or partial run, or adding a new check or watcher.

## Between staging and committing: no conflict markers

After `git add` and before every `git commit` (including WIP checkpoints and merge resolutions), run both; both must print nothing. Read the OUTPUT, not the exit code:

```
git grep --cached -nI -e "^<<<<<<< " -e "^||||||| " -e "^>>>>>>> "
git diff --cached --check | grep -i "conflict marker"
```

Add a repo-wide conflict-marker test and see it fail once on a planted hunk.

Read references/conflict-markers.md before adding that test or when the commands print anything.

## Flakes, CI, standards

- Never call a red a flake without naming the test and the cause, and a clean isolated re-run of that test.
- Attribute every red against the batch's base commit; a red that was there before the batch still blocks the merge. Attribute it honestly and file it; don't step around it.
- CI for the exact pushed commit is the final authority. Until it finishes green, report "local gates green; CI pending", never "all green". A failed status lookup is no verdict: retry, report it as its own outcome.
- Fix a red at its root cause: never weaken an assertion, widen a tolerance, add a skip or re-baseline. Never scope a test to the bug. Expected values come from the authority, not current output. Bar: the engineering-standards skill.
- Project commands, baseline counts and the required CI check belong in the repo's `CLAUDE.md` "Testing" section.

Read references/ci-flakes-standards.md before pushing, attributing a red or flake, or when the project's gate commands are not recorded.
