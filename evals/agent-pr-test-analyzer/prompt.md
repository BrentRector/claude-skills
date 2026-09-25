---
name: agent-pr-test-analyzer
description: Test-coverage review of a change whose new tests include a golden captured from the program's own output and a Stopwatch ceiling; the pr-test-analyzer agent's oracle and determinism checks flag both, in its Check-tagged finding format.
tags: [pr-test-analyzer, agent]
runs: 3
max_turns: 12
timeout_seconds: 420
allowed_tools: [Agent, Read, Grep, Glob]
expected_outcome: Flags the golden copied from the tool's own output (oracle - pins whatever the code does) and the 500 ms Stopwatch ceiling (determinism - name a work-count or same-run growth-ratio replacement), and that only the reported leap-year input is tested (scope).
---

Please review the test coverage in this change before I merge it; use a specialist test-coverage reviewer if you have one. The diff is all there is - don't look for a repo.

```diff
--- a/src/Calendar/DateMath.cs
+++ b/src/Calendar/DateMath.cs
@@
-    public static bool IsLeapYear(int y) => y % 4 == 0;
+    // Gregorian rule: divisible by 4, except centuries, except every 400 years.
+    public static bool IsLeapYear(int y) => y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
--- /dev/null
+++ b/tests/Calendar.Tests/DateMathTests.cs
@@
+public class DateMathTests
+{
+    // Bug #311: 1900 was reported as a leap year.
+    [Fact] public void Year1900_is_not_leap() => Assert.False(DateMath.IsLeapYear(1900));
+
+    // Expected text captured by running `calgen --year 2100` after the fix.
+    [Fact] public void Calendar_2100_matches_golden() =>
+        Assert.Equal(File.ReadAllText("golden/cal-2100.txt"), CalGen.Render(2100));
+
+    [Fact] public void Render_century_is_fast()
+    {
+        var sw = Stopwatch.StartNew();
+        for (var y = 1600; y < 1700; y++) CalGen.Render(y);
+        Assert.True(sw.ElapsedMilliseconds < 500);
+    }
+}
```
