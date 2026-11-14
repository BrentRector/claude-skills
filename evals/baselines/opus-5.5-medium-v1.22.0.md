# Eval result: claude-opus-5-5 at effort medium

- Model: `claude-opus-5-5` (verified from every run's trace); effort: `medium` (set through CLAUDE_CODE_EFFORT_LEVEL)
- CLI: 2.1.325; plugin: 1.22.0; tree: `dbe4df9d52`
- Started 2026-11-14T17:18:35.644Z; 950 s; $22.06 at list price as the CLI reports it; raw result `evals/results/2026-11-14T17-18-34Z-claude-opus-5-5-medium/` (git-ignored)
- Other models in the runs' usage: none
- Runs cut off by a turn cap or timeout: 0

| Case | WITH | W/OUT | Δ | Runs/arm | Fired |
|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.67 | +0.33 | 3 | 3/3 |
| `agent-fleet-file-clusters` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-finished-work-lands` | 1.00 | 0.75 | +0.25 | 3 | 3/3 |
| `agent-fleet-orientation` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-registrar-rerun` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-reprobe-backlog` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-pr-test-analyzer` | 0.83 | 0.00 | +0.83 | 3 | 3/3 |
| `agent-silent-failure-hunter` | 0.83 | 0.50 | +0.33 | 3 | 3/3 |
| `agent-type-design-analyzer` | 0.83 | 0.50 | +0.33 | 3 | 3/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-commit-hook` | 0.00 | 0.00 | +0.00 | 3 | 0/3 |
| `devlog-consolidate-brief` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-insert-entry` | 0.33 | 0.00 | +0.33 | 3 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `engineering-standards-explicit-registry` | 1.00 | 0.67 | +0.33 | 3 | 3/3 |
| `engineering-standards-no-fallback` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `review-wall-clock-ceiling` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 0.33 | +0.67 | 3 | 3/3 |
| `test-gate-conflict-markers-staged` | 1.00 | 0.33 | +0.67 | 3 | 3/3 |
| `test-gate-preexisting-red-blocks-merge` | 0.33 | 0.00 | +0.33 | 3 | 1/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |

Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator).

Mean Δ over 28 cases: +0.68.

## Notes on this run (written by hand, 2026-11-14)

- **Command:** `python scripts/run_evals.py run --model claude-opus-5-5 --effort medium -j 4`, from the repository
  root, on branch `update-5.2-evals` at `dbe4df9`: the skills and agents are unchanged from v1.22.0 (`0b6e663`); the
  cases carry the re-sized `max_turns` and `timeout_seconds` of `dbe4df9`. 28 cases × 3 runs × 2 arms = 168 runs,
  every run's model read from its trace as `claude-opus-5-5`, none cut off. The largest use of a limit was 8 of 16
  turns (`devlog-commit-hook`) and 74 of 360 s.
- **Quota cost:** the operator's weekly quota meter read
  ≈ 1.44 % before the run (17:18 UTC) and ≈ 2.02 % after it (17:35 UTC): about **0.6 points** of the weekly
  quota. The meter anchors on the status line's whole-percent reading plus telemetry, so the figure is good to
  about ±0.5 points; the list-price cost the CLI reports is $22.06.
- **Skill did not load:** `devlog-commit-hook` (0 of 3 WITH runs called the `devlog` skill; WITH 0.00) and
  `test-gate-preexisting-red-blocks-merge` (1 of 3; WITH 0.33). Both use natural phrasing. On this model those
  prompts no longer trigger their skill, which is a finding against the two skills' `description`s, not a case to
  drop. `devlog-insert-entry` fired 3 of 3 but scored WITH 0.33: the answer did not name `devlog.py`.
- **Against the last full run before this one** (2026-10-19, v1.22.0 tree before its final eval rewrite, model not
  recorded, so not comparable by `compare`): `test-gate-preexisting-red-blocks-merge` WITH 1.00 → 0.33 and
  `devlog-commit-hook` 0.50 → 0.00 (the trigger misses above); `engineering-standards-no-fallback` 0.67 → 1.00,
  `spec-oracle-render-the-diagram` 0.83 → 1.00, `agent-pr-test-analyzer` 0.67 → 0.83;
  `agent-silent-failure-hunter` and `agent-type-design-analyzer` 1.00 → 0.83 (one run each missing its finding
  label in the trace). `agent-fleet-finished-work-lands` W/OUT 1.00 → 0.75 is the rewritten case, as measured on
  its own on 2026-10-18.
