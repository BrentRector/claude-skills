# test-gate

Choosing and running the right test gate before a commit, merge or push, and reading its result without
producing a false green. A gate exists to catch regressions, and it fails in two ways: it runs too much, so every
change waits minutes for a suite it cannot affect and people start skipping it; or it runs too little, so it
reports green without having looked at what changed. This skill addresses both.

## When Claude uses it

Claude loads a skill automatically when the request matches its `description`. This one matches before every
commit, merge or push. You can also ask directly ("run the gate before committing this", "gate this batch before
merge") or name the skill (`test-gate`) in your request.

Its first move is a self-check: **what does this run have to prove?** At the head that lands, that every case the
merge run will execute is green there, or covered by a recorded pass at the same inputs. The gate rule is stated as
that outcome; the skill gives one design that meets it: the whole population on the developer's OS locally, the
other OS and the merged tree in the merge group.

## What it does

### The three tiers

| Tier | Where and when | What runs | Cost |
|---|---|---|---|
| **Local gate** | the developer's OS, at the branch head, before it lands | fresh build, the whole population minus the targets a recorded pass at their current inputs covers, every host-only witness (by trait), the audits whose inputs changed | the host's time per landing |
| **Merge group** | CI, on the merged tree | every target on the other OS and configurations; on the developer's OS, what no recorded pass at the merged tree covers | runners; final authority |
| **Battery** | local, once per accumulated batch | slow legs no gate runs | ~10–30 min |

### The procedure

1. **Build fresh.** A no-build run tests whatever binary was copied at the last full build. In .NET, build the
   solution (not one project) before `dotnet test --no-build`; in Python, reinstall editable or compiled
   extensions; in JS/TS, rebuild workspace packages that tests import from `dist/`.
2. **Run the tier.** At the head that lands, the whole population minus what a recorded pass covers. A change that rejects input the tool used to accept also runs
   the whole accepted-input corpus.
3. **Check the filter selected something.** Read the test count, not the pass/fail word.
4. **Confirm new tests ran, by name** (`dotnet test --list-tests`, `pytest --collect-only -q`,
   `jest --listTests`), and that the count rose by the number added.
5. **Read the verdict line.** Redirect the full output to a file, then grep it for the summary and for crashes.
   Commit or push in a separate command.
6. **Check the population.** Pass, fail and no-verdict must add up to the declared set, compared against a
   committed baseline, case by case for differential or snapshot results.
7. **Attribute every red** against the batch's base commit before calling it yours or someone else's.
8. **Between `git add` and `git commit`, assert no conflict markers are staged:**
   `git grep --cached -nI -e "^<<<<<<< " -e "^||||||| " -e "^>>>>>>> "` and
   `git diff --cached --check | grep -i "conflict marker"` must both print nothing (read the output, not the
   exit code).
9. **After the enqueue or push, read CI:** under a merge queue, the pull request's merge-group checks
   (`gh pr view <n> --json mergeQueueEntry,statusCheckRollup`), and a bounce is classified against the branch's gate
   record first: a red the branch caused is fixed on its branch before re-enqueue, and a red it did not cause is
   root-fixed first; otherwise `gh run list --commit <sha> --json databaseId,status,conclusion` then
   `gh run watch <id> --exit-status`, and `gh run view <id> --log-failed` on a red run.

## Why it works this way

- **Size the gate to the blast radius, not to anxiety.** Running everything on every commit makes the slow gate
  the bottleneck, and a long run that gets waved off is where a real regression slips through as a "flake".
- **The landing gate covers the whole population.** Merging several changes behind `A|B|C|D`, one filter term
  per change, leaves out every test no term names, and that leftover set is where breakage shows up.
  *(Validated 2026-09-28.)* Under a merge queue that gate is CI's merge-group run, the merged tree itself.
- **The gate rule is an outcome; the design is one way to meet it.** Every case the merge run executes ran green
  at the head that lands, or a recorded pass at the same inputs covers it, so a merge-group red is never an untested
  case. The worked design runs the whole population on the developer's OS locally and leaves the other OS and the
  merged tree to the merge group: in the project it comes from, a per-change local Linux leg found one red in 78
  records, and that one false. Earlier, a targeted local leg on both OSes was the design (local whole-population
  runs had been 41 % of landing time on 2026-10-10, 8 of 15 RED mostly on fixed time limits under load; 3 of 38
  landed changes had other-OS-only reds in their own tests), and it is still the right shape with no merge group.
  Content keys and the removal of fixed time limits are what make the whole population affordable locally.
- **Conflict markers are checked in what is staged, by output.** Four unresolved hunks in a script that no test
  imports passed three green gates. `git diff --cached --check` also flags every line of a CRLF file as trailing
  whitespace, so the rule reads the output for "conflict marker" rather than the exit code, and a repo-wide
  conflict-marker test, seen to fail once on a planted hunk, backs it. Since the test was adopted, no marker has
  reached main. *(Validated 2026-09-28.)*
- **Tightenings have a global blast radius.** A new diagnostic or stricter parser can break every "must be
  accepted" sample. The skill's own example: an implementer gated a tightening on its own tests, and the landing
  gate found 15 compatibility cases (5 samples at 3 language versions) it had broken. *(Practice — not yet validated: one use so far.)*
- **Stale binaries hide regressions.** The symptom is local green commit after commit while CI, building from a
  clean checkout, has been red since the first one. A failed or incremental build can also leave a stale assembly, so confirm the
  build succeeded and hash the assemblies when in doubt. *(Validated 2026-09-28.)*
- **A filter that matches nothing is a silent green.** In .NET, `--filter "~Parser|~Lexer"` matches nothing
  (every OR/AND term needs its own property, e.g. `FullyQualifiedName~Parser|FullyQualifiedName~Lexer`) and exits
  0. pytest `-k` that deselects everything exits 5, which CI scripts often swallow. Jest/Vitest `-t` with no
  match marks everything skipped and exits 0. A wrapper that fails on a zero or missing count closes this hole, and each OR'd term needs its own count: one
  dead term among live ones still prints a verdict. *(Validated 2026-09-28.)*
- **Undiscovered tests pass by never running.** A wrong attribute, a missing `test_` prefix or a non-public class
  prints nothing red. *(Validated 2026-09-28.)*
- **The exit code is not the verdict.** `| tail -N` drops the failing test's name, and in
  `test | tail && git push` the exit code is `tail`'s. So nothing is chained after a test or build run: it runs
  alone to a log, the verdict line is read, and the next step is a separate command (`; echo "EXIT=$?"` keeps
  the status in the same call). The `automating-agent-guardrails` skill ships a guard rule that enforces this. *(Validated 2026-09-28; the hook form is not yet proven in production.)*
- **Don't edit source while a gate runs**, and run rebuilding legs one at a time: legs that compile from the
  working tree pick up half-made edits, and a rebuild in the middle of a `--no-build` leg leaves it with no
  verdict. *(Practice — not yet validated: no before/after measure of false reds.)*
- **A missing observation is not a negative one.** A killed process leaves truncated output that can compare like
  a wrong answer or a correct one. That is "no verdict", reported loudly, never folded into pass or fail. Totals
  that barely move can hide one fix plus two regressions, so differential results are compared per case.
  Re-running something that produced no observation is legitimate; re-running a failed assertion until it passes
  is not. *(Validated 2026-09-28.)*
- **A gate that has never failed proves nothing.** Make a new check fail once, for the right reason, and ask what
  its scope leaves out. For long jobs, only positive evidence counts as liveness: a broken monitor and a healthy
  job both look like silence. *(Validated 2026-09-28.)*
- **No "flake" without a name.** A flake verdict needs a clean isolated re-run of that test. A red that predates
  the batch still blocks the merge; attribute it and file it. *(Practice — not yet validated: the record shows such reds later stepped around.)*
- **CI is the final authority.** Local green is evidence about one host, OS and configuration. A failed status
  lookup is its own outcome, never red or green: the skill cites a push script that read a transient TLS timeout
  as "CI is red" on a green run. A red CI run blocks further work until its fix lands on its own. *(CI as final authority: validated 2026-09-28.
  The failed-lookup rule: practice, not yet validated: its retry path has not been exercised yet.)*

The *Standards* section states the bar at the gate:
fix a red at its root cause (never weaken an assertion, widen a tolerance, add a skip, re-baseline an expected
value or edit valid input); never scope a test to the bug; treat a green test that pins wrong behaviour as a
defect; take expected values from the authority, not the current output.

## Using it in your project

The skill is generic; the commands belong to your repository. It looks for them, and records them if missing, in
the project's `CLAUDE.md` under a **"Testing"** section (or `CONTRIBUTING.md`, or the CI workflow file):

- the build command (which solution or workspace) and each tier's exact test commands;
- the **baseline counts** for each suite (total / passed / skipped), so a vanished population can be seen;
- which legs are slow, which rebuild, and which must run alone;
- a wrapper script, if one exists, that expands filter shorthand and fails on a missing verdict line (preferred
  over raw commands);
- which CI check is required on the default branch, whether a merge queue gates it, and how pushes or queued pull
  requests are verified against it;
- which tests are host-only witnesses (the trait), and which audits are reused when their inputs are unchanged.

Prerequisites: the GitHub CLI (`gh`) for the CI step. The build and filter guidance covers .NET, Python and
JS/TS; other stacks supply their own commands through the hooks above.

Related skills: [`dotnet-engineering`](../dotnet-engineering/SKILL.md) covers `dotnet test` filter traps in
.NET depth, and the `pr-test-analyzer` agent reviews the tests themselves.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The full rules: tiers, fresh build, filter traps, verdict reading, evidence, flakes, CI, project hooks |
| `README.md` | This overview |
