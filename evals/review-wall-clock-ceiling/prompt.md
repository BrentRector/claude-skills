---
name: review-wall-clock-ceiling
description: A diff whose new test asserts a Stopwatch ceiling; the review skill's full-code dimension makes that a finding with a concrete scenario and names a deterministic replacement (work count, observed effect, growth ratio).
tags: [review, skill]
runs: 3
max_turns: 10
timeout_seconds: 300
allowed_tools: [Skill, Read]
expected_outcome: Flags the ElapsedMilliseconds < 200 assertion as a finding (it measures the machine; a loaded CI runner turns it red with no regression) and names a deterministic replacement such as a work count through a seam or a growth ratio of two readings in the same run; each finding carries a Scenario.
---

Please do a code review of this diff before I merge it - architecture, correctness, performance and duplication. It adds a cache to our price lookup.

```diff
--- a/src/Pricing/PriceLookup.cs
+++ b/src/Pricing/PriceLookup.cs
@@
 public sealed class PriceLookup(IPriceStore store)
 {
+    private readonly ConcurrentDictionary<string, decimal> _cache = new();
+
-    public decimal Get(string sku) => store.Load(sku);
+    public decimal Get(string sku) => _cache.GetOrAdd(sku, store.Load);
 }
--- /dev/null
+++ b/tests/Pricing.Tests/PriceLookupCacheTests.cs
@@
+public class PriceLookupCacheTests
+{
+    [Fact]
+    public void Repeated_lookups_are_fast()
+    {
+        var lookup = new PriceLookup(new SqlPriceStore(TestDb.ConnectionString));
+        lookup.Get("SKU-1");
+        var sw = Stopwatch.StartNew();
+        for (var i = 0; i < 10_000; i++) lookup.Get("SKU-1");
+        sw.Stop();
+        Assert.True(sw.ElapsedMilliseconds < 200, $"took {sw.ElapsedMilliseconds} ms");
+    }
+}
```

The diff is all you need; don't go looking for the repo.
