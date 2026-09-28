# Regression evals

Behavioral regression tests for the `brent-tools` plugin, run with
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals). Each case proves that one skill or agent
**changes what Claude does**. Every case runs twice: once with the plugin loaded (WITH) and once with no plugin
(W/OUT). A case is only kept if the plugin arm beats the no-plugin arm. If the plugin arm does no better, the case
tests Claude rather than the skill, and so it can't detect an edit that breaks the skill.

## What it covers

Twenty-seven cases: one to six for each of the twelve skills and one for each of the four agents. Each case is a small
scenario, written inline in its `prompt.md`, that can only be handled correctly by following that skill's rule.
The scores below come from the last full run (3 runs per arm, 2026-09-25), except eleven cases added later and
measured on their own: `agent-fleet-reprobe-backlog`, `agent-fleet-registrar-rerun` and
`test-gate-conflict-markers-staged` (3 runs per arm, 2026-09-28), `automating-agent-guardrails-guard-design`
(2 runs per arm), `agent-fleet-file-clusters` and `agent-fleet-orientation` (3 runs per arm, 2026-09-27), `agent-fleet-stamped-handoff` (3 runs per arm,
2026-09-28), and the four `devlog-*` cases (3 runs per arm, 2026-09-28).

| Case | Covers | The rule it checks | WITH | W/OUT |
|---|---|---|---|---|
| `engineering-standards-no-fallback` | engineering-standards | Refuses the requested "token lookup, else match by name/signature" fallback, fixes the root cause, and sweeps for the same bug elsewhere | 0.83 | 0.00 |
| `engineering-standards-explicit-registry` | engineering-standards | Builds the registry explicitly in a trimmed app, with no reflection discovery, and adds a drift test without being asked | 0.83 | 0.50 |
| `review-wall-clock-ceiling` | review | Reports a `Stopwatch` ceiling test as a finding with a `Scenario:` and a deterministic replacement for it | 1.00 | 0.50 |
| `variant-analysis-latent-not-cleared` | variant-analysis | Reports a variant that nothing calls as *latent*, not cleared, and records the query calibration | 1.00 | 0.00 |
| `spec-oracle-render-the-diagram` | spec-oracle | Settles a required-vs-optional keyword by rendering the printed page, where underlining decides, instead of trusting the extracted text | 1.00 | 0.33 |
| `spec-compliance-audit-partial-verdict` | spec-compliance-audit | A rule that holds on one path and fails on another is `PARTIAL`, never `CONFORMS` | 1.00 | 0.00 |
| `test-gate-conflict-markers-staged` | test-gate | Between `git add` and `git commit`, checks what is STAGED (`git grep --cached` for the marker lines) and reads the OUTPUT of `git diff --cached --check` for "conflict marker" instead of its exit code | 1.00 | 0.17 |
| `test-gate-preexisting-red-blocks-merge` | test-gate | A red that already existed before the batch is attributed and filed, but it still blocks the merge | 1.00 | 0.00 |
| `dotnet-engineering-single-current-tfm` | dotnet-engineering | Targets one current TFM, with no `netstandard2.0` and no multi-targeting when no consumer is named | 1.00 | 0.00 |
| `roslyn-analysis-renamed-clones` | roslyn-analysis | Uses the bundled type-2 clone detector (`detect-clones.cs`) to find renamed copies | 1.00 | 0.00 |
| `roslyn-analysis-safe-rewriter` | roslyn-analysis | Uses the bundled `rewrite-template.cs` harness (dry run by default) for a mechanical rewrite | 1.00 | 0.00 |
| `agent-fleet-brief-limits` | agent-fleet | Uses the measured turn cap (~150–160) and a graceful STOP file in a dispatch brief | 1.00 | 0.50 |
| `agent-fleet-file-clusters` | agent-fleet | Assigns defects to implementer slots by COMPUTED per-file clusters ranked by summed harm, naming the bundled `fix_clusters.py` | 1.00 | 0.00 |
| `agent-fleet-orientation` | agent-fleet | Tells implementers to orient with the bundled `orient.py --notes …` (outline, covering tests, what earlier fixes learned) before reading source | 1.00 | 0.00 |
| `agent-fleet-stamped-handoff` | agent-fleet | Stamps the handoff summary with the commit it describes (`STATUS-AT: <sha>`) and has a resuming or successor agent run the bundled `status_delta.py` to read only the commits the summary does not cover | 1.00 | 0.00 |
| `agent-fleet-reprobe-backlog` | agent-fleet | The implementer re-runs each stale item's repro first; one that no longer reproduces is discharged with evidence (the commit it ran on) and goes to a refuter | 1.00 | 0.50 |
| `agent-fleet-registrar-rerun` | agent-fleet | The agent that files leads runs each lead's given repro once on its own build before filing (no fresh probe when a repro exists) and verifies quoted citations at their source | 1.00 | 0.00 |
| `claude-cloud-sessions-multi-repo-hooks` | claude-cloud-sessions | Explains that multi-repo sessions start in `/home/user` and load no repo hooks, and fixes it with a user-level hook shim | 1.00 | 0.00 |
| `agent-pr-test-analyzer` | pr-test-analyzer | Checks determinism: names a work-count or growth-ratio replacement for a Stopwatch ceiling (`Check:` findings) | 1.00 | 0.00 |
| `agent-silent-failure-hunter` | silent-failure-hunter | Ranks the silent default price above the crash; findings carry `Harm: silent wrong answer` | 1.00 | 0.50 |
| `agent-type-design-analyzer` | type-design-analyzer | Replaces the kind enum with its per-kind fields by a closed hierarchy; findings carry a `Smell:` classification | 0.83 | 0.50 |
| `agent-comment-analyzer` | comment-analyzer | Rejects a citation that answers a different question and finds the governing clause; findings carry `Scenario:`/`Evidence:` | 1.00 | 0.50 |
| `devlog-correction-and-clock` | devlog | Records an overturned finding as a NEW entry (`OLD-ENTRY: LEAVE`, against a teammate's "fix it in place") and takes the header time from the clock (`date`), not from "around 4:30" | 1.00 | 0.50 |
| `devlog-commit-hook` | devlog | Registers the missing-entry commit hook with NO `if` filter (which misses `git add -A && git commit`), although the prompt asks for one, and has it ASK rather than deny | 1.00 | 0.00 |
| `devlog-insert-entry` | devlog | Adds an entry to a CRLF, newest-first log with the bundled `devlog.py new` instead of a hand-written splice | 1.00 | 0.00 |
| `devlog-consolidate-brief` | devlog | A brief to consolidate the log into learnings closes with an open-problems list and a not-yet-acted-on list | 1.00 | 0.33 |
| `automating-agent-guardrails-guard-design` | automating-agent-guardrails | A guard hook for "no stash / land main only via the script" fails OPEN on its own errors (`ON-ERROR: ALLOW`) and scopes the push rule to this repository (`OTHER-REPO: ALLOWED`) | 1.00 | 0.50 |

The WITH score is the mean over 3 runs of the fraction of scored graders that passed. W/OUT is the same score with
no plugin loaded.

## How to run it

From the repository root. The suite uses only read-only tools, so it needs no `--allow-tools` or sandbox and runs
on native Windows.

```
claude plugin eval . -j 4 --no-publish --threshold 0
```

- `-j 4` runs four children at once. `--no-publish` keeps the HTML report local, under `evals/results/<timestamp>/`,
  which is gitignored.
- `--threshold 0` stops the exit code from reflecting the WITH score, because the Δ column is the verdict here (see
  below). Drop it if you want exit 1 whenever a case's WITH score falls below 1.0.
- To iterate on one case cheaply: `claude plugin eval . --case <name> --runs 1 -j 2 --no-publish`. A single run is
  noisy, so confirm a change at the default of 3 runs.
- The first run in a directory asks you to trust it. Add `--trust-plugin` for unattended runs.
- Cost: a full run (16 cases × 3 runs × 2 arms) took about 8 minutes and about **$10** at list price (reported by
  the CLI). Agent cases cost the most, about $0.15 per with-arm run.

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
- **Triggering.** Seven skill cases name the skill ("Use the `X` skill for this"):
  `engineering-standards`, `variant-analysis`, `spec-oracle`, `spec-compliance-audit`, `dotnet-engineering` and
  `agent-fleet`. On natural phrasing those skills fired only some of the time, and a run where the skill does not
  fire measures nothing. `test-gate-conflict-markers-staged` names `test-gate` too: on natural phrasing it did not
  fire in any of 3 runs. The rest use natural phrasing and fired in every run: review, the other test-gate case, both roslyn
  cases, cloud sessions, agent guardrails, and the four agent cases ("use a specialist … reviewer if you have one"). Those also guard
  each skill's `description`. The names `engineering-standards` and `variant-analysis` hint at the answer a little,
  which makes the baseline those two cases must beat harder, not easier.
- **Graders.** Most graders are deterministic regexes over the final message, often on a forced last line such as
  `MERGE: NO`. `llm` graders are used only where no deterministic signal exists (refusing a fallback, keeping a
  runtime registry reflection-free), and their rubrics state concrete PASS and FAIL conditions.
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
   `claude plugin eval . --case <name> --runs 3 -j 4 --no-publish`. Keep the case only if WITH clearly beats
   W/OUT. If the baseline passes as often as the plugin, rewrite the case around what Claude does *not* do unaided,
   or drop it and record why below.
3. **Run the full suite before merging a skill edit,** and compare each case's Δ with the table above. A Δ that
   falls toward 0 means the edit weakened the skill.
4. Update the table above when the numbers move.

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
| agent-fleet landing batch size | 4–6 clusters per landing | W/OUT 1.00 (the baseline also picks the middle) |
| agent-fleet workflow liveness | judge a background workflow alive by its processes and journal, never by transcript file times | W/OUT 0.83–1.00 across two prompt variants: the baseline already keys a watchdog on live processes and says quiet output is not death. A first grader that forbade the word "transcript" also failed the plugin arm, which names transcript times in order to reject them |
| spec-oracle spec over reference | the golden value is derived from a supplied spec excerpt, not copied from the reference tool | W/OUT 1.00 when the excerpt is in the prompt |
| spec-oracle inherited citation | re-derive a ticket's clause number instead of copying it | W/OUT 1.00 |
| engineering-standards complete, not test-scoped | implement the whole documented format, not only the case the failing test covers | W/OUT 1.00 |
| engineering-standards no known limitation | a data-loss bug is a defect, not a "known limitation" | W/OUT 1.00 |
| dotnet-engineering AOT no suppression | fix IL2026 with a source-generated `JsonSerializerContext`, never a suppression | W/OUT 1.00 |
| dotnet-engineering benchmark witness | `[GlobalSetup]` checks that both candidates agree, and a baseline is marked | W/OUT 1.00 |
| roslyn-analysis metadata-only inspection | list a DLL's types without `Assembly.LoadFrom` | W/OUT 1.00 (the baseline already uses `MetadataReader`) |
| variant-analysis other arm | after fixing one arm, flag the sibling arm with the same bug | W/OUT 1.00 when the sibling is in view |
| variant-analysis calibrated zero | a post-fix grep for the exact removed text is not evidence | W/OUT 1.00 |

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
