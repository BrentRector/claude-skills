# Eval result: claude-opus-5-5 at effort medium

- Model: `claude-opus-5-5` (verified from every run's trace); effort: `medium` (set through CLAUDE_CODE_EFFORT_LEVEL)
- CLI: 2.1.325; plugin: 1.22.0; tree: `7483c3849b`
- Started 2026-11-14T18:34:11.881Z; 906 s; $22.28 at list price as the CLI reports it; raw result `evals/results/2026-11-14T18-34-11Z-claude-opus-5-5-medium/` (git-ignored)
- Other models in the runs' usage: none
- Model settings in the operator's user settings `env`, which every child loads: `CLAUDE_CODE_SUBAGENT_MODEL=opus`
- Runs cut off by a turn cap or timeout: 0

| Case | WITH | W/OUT | Δ | Runs/arm | Fired |
|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-file-clusters` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-finished-work-lands` | 0.92 | 0.75 | +0.17 | 3 | 3/3 |
| `agent-fleet-orientation` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-registrar-rerun` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-reprobe-backlog` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-pr-test-analyzer` | 0.67 | 0.00 | +0.67 | 3 | 3/3 |
| `agent-silent-failure-hunter` | 0.83 | 0.50 | +0.33 | 3 | 3/3 |
| `agent-type-design-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-commit-hook` | 0.00 | 0.00 | +0.00 | 3 | 0/3 |
| `devlog-consolidate-brief` | 1.00 | 0.17 | +0.83 | 3 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-insert-entry` | 0.00 | 0.00 | +0.00 | 3 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `engineering-standards-explicit-registry` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `engineering-standards-no-fallback` | 0.67 | 0.00 | +0.67 | 3 | 3/3 |
| `review-wall-clock-ceiling` | 0.83 | 0.33 | +0.50 | 3 | 2/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `test-gate-conflict-markers-staged` | 0.83 | 0.33 | +0.50 | 3 | 3/3 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | 0.00 | +1.00 | 3 | 2/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |

Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator).

Mean Δ over 28 cases: +0.67.

## Against `opus-5.5-medium-v1.22.0` (written by hand, 2026-11-14)

Tree `7483c38` = v1.22.0 + the evals work + `update-5.2-labels` (validation labels removed) + `update-5.2-fixes`
(twelve contradiction fixes); same model, effort, CLI (2.1.325) and runs per arm (3) as the baseline. Command:
`python scripts/run_evals.py run --model claude-opus-5-5 --effort medium -j 4`, then
`python scripts/run_evals.py compare evals/baselines/opus-5.5-medium-v1.22.0.json evals/results/2026-11-14T18-34-11Z-claude-opus-5-5-medium`.
Mean Δ +0.68 → +0.67. 16 of 28 cases are unchanged. "Runs that changed" is the change in the arm's summed
per-run scores: 1 means one run of three went from passing to failing (or the reverse), 0.5 half a run's graders.

| Case | WITH before → after | Δ before → after | Change in Δ | Runs that changed (WITH, W/OUT) | Reading |
|---|---|---|---|---|---|
| `agent-fleet-brief-limits` | 1.00 → 1.00 | +0.33 → +0.50 | +0.17 | 0, 0.5 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `agent-fleet-finished-work-lands` | 1.00 → 0.92 | +0.25 → +0.17 | -0.08 | 0.25, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `agent-pr-test-analyzer` | 0.83 → 0.67 | +0.83 → +0.67 | -0.17 | 0.5, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `agent-type-design-analyzer` | 0.83 → 1.00 | +0.33 → +0.50 | +0.17 | 0.5, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `devlog-consolidate-brief` | 1.00 → 1.00 | +1.00 → +0.83 | -0.17 | 0, 0.5 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `devlog-insert-entry` | 0.33 → 0.00 | +0.33 → +0.00 | -0.33 | 1, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `engineering-standards-explicit-registry` | 1.00 → 1.00 | +0.33 → +0.50 | +0.17 | 0, 0.5 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `engineering-standards-no-fallback` | 1.00 → 0.67 | +1.00 → +0.67 | -0.33 | 1, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `review-wall-clock-ceiling` | 1.00 → 0.83 | +0.50 → +0.50 | +0.00 | 0.5, 0.5 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `spec-oracle-render-the-diagram` | 1.00 → 1.00 | +0.67 → +0.50 | -0.17 | 0, 0.5 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `test-gate-conflict-markers-staged` | 1.00 → 0.83 | +0.67 → +0.50 | -0.17 | 0.5, 0 | within one run of three: not distinguishable from noise at 3 runs per arm |
| `test-gate-preexisting-red-blocks-merge` | 0.33 → 1.00 | +0.33 → +1.00 | +0.67 | 2, 0 | 2 runs' worth: larger than one run, still only 3 runs per arm |

Only `test-gate-preexisting-red-blocks-merge` moved by more than one run (WITH 1 of 3 → 3 of 3). Its skill loaded
in 2 of 3 WITH runs here against 1 of 3 in the baseline, and one passing run did not load it, so the change is
not attributable to the skill text at 3 runs per arm. `devlog-commit-hook` still loads its skill in 0 of 3 runs.
Quota: the operator's weekly quota meter read ≈ 10.03 % before (18:34 UTC) and ≈ 11.0 % after (18:49 UTC); $22.28 at list
price, 906 s.
