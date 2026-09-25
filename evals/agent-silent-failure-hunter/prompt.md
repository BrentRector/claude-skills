---
name: agent-silent-failure-hunter
description: Error-handling review where one path crashes loudly and another silently returns a default price; the silent-failure-hunter agent ranks a silent wrong answer above a crash and never recommends replacing the crash with a default.
tags: [silent-failure-hunter, agent]
runs: 3
max_turns: 12
timeout_seconds: 420
allowed_tools: [Agent, Read, Grep, Glob]
expected_outcome: WORST is L9 (the TryParse failure silently becomes a 0 price that gets billed), ranked above the L13 NotSupportedException crash; the fix for L13 is not a default value.
---

Please check the error handling in this change for silent failures - use a specialist error-handling reviewer if you have one. The code is all there is; don't look for a repo. Line numbers are on the left.

```csharp
 1  public sealed class PriceService(IRateSource rates, IPriceFeed feed)
 2  {
 3      // Returns the unit price of a SKU in the requested currency.
 4      public decimal UnitPrice(string sku, string currency)
 5      {
 6          string raw = feed.RawPrice(sku);            // e.g. "12.50", or "N/A" when the feed has no price
 7          decimal price;
 8          if (!decimal.TryParse(raw, CultureInfo.InvariantCulture, out price))
 9              price = 0m;                             // keep checkout working
10          return currency switch
11          {
12              "USD" => price,
13              "EUR" or "GBP" => throw new NotSupportedException($"Currency {currency} not supported yet"),
14              _ => throw new ArgumentException($"Unknown currency {currency}", nameof(currency)),
15          };
16      }
17  }
```

Checkout calls `UnitPrice` for every cart line and bills the total. EUR and GBP carts are accepted by the storefront today. Rank the problems worst first, and end with exactly one line naming the single worst line: `WORST: L<number>`.
