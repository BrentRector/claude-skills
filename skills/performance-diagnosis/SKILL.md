---
name: performance-diagnosis
description: Use when something is slower than it should be - a test suite, a build, a compile, a service, a batch job - when adding threads or machines stops helping, when CPU sits idle while work waits, or before any optimization at all. Measure first, then find the mechanism; a scaling curve, a processes-versus-threads split and stack sampling locate the bottleneck, decompiling or reading the library confirms why, a behavior-neutral differential proves the fix changed nothing, and a structural guard (never a wall-clock limit) keeps it fixed. Not for micro-benchmarking one method in isolation (see dotnet-engineering's BenchmarkDotNet rules) or for code review of performance smells (see review).
---

# Performance diagnosis

**Measure before you design, and find the mechanism before you fix.** A slowdown is a question with a mechanical
answer: something is waiting for something. Intuition names a suspect; measurement names the culprit. Most of the
cost of performance work is optimizing the wrong thing, and the most valuable findings are the ones nobody was
looking for.

*Why: the largest speed-up in one long-running project came from an agent told to measure before designing a faster
test runner. One number didn't fit: the test host used about 4 of 24 cores. Four steps took it from that number to
six grammar rules in a generated lexer that serialized every thread on one lock. The fix made the front end about 32×
faster on one thread and cut the full test suite from about 11 minutes to under 5. Nobody had suspected the lexer.*
*(Practice — not yet validated: one investigation; the method is general, the evidence is one case.)*

## When to use

- A suite, build, compile or job is slower than it should be, or got slower.
- Adding threads, cores or machines stops helping, or CPU sits idle while work is queued.
- Before ANY optimization, including one a design or ticket already proposes: re-measure its premise.
- After a speed-up lands, to find the next bottleneck.

**Not for:** tuning one method in isolation (use a micro-benchmark harness; `dotnet-engineering` covers
BenchmarkDotNet), or reviewing code for performance smells without a measured problem (`review`).

## Step 1: A benchmark that proves it did the work

Fix the input, the machine and the conditions, and make the benchmark print a **witness**: a count, a checksum or a
number of items processed that proves the work ran. Record for every run:
- **Cold or warm.** Every cache matters: compiled-output caches, JIT, OS file cache, build servers, test result
  caches. State which were empty. A "fast" run on a warm cache is not a measurement of the code.
- **Load and priority.** Other processes on the host, the run's priority class, and anything sharing the cores.
  Compare only runs taken under the same conditions.
- **Wall time and CPU time.** Wall time alone cannot tell waiting from working.

*Why: a warm compiled-program cache once turned a 23-minute re-run into 78 seconds; a benchmark that silently hit it
would have "measured" a 17× speed-up that did not exist. And a before/after pair taken under different load is a
comparison of the machines, not of the code.* *(Practice — not yet validated.)*

## Step 2: Where does the time go?

Before looking for a slow line, find the slow PART:
- **Shares.** Per phase, per test class, per request type: which parts carry most of the time? One project's suite
  spent 54 % of its test-seconds in one family of tests.
- **The critical path.** In parallel work, the wall time is the longest chain, not the sum. Find what finishes last.
- **Long poles.** List the slowest individual items. One 219-second test was a separate defect (the code filled 64
  million elements before rejecting the input), fixed on its own.

Report the slowest items continuously (a top-5 list in every full run), but only REPORT them; never assert a time
limit in a test. *Why: a wall-clock ceiling in a test fails on a busy machine with no regression.* *(Practice — not yet
validated.)*

## Step 3: The scaling curve, and processes versus threads

Run the same work at 1, 2, 4, 8, … threads up to the core count, and record wall time and CPU utilization at each.
- **Linear, then flat at the core count:** compute-bound. The work itself is the cost.
- **Flat early, CPU mostly idle:** something serializes. Then split the question.
- **Split it: N processes versus N threads.** Run the same work as N separate processes, each single-threaded.
  - If N processes scale but N threads do not, the limit is INSIDE one process: a lock, a shared cache, the garbage
    collector, a thread pool, a single writer.
  - If neither scales, the limit is outside: disk, network, memory bandwidth, an external service.

*Why: measured in the lexer case, one process used about 4 of 24 cores. Two processes ran 1.8× faster and four 2.8×,
while threads stopped gaining past 8, with the CPU 85 % idle at 24. That split alone moved the search from "the
machine" to "one process", before any profiler ran.* *(Practice — not yet validated.)*

## Step 4: Sample the stacks during the plateau

With the work running at the thread count where it plateaus, take repeated stack samples of every thread, and count
frames.
- **.NET:** `dotnet-stack report -p <pid>` (repeat), `dotnet-trace collect`, and `dotnet-counters monitor` for
  `monitor-lock-contention-count`, GC pause time and heap sizes.
- **JVM:** `jstack`, async-profiler. **Python:** `py-spy dump` / `py-spy record`. **Native:** `perf`, ETW/WPA.
- **Read the counts, not one sample.** The frame that dominates the samples is the suspect. Threads parked in
  `Monitor.Enter`, a mutex or a futex mean a lock; a high GC-pause share means allocation pressure; threads in read,
  poll or recv mean I/O.

*Why: in the lexer case, 28 of 30 single-thread samples and 24 of 24 twelve-thread samples sat in the same two
frames of the lexer's simulator, with 12 of the 24 blocked entering one monitor. The counters confirmed about 1,400
contended lock acquisitions per compile.* *(Practice — not yet validated.)*

## Step 5: Explain the mechanism before fixing it

A hot frame is where the time goes, not why. Before changing anything, explain WHY that code runs so often or waits
so long. Read the library's source, or decompile it (ILSpy or ilspycmd for .NET, a decompiler for the JVM) when the
source isn't at hand, and find the condition that sends you down the slow path.

*Why: the stack samples said "the lexer rebuilds its start state and takes a lock on every token". Decompiling the
generator's runtime said why: it never caches a mode's start state when a rule in that mode begins with a semantic
predicate, and six rules did. That turned "rewrite the lexer" into "move six conditions from the start of their
rules into actions", a small, safe change.* *(Practice — not yet validated.)*

## Step 6: Prove the fix changed nothing but speed

A performance fix must be behavior-neutral, and "the tests pass" is not proof of that, because the tests may not
exercise what changed.
- **Differential over the whole input population.** Capture the old code's output for EVERY input the system
  actually processes (every file the tests feed it, every recorded request), replay it through the new code, and
  compare every field. For the lexer, all 17,055 inputs, about 10 million tokens, matched in type, channel, offsets,
  line, column, text and final mode.
- **Compare case by case, never by totals.** Equal counts can hide swapped items (`test-gate`).

*(Practice — not yet validated.)*

## Step 7: Guard the mechanism, not the clock

Pin the fix with a test that checks the MECHANISM stayed fixed, and see that test fail on the old code (or on a
planted regression) before trusting it.
- Good guards check structure: a cache is populated after warm-up, an allocation count, no call to the slow path,
  a query plan, a lock never taken on the hot path, a rule in the grammar never starting with a predicate.
- ⛔ **Never a wall-clock ceiling.** A timing assertion flakes on a loaded machine, and a flaky test gets ignored.

*Why: the lexer guard warms the lexer, then walks its cached state machine over the inputs and fails if any step
would need a fresh simulation. It was red on the old grammar and on a planted predicate, and green in 3 seconds on
the fix.* *(Practice — not yet
validated.)*

## Step 8: Re-measure, attribute honestly, name the next bottleneck

Run the Step 1 benchmark again under the same conditions, and report before and after with those conditions.
- **Attribute.** When several changes landed together, say how much each contributed, or say that you can't separate
  them. "11 minutes to under 5" included a removed long pole and newly parallel test groups, not only the lexer fix.
- **Name the next bottleneck.** Removing one limit exposes the next. After the lock was gone, CPU use was 21 % at 12
  threads, and the garbage collector was the new limit. Re-run Steps 3 and 4 and record it as the next item.
- **Measured versus modeled.** Mark every figure as measured (with its conditions) or modeled (with its assumptions).

*(Practice — not yet validated.)*

## Report

For every investigation, record:
1. The question, the benchmark and its witness, and the conditions (cold or warm, load, priority, hardware).
2. Where the time goes: shares, critical path, long poles.
3. The scaling curve and the processes-versus-threads result.
4. The stack-sample counts, and the mechanism with its source (the code read or decompiled).
5. The fix, its differential (population and result) and its guard (seen failing once).
6. Before and after, attributed; the next bottleneck.

## Anti-patterns

- Optimizing the first plausible suspect without a scaling curve or a stack sample.
- Measuring on a warm cache, or comparing runs taken under different load.
- A speed-up reported with no witness that the work was done.
- "The tests pass" offered as proof that a performance fix changed no behavior.
- A timing assertion in a test.
- One headline number for several changes, with no attribution.
