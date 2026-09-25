---
name: spec-compliance-audit-partial-verdict
description: A rule holds on the common path and fails on a second reachable path; spec-compliance-audit's vocabulary makes that PARTIAL, never CONFORMS, and it cannot close without a spec-derived witness.
tags: [spec-compliance-audit, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: Verdict PARTIAL (holds on the Write path, fails on the reachable WriteAppend path), the row does not close, and it becomes a tracked work item.
---

We're auditing our RLF writer against the RLF 2.1 standard, one rule at a time. Rule under audit:

> **RLF 2.1 §4.2 rule 3** - "When the value has fewer than W digits, the field is filled on the left with the digit zero to width W."

The implementation (both methods are public and used in production):

```csharp
public static string Write(long value, int width) =>
    value.ToString(CultureInfo.InvariantCulture).PadLeft(width, '0');

public static void WriteAppend(StringBuilder sb, long value, int width) =>
    sb.Append(value.ToString(CultureInfo.InvariantCulture).PadLeft(width));
```

There is a passing test `Write(42, 6) == "000042"`. Record the audit row: give the verdict for this rule as a single upper-case word on a line `VERDICT: <WORD>`, then say in one line whether the row is closed. Use the `spec-compliance-audit` skill for this.
