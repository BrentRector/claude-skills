# Regression evals

Behavioral regression tests for the `brent-tools` plugin, run with
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals). Each case proves that one skill or agent
**changes what Claude does**. Every case runs twice: once with the plugin loaded (WITH) and once with no plugin
(W/OUT). A case is only kept if the plugin arm beats the no-plugin arm. If the plugin arm does no better, the case
tests Claude rather than the skill, and so it can't detect an edit that breaks the skill.

## What it covers

Twenty-eight cases: they cover all thirteen skills (one to six cases each) and each of the four agents. Each case is a small
scenario, written inline in its `prompt.md`, that can only be handled correctly by following that skill's rule.

**Scores live in [`baselines/`](baselines/)**, one file per model, effort level and plugin version, each written by
`run_evals.py table` from a full run that recorded its model and effort. Compare a change against the baseline of
the same model and effort. The table this section used to carry (2026-09-25 and later single-case runs, model
unrecorded) is retired: the 2026-10-19 full run already contradicted it.

| Case | Covers | The rule it checks |
|---|---|---|
| `review-wall-clock-ceiling` | review | Reports a `Stopwatch` ceiling test as a finding with a `Scenario:` and a deterministic replacement for it |
| `variant-analysis-latent-not-cleared` | variant-analysis | Reports a variant that nothing calls as *latent*, not cleared, and records the query calibration |
| `spec-oracle-render-the-diagram` | spec-oracle | Settles a required-vs-optional keyword by rendering the printed page, where underlining decides, instead of trusting the extracted text |
| `spec-compliance-audit-partial-verdict` | spec-compliance-audit | A rule that holds on one path and fails on another is `PARTIAL`, never `CONFORMS` |
| `test-gate-conflict-markers-staged` | test-gate | Between `git add` and `git commit`, checks what is STAGED (`git grep --cached` for the marker lines) and reads the OUTPUT of `git diff --cached --check` for "conflict marker" instead of its exit code |
| `test-gate-preexisting-red-blocks-merge` | test-gate | A red that already existed before the batch is attributed and filed, but it still blocks the merge |
| `dotnet-engineering-single-current-tfm` | dotnet-engineering | Targets one current TFM, with no `netstandard2.0` and no multi-targeting when no consumer is named |
| `roslyn-analysis-renamed-clones` | roslyn-analysis | Uses the bundled type-2 clone detector (`detect-clones.cs`) to find renamed copies |
| `roslyn-analysis-safe-rewriter` | roslyn-analysis | Uses the bundled `rewrite-template.cs` harness (dry run by default) for a mechanical rewrite |
| `agent-fleet-brief-limits` | agent-fleet | Uses the measured turn cap (~150–160) and a graceful STOP file in a dispatch brief |
| `agent-fleet-file-clusters` | agent-fleet | Assigns defects to implementer slots by COMPUTED per-file clusters ranked by summed harm, naming the bundled `fix_clusters.py` |
| `agent-fleet-orientation` | agent-fleet | Tells implementers to orient with the bundled `orient.py --notes …` (outline, covering tests, what earlier fixes learned) before reading source |
| `agent-fleet-stamped-handoff` | agent-fleet | Stamps the handoff summary with the commit it describes (`STATUS-AT: <sha>`) and has a resuming or successor agent run the bundled `status_delta.py` to read only the commits the summary does not cover |
| `agent-fleet-reprobe-backlog` | agent-fleet | The implementer re-runs each stale item's repro first; one that no longer reproduces is discharged with evidence (the commit it ran on) and goes to a refuter |
| `agent-fleet-registrar-rerun` | agent-fleet | The agent that files leads runs each lead's given repro once on its own build before filing (no fresh probe when a repro exists) and verifies quoted citations at their source |
| `merge-queue-landing-finished-work-lands` | merge-queue-landing | A same-file predecessor reviewed CLEAN is enqueued at once (`A: ENQUEUE-NOW`, never held to land through its successor), the successor merges the REVIEWED head (the finisher's), a medium finding at the capped round is a lead (`X-ROUND-3: CLEAN`), and a torn findings file holds the branch that contains its head (`R: HELD`) |
| `claude-cloud-sessions-multi-repo-hooks` | claude-cloud-sessions | Explains that multi-repo sessions start in `/home/user` and load no repo hooks, and fixes it with a user-level hook shim |
| `agent-pr-test-analyzer` | pr-test-analyzer | Checks determinism: names a work-count or growth-ratio replacement for a Stopwatch ceiling (`Check:` findings) |
| `agent-silent-failure-hunter` | silent-failure-hunter | Ranks the silent default price above the crash; findings carry `Harm: silent wrong answer` |
| `agent-type-design-analyzer` | type-design-analyzer | Replaces the kind enum with its per-kind fields by a closed hierarchy; findings carry a `Smell:` classification |
| `agent-comment-analyzer` | comment-analyzer | Rejects a citation that answers a different question and finds the governing clause; findings carry `Scenario:`/`Evidence:` |
| `devlog-correction-and-clock` | devlog | Records an overturned finding as a NEW entry (`OLD-ENTRY: LEAVE`, against a teammate's "fix it in place") and takes the header time from the clock (`date`), not from "around 4:30" |
| `devlog-commit-hook` | devlog | Registers the missing-entry hook (now on `gh pr create`, one entry per landing) with NO `if` filter (which misses `git push … && gh pr create`), although the prompt asks for one, and has it ASK rather than deny. |
| `devlog-insert-entry` | devlog | Adds an entry to a CRLF, newest-first log with the bundled `devlog.py` (a one-time `migrate` to one file per entry, then `new`) instead of a hand-written splice. |
| `devlog-consolidate-brief` | devlog | A brief to consolidate the log into learnings closes with an open-problems list and a not-yet-acted-on list |
| `automating-agent-guardrails-guard-design` | automating-agent-guardrails | A guard hook for "no stash / land main only via the script" fails OPEN on its own errors (`ON-ERROR: ALLOW`) and scopes the push rule to this repository (`OTHER-REPO: ALLOWED`) |

A case's score is the mean over its runs of the fraction of scored graders that passed; W/OUT is the same score
with no plugin loaded.

## How to run it

From the repository root, always through `scripts/run_evals.py`, which names the model and the effort level and
records both in the result. The suite uses only read-only tools, so it needs no `--allow-tools` or sandbox and runs
on native Windows.

The two tiers the skills are measured on:

```
python scripts/run_evals.py run --model claude-opus-5-5 --effort medium     # worker tier
python scripts/run_evals.py run --model claude-mythos-5-2 --effort high     # top tier
```

Do not run `claude plugin eval` bare for a measurement. Its children load the operator's user settings
(`--setting-sources user`), so without `--model` they run on whatever default model that machine has, at whatever
`effortLevel` it has, and the CLI records neither the effort nor (without `--model`) the model. The wrapper:

- refuses an alias (`opus`) and requires a full model id, because an alias resolves to a different model over time;
- passes `--model` and sets the effort through `CLAUDE_CODE_EFFORT_LEVEL` in the children's environment, which takes
  precedence over every `effortLevel` setting; it refuses to run when the user settings' `env` block sets that
  variable itself, since a settings `env` overrides the process environment in the child;
- reads every run's trace and fails if any run did not start on the requested model; it records the other models
  seen in a run's usage (a subagent's model comes from `CLAUDE_CODE_SUBAGENT_MODEL` in the user settings `env`
  when that is set, and the record names it);
- marks each run that hit its turn cap or timeout (`cutOff`), so a cut-off is not read as a skill failure;
- writes `suite.model`, `suite.effort`, the same on every case, the git head and the CLI version into
  `evals/results/<timestamp>-<model>-<effort>/aggregate-result.json` (gitignored), with a `summary.md` beside it.

It always passes `--threshold 0` (the Δ column is the verdict here, see below), `--no-publish` and `--trust-plugin`.

- To iterate on one case cheaply: `python scripts/run_evals.py run --model <id> --effort <level> --case <name>
  --runs 1 -j 2`. A single run is noisy, so confirm a change at the default of 3 runs.
- To repair a measurement: a case with a cut-off run is re-sized, re-run alone (`run ... --case <name>`), and
  merged back: `python scripts/run_evals.py merge evals/results/<full run> evals/results/<re-run>... --out <name>`.
  The merge refuses a re-run of another model, effort, plugin version or skills tree, or one still cut off, and
  records which runs replaced which in `suite.merged`; the baseline table lists each replaced case.
- To keep a measurement: `python scripts/run_evals.py table evals/results/<dir> --out evals/baselines/<name>.md`
  writes the compact table and a JSON sidecar, both tracked.
- To compare two measurements: `python scripts/run_evals.py compare <before> <after>` (results directories or
  baseline JSON files). It refuses two results of different models or efforts, because that difference measures the
  model, not the skill.
- Cost: see the baseline files in [`baselines/`](baselines/), which record each full run's duration and the list-price
  cost the CLI reports.

## How to read the result

```
CASE                                   WITH  W/OUT Δ      RUNS COST
test-gate-preexisting-red-blocks-merge 1.00  0.00  +1.00  6    $0.44
```

- **Δ = WITH − W/OUT** is what the skill contributes. A case is doing its job when Δ is clearly positive.
- **Δ near 0 with WITH high:** Claude now does this by default, so the case no longer tests the skill. Rewrite it
  around a rule Claude does not follow unaided, or drop it.
- **Δ near 0 with both scores low:** the skill no longer produces the behavior. This is the regression the suite
  exists to catch. Check whether the `skill-fired` / `agent-dispatched` indicator (a with-only, unscored grader)
  passed. If it failed, the skill never loaded (look at its `description`, or at the prompt's trigger). If it
  passed, an edit removed or weakened the rule.
- **Negative Δ:** the plugin made the answer worse. Treat that as a bug in the skill.
- Before believing a low score, check the `NOTES` column for a rate-limit or usage-limit error.

## How the cases are built

- **Prompts are self-contained.** Each run starts in an empty directory, so the code, the diff, and any spec
  excerpt are written into `prompt.md`. There are no scaffold scripts and no fixtures on disk.
- **Triggering.** Every prompt uses natural phrasing and none names its skill, so each case also tests its skill's
  or agent's `description` (the agent cases ask for "a specialist ... reviewer if you have one"). The with-only
  `skill-fired` / `agent-dispatched` indicator shows whether it routed; a case whose skill does not load is a
  finding against that description, not a reason to name the skill in the prompt. Prompts carry no length caps,
  only the forced lines their graders read. Until 2026-11-14 fourteen prompts named their skill and twenty capped
  the answer; [`RETUNE.md`](RETUNE.md) records the change, and `baselines/README.md` the cases whose series restarts.
- **Graders.** Most graders are deterministic regexes over the final message, often on a forced last line such as
  `MERGE: NO`. `llm` graders are used only where no deterministic signal exists (refusing a fallback, keeping a
  runtime registry reflection-free), and their rubrics state concrete PASS and FAIL conditions.
- **Limits.** The limits must cover the slowest tier the suite targets, which today is Mythos 5.2 at `high`. A
  case's `max_turns` and `timeout_seconds` are each at least twice (the timeout rounded up to a minute) the most
  turns and seconds any run of it used on any targeted tier, a cut-off run counting as the limit it hit; they are
  never lowered. A limit costs nothing for a run that finishes inside it, but a run it cuts off scores as a skill
  failure. `run_evals.py` lists every run cut off by either limit (`cutOff`); when one appears, re-size that case and
  re-run it (`--case`, then `merge`) before the result is a baseline. Sized 2026-11-14 from the two tier baselines
  in `baselines/`, on top of an earlier floor of four times the 50 pre-tier results (model unrecorded, largest 90 s).
  On Mythos 5.2 `high` the largest uncut run took 254 s and 15 turns (`devlog-commit-hook`); on Opus 5.5 `medium`,
  74 s and 8 turns.
- **Never grade a skill case on `trace`.** The `Skill` tool result in the trace contains the SKILL.md text, so a
  trace regex would match the skill's own words. Agent cases may grade the `trace`: the subagent's report is there,
  but its definition file is not. That is how their finding format (`Check:`, `Harm:`, `Smell:`, `Scenario:`) is
  checked.
- **Prose mentions count as matches.** A `not_contains` regex matches a skill's own warning ("never `git stash`")
  just as it matches the forbidden command. Anchor such regexes to the command or code line (`^\s*git stash` with
  flag `m`), or grade with a rubric.

## Rule: a skill change ships with its eval

When you add or change a skill or agent rule:

1. **Add or update a case in the same change.** Write a small scenario that can only be handled correctly by
   following the rule, and grade the rule's distinctive output.
2. **Measure it with the baseline:**
   `python scripts/run_evals.py run --model <id> --effort <level> --case <name> --runs 3`, on each tier the
   baselines cover. Keep the case only if WITH clearly beats
   W/OUT. If the baseline passes as often as the plugin, rewrite the case around what Claude does *not* do unaided,
   or drop it and record why below.
3. **Run the full suite before merging a skill edit,** on each tier, and compare it with that tier's baseline:
   `python scripts/run_evals.py compare evals/baselines/<baseline>.json evals/results/<dir>`. A Δ that falls toward 0
   means the edit weakened the skill.
4. When a release changes the numbers, write the new baseline with `run_evals.py table` into `baselines/`.

## Cases dropped during authoring (baseline passed as often as the plugin)

These were written, run with ablation, and dropped because Claude already does the right thing without the plugin.
Each is kept here so nobody spends money writing it again.

| Case | Rule | Result |
|---|---|---|
| test-gate bare filter term | `--filter "~Parser\|~Lexer"`, and the mixed `FullyQualifiedName~Parser\|~Lexer`, match nothing and exit 0 | W/OUT 1.00 both times: the baseline already knows the rule |
| test-gate landing union filter | a landing gate built from the union of each change's filters is not enough | W/OUT 1.00 |
| test-gate CI pending | the status line after a push says "local green; CI pending" | W/OUT matched WITH (1/2 each); Claude already hedges |
| agent-fleet WIP commit, not `git stash` | set WIP aside with a commit, because the stash is shared by linked worktrees | once the grader stopped counting prose warnings, W/OUT was 1.00 across two prompt variants |
| agent-fleet fresh vs resume | a fresh agent from the checkpoint beats resuming a 280-turn transcript | W/OUT 1.00 |
| test-gate battery in a worktree | run the comprehensive battery in its own detached worktree while landings continue | W/OUT 1.00 across two prompt variants (3 runs each): once the prompt mentions landings during the run, the baseline already cuts a `git worktree add` for it |
| agent-fleet no early peek | never read a two-stage fleet's output before it signals completion | W/OUT 1.00 |
| agent-fleet landing batch size | 4–6 clusters per landing (rule retired 2026-10-11: one pull request per branch through a merge queue) | W/OUT 1.00 (the baseline also picks the middle) |
| agent-fleet workflow liveness | judge a background workflow alive by its processes and journal, never by transcript file times | W/OUT 0.83–1.00 across two prompt variants: the baseline already keys a watchdog on live processes and says quiet output is not death. A first grader that forbade the word "transcript" also failed the plugin arm, which names transcript times in order to reject them |
| spec-oracle spec over reference | the golden value is derived from a supplied spec excerpt, not copied from the reference tool | W/OUT 1.00 when the excerpt is in the prompt |
| spec-oracle inherited citation | re-derive a ticket's clause number instead of copying it | W/OUT 1.00 |
| dotnet-engineering AOT no suppression | fix IL2026 with a source-generated `JsonSerializerContext`, never a suppression | W/OUT 1.00 |
| dotnet-engineering benchmark witness | `[GlobalSetup]` checks that both candidates agree, and a baseline is marked | W/OUT 1.00 |
| roslyn-analysis metadata-only inspection | list a DLL's types without `Assembly.LoadFrom` | W/OUT 1.00 (the baseline already uses `MetadataReader`) |
| variant-analysis other arm | after fixing one arm, flag the sibling arm with the same bug | W/OUT 1.00 when the sibling is in view |
| variant-analysis calibrated zero | a post-fix grep for the exact removed text is not evidence | W/OUT 1.00 |
| cross-platform other-OS leg | Windows dev, Linux CI: build and test a clone on the WSL filesystem, targeted tests only | W/OUT 1.00 (3 runs, Opus 5.5 medium, 2026-11-14) |
| cross-platform GIT_DIR export | an exported GIT_DIR redirects tests' scratch repositories into the real one | W/OUT 1.00 (same) |
| cross-platform autocrlf in system config | Git for Windows' system core.autocrlf, invisible to WSL git; eol=lf and renormalize | W/OUT 1.00 (same) |
| cross-platform JVM charset | a JVM tool reads the grammar in the platform charset on the Windows runner; declare -encoding | W/OUT 1.00 (same) |

Two graders were also removed from kept cases because the agent did not produce them reliably: `Hides:` on
silent-failure-hunter, and a `drift test` phrase on type-design-analyzer. An `llm` grader on pr-test-analyzer was
replaced by trace regexes after the default haiku judge passed a baseline answer that its own rubric should have
failed.

One kept grader passes the baseline too: `OTHER-REPO: ALLOWED` in `automating-agent-guardrails-guard-design`. Asked
directly about another repository, Claude scopes the rule correctly, although the baseline builder that was never
asked did not. It stays as a regression guard; the case's delta comes from `ON-ERROR: ALLOW` (W/OUT 0/2: the baseline
fails closed). Likewise `OLD-ENTRY: LEAVE` in `devlog-correction-and-clock` passes the baseline (6/6 over the
authoring run and the final run: Claude already keeps a log append-only) and stays as a regression guard. That case's
delta comes from the clock-read timestamp (W/OUT 0/6: the baseline writes "16:30"). In `devlog-consolidate-brief` the
baseline named open problems in 2 of 6 runs but a not-yet-acted-on list in none. An earlier variant of the
correction case, whose `TIMESTAMP:` line offered "or the command you take it from", passed the baseline 2/2 and was
rewritten. In `devlog-commit-hook` the baseline registered the `if` filter the prompt asked for in 5 of 6 runs and
chose DENY in all 6. A `keeps-reversals` grader on the consolidation case passed the baseline 2/2 and was replaced
by the not-yet-acted-on grader. The four devlog cases cost about $4.40 at 3 runs per arm.
