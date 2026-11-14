# Eval result: claude-mythos-5-2 at effort high

- Model: `claude-mythos-5-2` (verified from every run's trace); effort: `high` (set through CLAUDE_CODE_EFFORT_LEVEL)
- CLI: 2.1.325; plugin: 1.22.0; tree: `755cce3c58`
- Started 2026-11-14T17:38:14.766Z; 2940 s; $83.84 at list price as the CLI reports it; raw result `evals/results/2026-11-14-claude-mythos-5-2-high-merged/` (git-ignored)
- Other models in the runs' usage: claude-opus-5-5
- Model settings in the operator's user settings `env`, which every child loads: `CLAUDE_CODE_SUBAGENT_MODEL=opus`
- Runs cut off by a turn cap or timeout: 0
- Case `review-wall-clock-ceiling` replaced by its re-run in `evals/results/2026-11-14T18-18-27Z-claude-mythos-5-2-high/` (tree `a1d0b1a390`, limits 16 turns / 660 s; the replaced runs had 3 cut off at 10 turns / 300 s)
- Case `devlog-insert-entry` replaced by its re-run in `evals/results/2026-11-14T18-26-34Z-claude-mythos-5-2-high/` (tree `a1d0b1a390`, limits 14 turns / 540 s; the replaced runs had 2 cut off at 12 turns / 240 s)

| Case | WITH | W/OUT | Δ | Runs/arm | Fired |
|---|---|---|---|---|---|
| `agent-comment-analyzer` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-brief-limits` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-file-clusters` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-finished-work-lands` | 1.00 | 0.75 | +0.25 | 3 | 3/3 |
| `agent-fleet-orientation` | 0.67 | 0.00 | +0.67 | 3 | 3/3 |
| `agent-fleet-registrar-rerun` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-fleet-reprobe-backlog` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-fleet-stamped-handoff` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `agent-pr-test-analyzer` | 0.67 | 0.00 | +0.67 | 3 | 3/3 |
| `agent-silent-failure-hunter` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `agent-type-design-analyzer` | 0.83 | 0.50 | +0.33 | 3 | 3/3 |
| `automating-agent-guardrails-guard-design` | 1.00 | 1.00 | +0.00 | 3 | 3/3 |
| `claude-cloud-sessions-multi-repo-hooks` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-commit-hook` | 0.67 | 0.00 | +0.67 | 3 | 0/3 |
| `devlog-consolidate-brief` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `devlog-correction-and-clock` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `devlog-insert-entry` | 0.00 | 0.00 | +0.00 | 3 | 3/3 |
| `dotnet-engineering-single-current-tfm` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `engineering-standards-explicit-registry` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `engineering-standards-no-fallback` | 0.33 | 0.00 | +0.33 | 3 | 3/3 |
| `review-wall-clock-ceiling` | 0.50 | 0.00 | +0.50 | 3 | 3/3 |
| `roslyn-analysis-renamed-clones` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `roslyn-analysis-safe-rewriter` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-compliance-audit-partial-verdict` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `spec-oracle-render-the-diagram` | 1.00 | 0.50 | +0.50 | 3 | 3/3 |
| `test-gate-conflict-markers-staged` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `test-gate-preexisting-red-blocks-merge` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |
| `variant-analysis-latent-not-cleared` | 1.00 | 0.00 | +1.00 | 3 | 3/3 |

Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator).

Mean Δ over 28 cases: +0.66.

## Notes on this run (written by hand, 2026-11-14)

- **Commands** (repository root, branch `update-5.2-evals`): the full run
  `python scripts/run_evals.py run --model claude-mythos-5-2 --effort high -j 4` at `755cce3` (run by the
  coordinating session; 2,173 s, $69.54), then the two cases it cut off, re-run alone at `a1d0b1a` after the
  limits were re-sized (`run ... --case review-wall-clock-ceiling`, 485 s, $9.82; `run ... --case
  devlog-insert-entry`, 282 s, $4.48), merged with `python scripts/run_evals.py merge <full> <re-run> <re-run>
  --out 2026-11-14-claude-mythos-5-2-high-merged`. `skills/` and `agents/` are identical at both heads (the merge
  compares their git tree ids) and unchanged from v1.22.0. The cost and time in the header are the sum.
- **Cut off in the full run, replaced:** `devlog-insert-entry` WITH #1 and #3 (timeout, 243 s of 240) and
  `review-wall-clock-ceiling` WITH #1-#3 (timeout, 302-303 s of 300). The other 163 runs completed and stand. In the
  re-runs the slowest took 484 s (`review-wall-clock-ceiling`) and 282 s (`devlog-insert-entry`); neither was cut off.
  Their limits were raised again after the re-run by the 2x rule (1,020 s and 600 s), which a completed run does
  not need re-running for.
- **Subagent model:** the operator's user settings `env` sets `CLAUDE_CODE_SUBAGENT_MODEL=opus`, and the eval
  children load those settings, so subagents in these runs ran on `claude-opus-5-5` (seen in the runs' usage), not
  on Mythos. The four agent cases, and any skill run that dispatched a subagent, measure a Mythos 5.2 session
  delegating to Opus 5.5. The setting was left as it is.
- **Quota:** the operator's weekly quota meter read ≈ 2.02 % before the full run and ≈ 9.01 % after it
  (about 7.0 points), ≈ 9.2 % before the re-runs and ≈ 10.0 % after (about 0.8 points).
- **Turns:** the CLI's per-run `turns` is not the count `--max-turns` limits: `review-wall-clock-ceiling` recorded
  19 turns against a cap of 16 and `dotnet-engineering-single-current-tfm` 7 against 6, both with a `success`
  ending. A cap hit ends a run as `error_max_turns`, which `run_evals.py` reports; none did.
