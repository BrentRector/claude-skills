# Benchmarking with BenchmarkDotNet

Adapted from dotnet/skills `plugins/dotnet-diag/skills/microbenchmarking` and its references (MIT, © .NET
Foundation and Contributors). Changes: condensed; the witness discipline and the result-equality assertion added.

## 1. Before writing code: what will the number be compared against?

A single benchmark number only tells you an order of magnitude. Name the comparison axis first:

| Axis | How BenchmarkDotNet (BDN) does it |
|---|---|
| Approach A vs B | two `[Benchmark]` methods, one `Baseline = true` (preferred: one process, one run) |
| Before vs after a change | reference the saved old build as a DLL next to the current source, or two jobs over two builds, one `.AsBaseline()` |
| Runtime vs runtime | `<TargetFrameworks>` listing both, `--runtimes a b` (first listed is the baseline) |
| Package version vs version | an MSBuild property for the version, one job per value via `.WithMsBuildArguments` |
| Runtime configuration (GC, JIT) | one job per configuration, one `.AsBaseline()` |
| Scale | `[Params(100, 10_000, 1_000_000)]` |

`[Benchmark(Baseline = true)]` compares methods within a job; `.AsBaseline()` compares jobs. Using the wrong one
produces no `Ratio` column. For cross-job comparisons, `--apples` fixes the invocation count from the baseline
job so every job measures the same number of operations (it needs an explicit iteration count such as
`--job Short`). A `StatisticalTestColumn` (Mann-Whitney, with a threshold such as 5%) turns ratios into
Faster / Same / Slower verdicts.

Know why the benchmark exists: a **permanent coverage suite** (checked in, follows the suite's conventions, real
callers' inputs) or a **task-scoped** investigation, change validation or design choice (a standalone project in a
scratch directory, deleted when the decision is made).

## 2. Writing a correct benchmark

- **Add the package without a version** (`dotnet add package BenchmarkDotNet`) so you get the one that knows the
  current runtime. Remembered version numbers are stale.
- **Entry point passes `args` through**: `BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args)`.
  Without `args`, every CLI flag is silently ignored. Always pass `--filter` so the switcher never waits on an
  interactive prompt.
- **Return the result.** A `void` method whose result is unused can be dead-code eliminated. For deferred
  sequences, consume them (`Consumer`) or materialise.
- **Inputs in fields or `[Params]`,** never literals or `const`: the JIT folds constant expressions and you measure
  a precomputed answer.
- **Setup in `[GlobalSetup]`.** Work inside the method is measured. Use `[IterationSetup]` only when the benchmark
  mutates state that must be reset, and then make the operation long (hundreds of ms): it forces one invocation
  per iteration.
- **No manual loops.** BDN chooses the invocation count. When per-invocation setup can't move out (a `Span<T>`),
  unroll N operations by hand and declare `OperationsPerInvoke = N`.
- **Idempotent.** A benchmark that grows a list on every call measures a moving target.
- **Seeded randomness** with a sample large enough to be representative.
- **`[MemoryDiagnoser]` on by default.** Allocations are usually the finding, and `Allocated` is a cheap witness
  that the code path you think ran did run.
- **Async**: return `Task` / `ValueTask`; BDN awaits it.

## 3. The witness: proving the benchmark measured the work

A benchmark that measured the wrong thing looks exactly like a fast one. Before quoting any number:

1. **Equal outputs.** When comparing A and B, a `[GlobalSetup]` computes both results on the benchmark's inputs
   and throws if they differ. A faster wrong answer is not an optimization.
2. **Expected population.** The summary shows the number of cases you planned (methods × params × jobs). A
   `--filter` that matched nothing prints no table and still exits 0: the same silent green as a test filter.
3. **Right build.** The report header shows Release, the intended runtime, no attached debugger, and the
   commit or build you meant. BDN refuses Debug builds of the benchmark project; it does not check that the
   *referenced* library is the build you think it is.
4. **Plausible magnitudes.** Sub-nanosecond means for real work mean the JIT removed it. `Allocated` of `-` for
   code that must allocate means it didn't run.
5. **Record the report.** Keep `*-report-github.md` (and the CSV) with the claim, together with the commit,
   machine and runtime. A ratio without the report behind it is an anecdote.

## 4. Running efficiently

| Job | Per case | Use |
|---|---|---|
| `--job Dry` | < 1 s | proves it compiles and runs; no measurement |
| `--job Short` | ~5-8 s | iterating on design |
| default | ~15-25 s | the numbers you report |
| `--job Medium` / `Long` | ~40 s / minutes | when a small difference matters |

- Estimate the case count before running: `[Params]` form a Cartesian product, and jobs multiply it.
- Redirect the verbose console to a file and read the Markdown report:
  `dotnet run -c Release -- --filter "*Parser*" > bench.log 2>&1`. Read the log only for errors.
- Run subsets with `--filter`, one or two methods at a time, rather than one multi-hour run.
- Close noisy processes; plug in laptops; don't compare numbers from different machines as if they were one run.
- Unstable results (high `StdDev`, bimodal): raise the iteration count, check for GC or tiering effects
  (`--job Medium`, `[DisassemblyDiagnoser]`, `EventPipeProfiler`), and look for hidden I/O or shared state before
  concluding anything.

Profiling (dotnet-trace, PerfView), production telemetry and load testing are different tools; BDN answers
"which of these is faster, and by how much, in isolation".
