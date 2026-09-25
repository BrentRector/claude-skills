---
name: variant-analysis-latent-not-cleared
description: A sweep finds the same defect in code nothing calls today; variant-analysis reports it as latent (unreachable today but unprotected) rather than cleared or omitted, and its sweep report records that the query was calibrated against the original instance so a zero elsewhere counts as evidence.
tags: [variant-analysis, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The report names the mechanism, lists the query verbatim with its scope and hits, classifies FormatRefund as latent (not cleared, not omitted), and states the calibration (the query hit the original before the fix).
---

Confirmed and fixed: negative amounts lost their minus sign because `InvoiceView.FormatTotal` called `Math.Abs(amount)`. My sweep, run before the fix: `rg -n 'Math\.Abs\(' src/` - 2 hits: the original in `InvoiceView.FormatTotal`, and `LegacyFormatter.FormatRefund(decimal amount) => Math.Abs(amount).ToString("N2")`. A solution-wide find-references shows nothing calls `FormatRefund` today.

Write the variant-sweep section for the PR description, at most 12 lines. Use the `variant-analysis` skill for this.
