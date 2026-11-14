---
name: test-gate
description: Chooses and runs the right test gate before a commit, merge, enqueue or push, and reads its result without producing a false green. Use when deciding which tests a change must pass; when deciding whether a gate's result allows the merge or push (a red that also fails on the base commit, a suspected flake, a filter that matched nothing, CI not yet finished); when adding a check to the commit step or any guard meant to stop a bad commit; or when local and CI results disagree.
---

# Test Gate

**The result is a gate that cannot report a false green: every case the merge run executes was run green at the
head that lands, or a recorded pass at the same inputs covers it.** It is checked by evidence, never by an exit
code: the verdict line quoted from the log, the count that ran, and pass, fail and no-verdict adding up to the
declared population. A gate fails in two ways, running too little and reporting green on what it never looked at,
or running what did not change until people skip it; this skill covers both.

**Self-check before any test command: what does THIS run have to prove?** At the head that lands, the gate rule
below. While developing, nothing: run what is fast.

## The three tiers

**The gate rule: every case the merge run executes was run green at the head that lands, on this host and
toolchain, or a recorded pass at the same inputs covers it.** The merge run is then the first run only of what the
host cannot run (the merged tree, another OS, another configuration, CI's runners), so a red there is one of those,
a flake or infrastructure, never an untested case. A selection (a filter, an impact map, a union of per-change
terms) is never the landing gate: what it leaves out is where the red shows up.

One worked design, for a merge queue with CI on two operating systems:

| Tier | Where and when | What runs | Cost |
|---|---|---|---|
| **Local gate** | the developer's OS, at the branch head, before it lands | fresh build · the whole population of every test target, minus each target a recorded pass at its current inputs covers · every **host-only witness** (by trait) · the audits whose inputs changed | the host's time per landing; content keys hold it to what changed |
| **Merge group** | CI, on the merged tree, before the default branch moves | every target on the other OS and configurations · on the developer's OS, each target no recorded pass at the merged tree's inputs covers | runners; a red bounces the change, one round trip |
| **Battery** | local, once per accumulated batch | slow legs no gate runs (a differential against another implementation, a large corpus) | ~10–30 min |

The change's leg also runs on the other OS locally (a clone built there, fail-fast native first) when there is no
merge group, when the change's own tests often go red only there, or when a witness reproduces only on a local
other-OS host. Host-only witnesses (a property CI's runners lack) run in every local gate, their membership derived
from a trait. A change that REJECTS input the tool used to accept runs the whole accepted-input corpus. No test
carries a fixed wall-clock time limit. A test that encodes deliberately changed behaviour is fixed to assert the new
behaviour, never excluded. Every gate and CI run the line-ending drift check (no CR in any tracked text file; the
`cross-platform` skill). The project's own gate definition, in its `CLAUDE.md` "Testing" section, decides the shape.

Read references/tiers-and-landing.md before choosing or changing a gate's shape, adding a host-only witness or a
time-limited test, or gating a change that rejects input: it holds the reasons and the costs.

## Always first: build fresh

Build the whole solution or workspace fresh before any no-build test run, then confirm the build succeeded.

- .NET: `dotnet build <Solution>.sln` (or `.slnx`; the solution, not one project), then `dotnet test --no-build`; or drop `--no-build`.
- Python: reinstall editable or compiled extensions. JS/TS: rebuild workspace packages imported from `dist/`.

## A filter that matches nothing is a silent green

- .NET `--filter`: every OR/AND term needs its own property (`FullyQualifiedName~A|FullyQualifiedName~B`); a bare `~A|~B` matches nothing and exits 0.
- pytest `-k` exits 5 on nothing collected, and Jest/Vitest `-t` skips everything and exits 0.
- Read the COUNT, not the pass/fail word: `Total: 0` or "0 passed, N skipped" means the gate did not run. Check each OR'd term's own count.
- After adding tests, find their names in the run output or the test list, and check that the count rose by the number added.

Read references/build-and-filters.md before writing or changing a test filter, running a no-build gate, or adding tests.

## Read the verdict line, not the exit code

1. Redirect the full output to a file; never `| tail -N` it. Grep the file for the summary and for crashes.
2. Never chain anything after a test or build run with `&&`, `||` or `;`, above all never `git commit` or `git push`: in `test | tail && git push` the exit code is `tail`'s. Run the gate alone to a log, read the verdict, then take the next step in a separate command. The one exception is `; echo "EXIT=$?"`, which keeps the status in the same call.
3. Never edit source while a gate is running.
4. Run long legs one at a time when one of them rebuilds.
5. Identify the kind of failure (stack trace, compile error, diagnostic, timeout) before diagnosing.
6. A missing observation is not a negative one: a killed process or a non-zero exit with no reason is NO VERDICT, reported loudly, never folded into pass or fail. Pass, fail and no-verdict must add up to the declared set; compare against a committed baseline, and differential results case by case, never by totals.
7. A gate that has never failed proves nothing: make a new test, check, guard or watcher fail once, for the right reason (against the defect restored or a mutation of what it guards), and record what it was seen to fail under, before trusting it. A witness that closes a rule of a standard follows `spec-compliance-audit` §5 (the mutation named in the verdict).

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
- CI is the final authority: the merge-group run for a queued change, the run for the exact commit otherwise. Classify a merge-group red against the branch's gate record before changing anything; a red the branch caused is fixed on its branch before re-enqueue. A failed status lookup is no verdict: retry, report it as its own outcome.
- A red the branch did not cause (it fails at the base, on main, or in the merge group outside anything the branch reaches) is root-fixed at once, as its own change, and that fix reaches the build ahead of the queued work it would hit. *Why: every landing queued behind a red main carries meets it; in one project a single flaky test met 18 merge groups and three re-queues before its fix reached main, 13 hours after the first red.*
- A second re-run of one cause is refused. An infrastructure or runner red may be re-run once; a second red of the same case is a defect of the test or the pipeline, filed with its rate and fixed at its root. *Why: re-running in place of a root fix was the costliest process failure measured, about one extra local gate per landing.*
- A gate does not re-run a test whose inputs are unchanged since its last recorded pass: it reports the target as reused and names the record. A re-gate at an unchanged tree, or a full gate after a commit no test reads, shows nothing new.
- Fix a red at its root cause: never weaken an assertion, widen a tolerance, add a skip or re-baseline. Never scope a test to the bug. Expected values come from the authority, not current output.
- Project commands, baseline counts and the required CI check belong in the repo's `CLAUDE.md` "Testing" section.

Read references/ci-flakes-standards.md before pushing or enqueuing, attributing a red, a bounce or a flake, re-running anything, or when the project's gate commands are not recorded.
