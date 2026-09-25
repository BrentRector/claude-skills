---
name: agent-type-design-analyzer
description: A new type with a kind enum plus kind-specific nullable fields and a hand-synced name table; the type-design-analyzer agent reports the illegal states and the drift, recommends a closed hierarchy, and pairs the collapse with a drift test.
tags: [type-design-analyzer, agent]
runs: 3
max_turns: 12
timeout_seconds: 420
allowed_tools: [Agent, Read, Grep, Glob]
expected_outcome: Flags the kind-enum-plus-nullable-fields shape (illegal states representable; wants a sealed hierarchy / discriminated union) and the hand-maintained KindNames array (drift), and recommends a drift test or construction-time guarantee to keep the fix true.
---

Please review the design of the new types in this change - use a specialist type-design reviewer if you have one. The code is all there is; don't look for a repo.

```csharp
public enum PaymentKind { Card, BankTransfer, Voucher }

public sealed class Payment
{
    public PaymentKind Kind { get; set; }
    public decimal Amount { get; set; }
    public string? CardLast4 { get; set; }      // Card only
    public string? Iban { get; set; }           // BankTransfer only
    public string? VoucherCode { get; set; }    // Voucher only

    // Display names; must stay in the same order as PaymentKind.
    public static readonly string[] KindNames = ["Card", "Bank transfer", "Voucher"];

    public string DisplayName => KindNames[(int)Kind];
}
```

Keep the answer under 250 words.
