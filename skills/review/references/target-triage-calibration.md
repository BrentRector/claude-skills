# Target, triage and calibration (Steps 1, 3, 4)

Moved out of `SKILL.md` verbatim. Read it before Step 1 when a PR already carries a review, before skipping any dimension, and before Step 4.

## Target selection and incremental PR mode (Step 1)

- **No argument:** the local diff against the default branch (detect it: `git symbolic-ref refs/remotes/origin/HEAD`,
  never assume `main`), including staged and unstaged changes.
- **PR number/URL:** `gh pr diff`, `gh pr view` for the description and linked issue.
- **Branch or path:** diff the branch against its merge base, or review the named files/directories.
- **"Audit" / "be comprehensive" / a subsystem name:** whole-source mode (see *Scale* below).
- **Incremental PR mode:** if the PR already carries a review from a previous run, read the full conversation first
  (`gh pr view --json reviews,comments`), diff only the commits pushed since that review, and open the report with
  `Incremental review - changes since <timestamp>`. Do not re-raise a finding the author already answered with a
  justification. No new commits → say so and stop.

## Triage table (Step 3)

| Dimension | Skip when the change is... |
|---|---|
| Architecture | a local fix inside one function with no new types, dependencies or call paths |
| Full code review | never skipped |
| Performance | docs, config, copy, styling or test-only, with no logic on a runtime path |
| Duplication and efficiency | docs-only; **never** skip for new files - new code is where duplication is born |

## Calibration (Step 4)

Read the project's instructions (CLAUDE.md, README) for explicit context first; an author's statement beats
anything inferred. The axes are independent - a small internal payroll tool is low-scale and high-consequence.

- **Scale** (tunes architecture and performance): *pre-launch* - drop speculative scale concerns, downgrade perf
  and architecture to suggestions · *early users* - flag clear regressions, no premature optimization · *at scale*
  or *long-lived* (a product expected to be maintained for years) - full rigor; structural debt compounds.
- **Consequence** (tunes correctness): *low* - recoverable, nothing sensitive · *standard* - normal product code ·
  *high* - money, PII, auth, compliance, safety, data loss, or output other systems trust - edge cases are real.

If nothing is stated, assume *early users / standard*, say that you inferred it, and suggest the author add a line
such as `Project context: scale=long-lived, consequence=high` to CLAUDE.md. Pass both axes to every agent.
