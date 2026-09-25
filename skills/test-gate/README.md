# test-gate

Choosing and running the right test gate before a commit, merge or push, and reading its result without
producing a false green. A gate exists to catch regressions, and it fails in two ways: it runs too much, so every
change waits minutes for a suite it cannot affect and people start skipping it; or it runs too little, so it
reports green without having looked at what changed. This skill addresses both.

## When Claude uses it

Claude loads a skill automatically when the request matches its `description`. This one matches before every
commit, merge or push. You can also ask directly ("run the gate before committing this", "gate this batch before
merge") or name the skill (`test-gate`) in your request.

Its first move is a self-check: **is this one change, or a batch that is about to merge?** One change gets the
targeted gate, a batch gets the full suite, and the CI run for the pushed commit has the final say either way.

## What it does

### The three tiers

| Tier | When | What runs | Cost |
|---|---|---|---|
| **Targeted** | every commit | fresh build, the change's own tests and neighbours, fast whole-suite smoke tests, one real end-to-end probe of the changed behaviour | ~minutes |
| **Comprehensive** | once per batch, before merge or landing | every affected test assembly or package, **unfiltered**, plus slow differential/integration legs | ~10–30 min |
| **CI** | after every push | whatever the pipeline runs: other OSes, Release config, clean checkout | final authority |

### The procedure

1. **Build fresh.** A no-build run tests whatever binary was copied at the last full build. In .NET, build the
   solution (not one project) before `dotnet test --no-build`; in Python, reinstall editable or compiled
   extensions; in JS/TS, rebuild workspace packages that tests import from `dist/`.
2. **Run the tier.** Size it to the blast radius. A change that rejects input the tool used to accept also runs
   the whole accepted-input corpus.
3. **Check the filter selected something.** Read the test count, not the pass/fail word.
4. **Confirm new tests ran, by name** (`dotnet test --list-tests`, `pytest --collect-only -q`,
   `jest --listTests`), and that the count rose by the number added.
5. **Read the verdict line.** Redirect the full output to a file, then grep it for the summary and for crashes.
   Commit or push in a separate command.
6. **Check the population.** Pass, fail and no-verdict must add up to the declared set, compared against a
   committed baseline, case by case for differential or snapshot results.
7. **Attribute every red** against the batch's base commit before calling it yours or someone else's.
8. **After the push, read CI for the exact commit:**
   `gh run list --commit <sha> --json databaseId,status,conclusion` then `gh run watch <id> --exit-status`, and
   `gh run view <id> --log-failed` on a red run. Until it is green, the status is "local gates green; CI pending".

## Why it works this way

- **Size the gate to the blast radius, not to anxiety.** Running everything on every commit makes the slow gate
  the bottleneck, and a long run that gets waved off is where a real regression slips through as a "flake".
- **A landing gate covers the whole affected assembly.** Merging several changes behind `A|B|C|D`, one filter term
  per change, leaves out every test no term names, and that leftover set is where breakage shows up. The
  unfiltered run costs less than a red CI run plus a re-push.
- **Tightenings have a global blast radius.** A new diagnostic or stricter parser can break every "must be
  accepted" sample. The skill's own example: an implementer gated a tightening on its own tests, and the landing
  gate found 15 compatibility samples it had broken.
- **Stale binaries hide regressions.** The symptom is local green commit after commit while CI, building from a
  clean checkout, has been red since the first one.
- **A filter that matches nothing is a silent green.** In .NET, `--filter "~Parser|~Lexer"` matches nothing
  (every OR/AND term needs its own property, e.g. `FullyQualifiedName~Parser|FullyQualifiedName~Lexer`) and exits
  0. pytest `-k` that deselects everything exits 5, which CI scripts often swallow. Jest/Vitest `-t` with no
  match marks everything skipped and exits 0. A wrapper that fails on a zero or missing count closes this hole.
- **Undiscovered tests pass by never running.** A wrong attribute, a missing `test_` prefix or a non-public class
  prints nothing red.
- **The exit code is not the verdict.** `| tail -N` drops the failing test's name, and in
  `test | tail && git push` the exit code is `tail`'s.
- **Don't edit source while a gate runs**, and run rebuilding legs one at a time: legs that compile from the
  working tree pick up half-made edits, and a rebuild in the middle of a `--no-build` leg leaves it with no
  verdict.
- **A missing observation is not a negative one.** A killed process leaves truncated output that can compare like
  a wrong answer or a correct one. That is "no verdict", reported loudly, never folded into pass or fail. Totals
  that barely move can hide one fix plus two regressions, so differential results are compared per case.
  Re-running something that produced no observation is legitimate; re-running a failed assertion until it passes
  is not.
- **A gate that has never failed proves nothing.** Make a new check fail once, for the right reason, and ask what
  its scope leaves out. For long jobs, only positive evidence counts as liveness: a broken monitor and a healthy
  job both look like silence.
- **No "flake" without a name.** A flake verdict needs a clean isolated re-run of that test. A red that predates
  the batch still blocks the merge; attribute it and file it.
- **CI is the final authority.** Local green is evidence about one host, OS and configuration. A failed status
  lookup is its own outcome, never red or green: the skill cites a push script that read a transient TLS timeout
  as "CI is red" on a green run. A red CI run blocks further work until its fix lands on its own.

The *Standards* section applies the [`engineering-standards`](../engineering-standards/SKILL.md) bar at the gate:
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
- which CI check is required on the default branch, and how pushes are verified against it.

Prerequisites: the GitHub CLI (`gh`) for the CI step. The build and filter guidance covers .NET, Python and
JS/TS; other stacks supply their own commands through the hooks above.

Related skills: [`dotnet-engineering`](../dotnet-engineering/SKILL.md) covers `dotnet test` filter traps in
.NET depth, and the `pr-test-analyzer` agent reviews the tests themselves.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The full rules: tiers, fresh build, filter traps, verdict reading, evidence, flakes, CI, project hooks |
| `README.md` | This overview |
