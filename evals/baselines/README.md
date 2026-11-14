# Baselines

One file per model, effort level and plugin version, written by `python scripts/run_evals.py table` from a run
that recorded its model and effort; the `.json` beside each is what `run_evals.py compare` reads. Compare a
change only with the baseline of the same model and effort.

## The two tiers on the unchanged v1.22.0 skills

| | Opus 5.5 `medium` | Mythos 5.2 `high` |
|---|---|---|
| File | [`opus-5.5-medium-v1.22.0.md`](opus-5.5-medium-v1.22.0.md) | [`mythos-5.2-high-v1.22.0.md`](mythos-5.2-high-v1.22.0.md) |
| List-price cost (CLI) | $22.06 | $83.84 |
| Wall time | 950 s | 2940 s |
| Other models in usage | none | claude-opus-5-5 |
| Mean Δ | +0.68 | +0.66 |

The Mythos figures are the full run ($69.54, 2,173 s) plus the re-run of the two cases it cut off ($14.30, 767 s);
see its file. In the Mythos runs subagents ran on `claude-opus-5-5`, from `CLAUDE_CODE_SUBAGENT_MODEL=opus` in the
operator's user settings. `devlog-commit-hook` scored WITH 0.67 on Mythos with the `devlog` skill loaded in none
of the three runs.

| Case | WITH Opus | W/OUT Opus | Δ Opus | Fired Opus | WITH Mythos | W/OUT Mythos | Δ Mythos | Fired Mythos |
|---|---|---|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.67 | +0.33 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `agent-fleet-file-clusters` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `agent-fleet-finished-work-lands` | 1.00 | 0.75 | +0.25 | 3/3 | 1.00 | 0.75 | +0.25 | 3/3 |
| `agent-fleet-orientation` | 1.00 | 0.00 | +1.00 | 3/3 | 0.67 | 0.00 | +0.67 | 3/3 |
| `agent-fleet-registrar-rerun` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `agent-fleet-reprobe-backlog` | 1.00 | 0.50 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `agent-pr-test-analyzer` | 0.83 | 0.00 | +0.83 | 3/3 | 0.67 | 0.00 | +0.67 | 3/3 |
| `agent-silent-failure-hunter` | 0.83 | 0.50 | +0.33 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `agent-type-design-analyzer` | 0.83 | 0.50 | +0.33 | 3/3 | 0.83 | 0.50 | +0.33 | 3/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 0.50 | +0.50 | 3/3 | 1.00 | 1.00 | +0.00 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `devlog-commit-hook` | 0.00 | 0.00 | +0.00 | 0/3 | 0.67 | 0.00 | +0.67 | 0/3 |
| `devlog-consolidate-brief` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `devlog-insert-entry` | 0.33 | 0.00 | +0.33 | 3/3 | 0.00 | 0.00 | +0.00 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `engineering-standards-explicit-registry` | 1.00 | 0.67 | +0.33 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `engineering-standards-no-fallback` | 1.00 | 0.00 | +1.00 | 3/3 | 0.33 | 0.00 | +0.33 | 3/3 |
| `review-wall-clock-ceiling` | 1.00 | 0.50 | +0.50 | 3/3 | 0.50 | 0.00 | +0.50 | 3/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 0.33 | +0.67 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 |
| `test-gate-conflict-markers-staged` | 1.00 | 0.33 | +0.67 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `test-gate-preexisting-red-blocks-merge` | 0.33 | 0.00 | +0.33 | 1/3 | 1.00 | 0.00 | +1.00 | 3/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | 0.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 |

Δ > 0 on Opus and ≤ 0 on Mythos: `automating-agent-guardrails-guard-design`, `devlog-insert-entry`.
Δ > 0 on Mythos and ≤ 0 on Opus: `devlog-commit-hook`.
Skill or agent not loaded in every WITH run (Fired), Opus: `devlog-commit-hook` 0/3, `test-gate-preexisting-red-blocks-merge` 1/3.
Fired, Mythos: `devlog-commit-hook` 0/3.

## The Phase 3 result: `-c`, the Opus reference from here on

**Opus 5.5 `medium`: [`opus-5.5-medium-update-5.2-c.md`](opus-5.5-medium-update-5.2-c.md)** (and its `.json`) is
the reference for the next phase. It is one full run (35 cases, none cut off, every trace on `claude-opus-5-5`,
$30.00, 1,595 s) on the Phase 3 tree `973f2a9`: the four rewrite branches merged (`p3-guardrails`,
`p3-agent-fleet`, `p3-review-gate`, `p3-engineering`), the integration seams, and the description fixes that the
case-by-case measurement kept (cross-platform, test-gate, agent-fleet, engineering-standards). Mean Δ +0.53,
against +0.47 in `-b`. The Mythos 5.2 `high` reference on the `-b` tree is
[`mythos-5.2-high-update-5.2-b.md`](mythos-5.2-high-update-5.2-b.md) (mean Δ +0.54); the phase's closing Mythos run
on this tree becomes the next one.

`agent-fleet-finished-work-lands` is renamed `merge-queue-landing-finished-work-lands` (the lint keys a case to its
skill by name, and the landing rules moved to `merge-queue-landing`); the `-b` column below is the old name. Its
Fired 0/3 is the unchanged `skill-fired` grader, which still matches `agent-fleet`: the traces show
`merge-queue-landing` loaded in all three runs.

Three runs per arm cannot tell a one-run move (±0.33 on a single-grader case) from noise; the per-case notes are in
the Phase 3 integration report.

| Case | WITH `-b` | Δ `-b` | Fired `-b` | WITH `-c` | W/OUT `-c` | Δ `-c` | Fired `-c` | Δ change |
|---|---|---|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `agent-fleet-brief-limits` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `agent-fleet-file-clusters` | 0.50 | +0.50 | 3/3 | 0.50 | 0.00 | +0.50 | 3/3 | +0.00 |
| `agent-fleet-orientation` | 0.50 | +0.50 | 3/3 | 0.50 | 0.00 | +0.50 | 3/3 | +0.00 |
| `agent-fleet-registrar-rerun` | 0.33 | +0.33 | 1/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.67 |
| `agent-fleet-reprobe-backlog` | 0.50 | +0.00 | 0/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.50 |
| `agent-fleet-stamped-handoff` | 1.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.00 |
| `agent-pr-test-analyzer` | 0.67 | +0.67 | 3/3 | 0.83 | 0.00 | +0.83 | 3/3 | +0.17 |
| `agent-silent-failure-hunter` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `agent-type-design-analyzer` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `architecture-audit-dead-by-grep` | 1.00 | +0.33 | 0/3 | 1.00 | 0.67 | +0.33 | 0/3 | +0.00 |
| `architecture-audit-delete-before-refactor` | 0.67 | +0.00 | 3/3 | 1.00 | 1.00 | +0.00 | 3/3 | +0.00 |
| `architecture-audit-no-alias-rename` | 1.00 | +0.33 | 0/3 | 1.00 | 0.67 | +0.33 | 0/3 | +0.00 |
| `automating-agent-guardrails-guard-design` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | +0.67 | 3/3 | 1.00 | 0.17 | +0.83 | 3/3 | +0.17 |
| `cross-platform-host-only-witness` | 1.00 | +0.67 | 3/3 | 0.67 | 0.00 | +0.67 | 3/3 | -0.00 |
| `cross-platform-per-os-commands` | 0.33 | +0.33 | 0/3 | 0.67 | 0.00 | +0.67 | 0/3 | +0.33 |
| `devlog-commit-hook` | 1.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.00 |
| `devlog-consolidate-brief` | 1.00 | +0.83 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | -0.33 |
| `devlog-correction-and-clock` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `devlog-insert-entry` | 0.33 | +0.33 | 3/3 | 0.00 | 0.00 | +0.00 | 3/3 | -0.33 |
| `dotnet-engineering-single-current-tfm` | 0.67 | +0.67 | 2/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.33 |
| `engineering-standards-explicit-registry` | 1.00 | +0.00 | 0/3 | 1.00 | 1.00 | +0.00 | 0/3 | +0.00 |
| `engineering-standards-no-fallback` | 0.17 | +0.17 | 0/3 | 0.00 | 0.00 | +0.00 | 0/3 | -0.17 |
| `merge-queue-landing-finished-work-lands` | 1.00 | +0.25 | 3/3 | 1.00 | 0.75 | +0.25 | 0/3 | +0.00 |
| `performance-diagnosis-guard-not-clock` | 0.83 | +0.17 | 1/3 | 0.83 | 1.00 | -0.17 | 3/3 | -0.33 |
| `performance-diagnosis-warm-cache-claim` | 0.67 | +0.00 | 0/3 | 0.33 | 0.67 | -0.33 | 0/3 | -0.33 |
| `review-wall-clock-ceiling` | 1.00 | +0.50 | 3/3 | 1.00 | 0.50 | +0.50 | 3/3 | +0.00 |
| `roslyn-analysis-renamed-clones` | 1.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.00 |
| `roslyn-analysis-safe-rewriter` | 1.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.00 |
| `spec-compliance-audit-partial-verdict` | 0.67 | +0.67 | 2/3 | 0.67 | 0.00 | +0.67 | 2/3 | +0.00 |
| `spec-oracle-render-the-diagram` | 1.00 | +0.50 | 3/3 | 1.00 | 0.67 | +0.33 | 3/3 | -0.17 |
| `test-gate-conflict-markers-staged` | 0.17 | -0.50 | 0/3 | 1.00 | 0.17 | +0.83 | 3/3 | +1.33 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | +1.00 | 3/3 | 1.00 | 0.00 | +1.00 | 3/3 | +0.00 |
| `variant-analysis-latent-not-cleared` | 0.67 | +0.50 | 2/3 | 1.00 | 0.17 | +0.83 | 3/3 | +0.33 |

## The reference for Phase 3 (`-b`)

`-c` above replaces it. **Opus 5.5 `medium`, Phase 3's reference: [`opus-5.5-medium-update-5.2-b.md`](opus-5.5-medium-update-5.2-b.md)** (and its `.json`), measured
on the `update-5.2` tree with the skills of `a09a989`: v1.22.0 with the validation labels removed, the twelve
contradiction fixes, and the `devlog` and `test-gate` descriptions rewritten. Compare the next phase's Opus runs
with it (`run_evals.py compare evals/baselines/opus-5.5-medium-update-5.2-b.json <result>`). It is one full run of
the suite as it stood at `7d07908`, with the four cases written after that run each measured alone on the same
skills tree and merged in (`merge --add-new`; its header names them), and the three candidates that run measured
and the suite then dropped left out (`table --drop-removed`). Its cost and time include those candidates.
The Mythos 5.2 `high` reference for this tree is [`mythos-5.2-high-update-5.2-b.md`](mythos-5.2-high-update-5.2-b.md);
`mythos-5.2-high-v1.22.0` measures the v1.22.0 skills and the earlier prompts, and is not comparable with `-b`.

## A new series starts at `7d07908`

These 23 cases were retuned at `7d07908` (`RETUNE.md`): the prompt no longer names the skill, or no longer caps the
answer, or both. Their scores before that commit, in `opus-5.5-medium-v1.22.0`, `opus-5.5-medium-update-5.2-a` and
`mythos-5.2-high-v1.22.0`, measure different prompts and are not comparable with `-b` or later. The table gives
both for the record, not as a change.

| Case | WITH `-a` (old prompt) | Δ `-a` | Fired `-a` | WITH `-b` (retuned) | Δ `-b` | Fired `-b` |
|---|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `agent-type-design-analyzer` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `agent-fleet-file-clusters` | 1.00 | +1.00 | 3/3 | 0.50 | +0.50 | 3/3 |
| `agent-fleet-finished-work-lands` | 0.92 | +0.17 | 3/3 | 1.00 | +0.25 | 3/3 |
| `agent-fleet-orientation` | 1.00 | +1.00 | 3/3 | 0.50 | +0.50 | 3/3 |
| `agent-fleet-registrar-rerun` | 1.00 | +1.00 | 3/3 | 0.33 | +0.33 | 1/3 |
| `agent-fleet-reprobe-backlog` | 1.00 | +0.50 | 3/3 | 0.50 | +0.00 | 0/3 |
| `agent-fleet-stamped-handoff` | 1.00 | +1.00 | 3/3 | 1.00 | +1.00 | 3/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | +1.00 | 3/3 | 1.00 | +0.67 | 3/3 |
| `devlog-commit-hook` | 0.00 | +0.00 | 0/3 | 1.00 | +1.00 | 3/3 |
| `devlog-consolidate-brief` | 1.00 | +0.83 | 3/3 | 1.00 | +0.83 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `devlog-insert-entry` | 0.00 | +0.00 | 3/3 | 0.33 | +0.33 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | +1.00 | 3/3 | 0.67 | +0.67 | 2/3 |
| `engineering-standards-explicit-registry` | 1.00 | +0.50 | 3/3 | 1.00 | +0.00 | 0/3 |
| `engineering-standards-no-fallback` | 0.67 | +0.67 | 3/3 | 0.17 | +0.17 | 0/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | +1.00 | 3/3 | 0.67 | +0.67 | 2/3 |
| `spec-oracle-render-the-diagram` | 1.00 | +0.50 | 3/3 | 1.00 | +0.50 | 3/3 |
| `test-gate-conflict-markers-staged` | 0.83 | +0.50 | 3/3 | 0.17 | -0.50 | 0/3 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | +1.00 | 2/3 | 1.00 | +1.00 | 3/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | +1.00 | 3/3 | 0.67 | +0.50 | 2/3 |

Mean Δ over these 23: +0.66 with the old prompts, +0.47 retuned.
In `-b`, the skill loaded in fewer than three of the three WITH runs for: `agent-fleet-registrar-rerun` 1/3, `agent-fleet-reprobe-backlog` 0/3, `dotnet-engineering-single-current-tfm` 2/3, `engineering-standards-explicit-registry` 0/3, `engineering-standards-no-fallback` 0/3, `spec-compliance-audit-partial-verdict` 2/3, `test-gate-conflict-markers-staged` 0/3, `variant-analysis-latent-not-cleared` 2/3.

The seven cases new at this point (no earlier series):

| Case | WITH | W/OUT | Δ | Fired |
|---|---|---|---|---|
| `architecture-audit-no-alias-rename` | 1.00 | 0.67 | +0.33 | 0/3 |
| `performance-diagnosis-guard-not-clock` | 0.83 | 0.67 | +0.17 | 1/3 |
| `performance-diagnosis-warm-cache-claim` | 0.67 | 0.67 | +0.00 | 0/3 |
| `architecture-audit-dead-by-grep` | 1.00 | 0.67 | +0.33 | 0/3 |
| `architecture-audit-delete-before-refactor` | 0.67 | 0.67 | +0.00 | 3/3 |
| `cross-platform-per-os-commands` | 0.33 | 0.00 | +0.33 | 0/3 |
| `cross-platform-host-only-witness` | 1.00 | 0.33 | +0.67 | 3/3 |

## Three skills retired after the `-c` run

`engineering-standards`, `performance-diagnosis` and `architecture-audit`, and their seven cases, were removed after
`opus-5.5-medium-update-5.2-c` and `mythos-5.2-high-update-5.2-b`, because neither tier showed a gain attributable
to the skill. `engineering-standards` (two cases): mean Δ +0.00 on Opus and +0.08 on Mythos, and the skill loaded in
0 of 6 WITH runs on both tiers after two description rewrites. `performance-diagnosis` (two cases): Δ −0.25 on Opus
(WITH 0.58, W/OUT 0.83) and +0.00 on Mythos. `architecture-audit` (three cases): Δ +0.22 on Opus and +0.11 on Mythos,
but the cases that gained loaded the skill in 0 of 3 runs, and the one case where it loaded scored the same with and
without it. Their rows above and the JSON results stay as the record.
