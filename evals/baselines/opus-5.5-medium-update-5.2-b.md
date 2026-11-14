# Eval result: claude-opus-5-5 at effort medium

- Model: `claude-opus-5-5` (verified from every run's trace); effort: `medium` (set through CLAUDE_CODE_EFFORT_LEVEL)
- CLI: 2.1.325; plugin: 1.22.0; tree: `7d07908e43`
- Started 2026-11-14T19:11:08.803Z; 1767 s; $31.09 at list price as the CLI reports it; raw result `evals/results/2026-11-14-claude-opus-5-5-medium-update-5.2-b/` (git-ignored)
- Other models in the runs' usage: none
- Model settings in the operator's user settings `env`, which every child loads: `CLAUDE_CODE_SUBAGENT_MODEL=opus`
- Runs cut off by a turn cap or timeout: 0
- Measured in this run but removed from the suite, so not in this table: `architecture-audit-neutrality-oracle`, `architecture-audit-no-fix-in-wave`, `cross-platform-other-os-leg`
- Case `architecture-audit-dead-by-grep` added from its own run in `evals/results/2026-11-14T19-43-50Z-claude-opus-5-5-medium/` (tree `7d07908e43`, same skills tree)
- Case `architecture-audit-delete-before-refactor` added from its own run in `evals/results/2026-11-14T19-45-03Z-claude-opus-5-5-medium/` (tree `7d07908e43`, same skills tree)
- Case `cross-platform-per-os-commands` added from its own run in `evals/results/2026-11-14T19-46-17Z-claude-opus-5-5-medium/` (tree `7d07908e43`, same skills tree)
- Case `cross-platform-host-only-witness` added from its own run in `evals/results/2026-11-14T19-47-01Z-claude-opus-5-5-medium/` (tree `7d07908e43`, same skills tree)

| Case | WITH | W/OUT | Δ | Runs/arm | Fired |
|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-file-clusters` | 0.50 | 0.00 | +0.50 | 3 | 3/3 |
| `agent-fleet-finished-work-lands` | 1.00 | 0.75 | +0.25 | 3 | 3/3 |
| `agent-fleet-orientation` | 0.50 | 0.00 | +0.50 | 3 | 3/3 |
| `agent-fleet-registrar-rerun` | 0.33 | 0.00 | +0.33 | 3 | 1/3 |
| `agent-fleet-reprobe-backlog` | 0.50 | 0.50 | +0.00 | 3 | 0/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-pr-test-analyzer` | 0.67 | 0.00 | +0.67 | 3 | 3/3 |
| `agent-silent-failure-hunter` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-type-design-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `architecture-audit-no-alias-rename` | 1.00 | 0.67 | +0.33 | 3 | 0/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.33 | +0.67 | 3 | 3/3 |
| `devlog-commit-hook` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-consolidate-brief` | 1.00 | 0.17 | +0.83 | 3 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-insert-entry` | 0.33 | 0.00 | +0.33 | 3 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 0.67 | 0.00 | +0.67 | 3 | 2/3 |
| `engineering-standards-explicit-registry` | 1.00 | 1.00 | +0.00 | 3 | 0/3 |
| `engineering-standards-no-fallback` | 0.17 | 0.00 | +0.17 | 3 | 0/3 |
| `performance-diagnosis-guard-not-clock` | 0.83 | 0.67 | +0.17 | 3 | 1/3 |
| `performance-diagnosis-warm-cache-claim` | 0.67 | 0.67 | +0.00 | 3 | 0/3 |
| `review-wall-clock-ceiling` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 0.67 | 0.00 | +0.67 | 3 | 2/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `test-gate-conflict-markers-staged` | 0.17 | 0.67 | -0.50 | 3 | 0/3 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `variant-analysis-latent-not-cleared` | 0.67 | 0.17 | +0.50 | 3 | 2/3 |
| `architecture-audit-dead-by-grep` | 1.00 | 0.67 | +0.33 | 3 | 0/3 |
| `architecture-audit-delete-before-refactor` | 0.67 | 0.67 | +0.00 | 3 | 3/3 |
| `cross-platform-per-os-commands` | 0.33 | 0.00 | +0.33 | 3 | 0/3 |
| `cross-platform-host-only-witness` | 1.00 | 0.33 | +0.67 | 3 | 3/3 |

Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator).

Mean Δ over 35 cases: +0.47.

## Notes (written by hand, 2026-11-14)

- **Why a merge and not a second full run:** the full run (`2026-11-14T19-11-08Z`, 1,543 s, $28.54) measured the
  final skills tree (`a09a989`; no skill file changed after it) and every retuned prompt. After it, only eval cases
  changed: four new ones were written and each run alone on the same skills tree, three that run measured were
  dropped, and three lost to a YAML error were re-run alone and dropped. Re-running the unchanged cases would
  measure the same inputs again.
- **This is the first measurement of the retuned prompts** (a new series; see `README.md`). Mean Δ over the 35 cases
  is +0.47. With the skill no longer named, eight retuned cases load their skill in fewer than 3 of 3 WITH runs, and
  so do five of the seven new cases. Those are findings against the skills' descriptions, not tuned here.
- **`test-gate-conflict-markers-staged`:** WITH 0.17, W/OUT 0.67, Δ −0.50, with `test-gate` loaded in none of the
  WITH runs. The plugin arm did worse than no plugin without loading the skill the case covers.
- **Trigger fixes in this tree:** `devlog-commit-hook` (devlog loaded 3/3, WITH 1.00) and
  `test-gate-preexisting-red-blocks-merge` (test-gate 3/3, WITH 1.00).
