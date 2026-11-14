# Eval result: claude-mythos-5-2 at effort high

- Model: `claude-mythos-5-2` (verified from every run's trace); effort: `high` (set through CLAUDE_CODE_EFFORT_LEVEL)
- CLI: 2.1.325; plugin: 1.22.0; tree: `ca171852a6`
- Started 2026-11-14T19:50:39.751Z; 3280 s; $104.62 at list price as the CLI reports it; raw result `evals/results/2026-11-14T19-50-39Z-claude-mythos-5-2-high/` (git-ignored)
- Other models in the runs' usage: claude-opus-5-5
- Model settings in the operator's user settings `env`, which every child loads: `CLAUDE_CODE_SUBAGENT_MODEL=opus`
- Runs cut off by a turn cap or timeout: 0

| Case | WITH | W/OUT | Δ | Runs/arm | Fired |
|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.67 | +0.33 | 3 | 3/3 |
| `agent-fleet-file-clusters` | 0.83 | 0.00 | +0.83 | 3 | 3/3 |
| `agent-fleet-finished-work-lands` | 1.00 | 0.75 | +0.25 | 3 | 3/3 |
| `agent-fleet-orientation` | 0.33 | 0.00 | +0.33 | 3 | 2/3 |
| `agent-fleet-registrar-rerun` | 0.67 | 0.00 | +0.67 | 3 | 2/3 |
| `agent-fleet-reprobe-backlog` | 0.50 | 0.50 | +0.00 | 3 | 0/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-pr-test-analyzer` | 0.83 | 0.00 | +0.83 | 3 | 3/3 |
| `agent-silent-failure-hunter` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-type-design-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `architecture-audit-dead-by-grep` | 1.00 | 0.67 | +0.33 | 3 | 0/3 |
| `architecture-audit-delete-before-refactor` | 1.00 | 1.00 | +0.00 | 3 | 3/3 |
| `architecture-audit-no-alias-rename` | 1.00 | 1.00 | +0.00 | 3 | 0/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 0.83 | +0.17 | 3 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `cross-platform-host-only-witness` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `cross-platform-per-os-commands` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-commit-hook` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-consolidate-brief` | 1.00 | 0.33 | +0.67 | 3 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-insert-entry` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `engineering-standards-explicit-registry` | 1.00 | 1.00 | +0.00 | 3 | 0/3 |
| `engineering-standards-no-fallback` | 0.17 | 0.00 | +0.17 | 3 | 0/3 |
| `performance-diagnosis-guard-not-clock` | 1.00 | 1.00 | +0.00 | 3 | 3/3 |
| `performance-diagnosis-warm-cache-claim` | 1.00 | 1.00 | +0.00 | 3 | 0/3 |
| `review-wall-clock-ceiling` | 0.83 | 0.17 | +0.67 | 3 | 3/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 1.00 | +0.00 | 3 | 3/3 |
| `test-gate-conflict-markers-staged` | 0.00 | 0.00 | +0.00 | 3 | 0/3 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |

Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator).

Mean Δ over 35 cases: +0.54.
