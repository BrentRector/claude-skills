---
name: dotnet-engineering
description: Use for any .NET or C# work - writing or reviewing C#, running or filtering dotnet test, writing tests or judging whether tests would catch a bug, BenchmarkDotNet measurements, diagnosing an MSBuild failure from a binlog, trimming or Native AOT warnings (IL2026, IL3050 and friends), or publishing a NuGet package from GitHub Actions. States the .NET-specific bar - latest .NET and C#, no back-compat baggage, strong types, tests that verify values from the authority, benchmarks that carry a witness, and a test filter that matched nothing counted as a red.
---

# .NET engineering

> Adapted from [dotnet/skills](https://github.com/dotnet/skills) `plugins/dotnet-test/skills/filter-syntax`,
> `plugins/dotnet-test/skills/test-gap-analysis`, `plugins/dotnet-test/skills/test-smell-detection`,
> `plugins/dotnet-diag/skills/microbenchmarking`, `plugins/dotnet-msbuild/skills/binlog-failure-analysis`,
> `plugins/dotnet-upgrade/skills/dotnet-aot-compat` and `plugins/dotnet-advanced/skills/nuget-trusted-publishing`
> (MIT, © .NET Foundation and Contributors). **Changes:** seven skills consolidated into one with a reference file
> per topic; condensed and reworded; multi-targeting, .NET Framework, netstandard polyfill and older-SDK guidance
> dropped (latest .NET only); added the owner's bar (zero-match filter is a red, expected values from the
> authority, benchmarks carry a witness, suppressions are defects, no fallbacks). The MIT notice is in
> [references/THIRD-PARTY-NOTICES.md](references/THIRD-PARTY-NOTICES.md).

This is the .NET-specific layer on top of **engineering-standards** and **test-gate**. It says what the generic
bar means in C#, MSBuild, `dotnet test`, BenchmarkDotNet, the trimmer and NuGet. Detail lives in the reference
files; load the one for the task in hand, not all of them.

| Task | Read |
|---|---|
| Running, filtering, writing or auditing tests | [references/testing.md](references/testing.md) |
| Measuring performance with BenchmarkDotNet | [references/benchmarking.md](references/benchmarking.md) |
| A build fails and the console output doesn't explain it | [references/build-failures.md](references/build-failures.md) |
| Trim or AOT analyzer warnings, `IsAotCompatible`, `PublishAot` | [references/aot.md](references/aot.md) |
| Publishing to nuget.org from GitHub Actions | [references/publishing.md](references/publishing.md) |

## The language and runtime bar

- **Target the latest stable .NET and the C# version it ships with.** One TFM, the current one. No
  `netstandard2.0`, no `net4x`, no multi-targeting and no polyfill packages unless a named, real consumer needs
  them, and then say who. Compatibility shims for users who don't exist are pure maintenance cost.
- **Modern idioms by default:** file-scoped namespaces, primary constructors, `record` / `record struct` for
  values, `required` and `init` members, collection expressions, pattern matching and switch expressions over
  `if` ladders, `Span<T>` / `ReadOnlySpan<T>` / `stackalloc` on hot paths, `field`-backed properties, generic
  math where it removes duplication, source generators over reflection.
- **Strong types over strings and primitives.** A value with rules (an id, a code, a unit, a validated name) gets
  its own type, so an invalid value cannot be constructed. Enums over magic strings; a closed hierarchy with an
  exhaustive `switch` over a type tag and a `default: throw`.
- **Nullable reference types on, warnings as errors, analyzers on** (`<Nullable>enable</Nullable>`,
  `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`, `<AnalysisLevel>latest-recommended</AnalysisLevel>`
  or stricter). A `!` or `#pragma warning disable` is a claim that needs a comment saying why it is true.
- **Central build configuration.** Shared properties in `Directory.Build.props`, package versions in
  `Directory.Packages.props` (central package management). A property repeated across `.csproj` files is one rule
  in several places.
- **Reflection is a design smell, not a tool of first resort.** It defeats the compiler, the trimmer and AOT.
  Prefer source generators (`System.Text.Json` contexts, `[GeneratedRegex]`, `[LoggerMessage]`,
  `[LibraryImport]`) and typed dispatch.
- **Async all the way:** no `.Result`, `.Wait()` or `async void` outside event handlers; pass the
  `CancellationToken` through; `ConfigureAwait(false)` in libraries.

## Testing - the rules that bite

Full detail, framework syntax and the smell catalog are in [references/testing.md](references/testing.md).

- **A filter that matched nothing is a red, not a green.** VSTest `dotnet test --filter` prints "No test matches
  the given testcase filter" and **exits 0**. Every OR/AND term needs its own property:
  `FullyQualifiedName~Parser|FullyQualifiedName~Lexer` works; `~Parser|~Lexer` and
  `FullyQualifiedName~Parser|~Lexer` match nothing. Read the `Total:` count, not the exit code.
- **Confirm new tests ran by name** (`dotnet test --list-tests`, or the TRX). A test that was never discovered
  passes by never running.
- **Expected values come from the authority** - the spec, the contract, a hand derivation - never from pasting
  whatever the code under test printed. A snapshot of current output is a regression net, not a verification.
- **Would the tests catch a bug?** Answer it by pseudo-mutation: inventory each caller-visible outcome, find the
  assertion that observes it, and name the witness input on which a plausible mutant differs. An outcome no
  assertion observes is a gap whatever the coverage percentage says.
- **Test smells that hide defects rank first:** a missing `await` on an async assertion, a test with no
  assertion, conditional logic that skips the assertion, a fixed `Thread.Sleep`, a disabled test with no tracked
  reason.
- **Build the solution before `--no-build`.** Building one project doesn't refresh the test output folders.

## Benchmarking - the rules that bite

Full detail in [references/benchmarking.md](references/benchmarking.md).

- **A number without a comparison is a rumour.** Every benchmark names its comparison axis (A vs B, before vs
  after, runtime vs runtime, N vs 10N) and marks a baseline so the report carries a `Ratio` column.
- **A benchmark carries a witness.** Before quoting a result, prove the benchmark did the work: the method
  returns its result, a `[GlobalSetup]` assertion checks both candidates produce the same output, and the report
  shows the expected case count, runtime and `Allocated` column. A benchmark that measured a folded constant, an
  empty filter or a Debug build looks exactly like a fast one.
- **Release, out of process, no debugger, no manual loops, inputs in fields** so the JIT can't fold them.
- **Validate cheap, measure once:** `--job Dry` to prove it runs, `--job Short` while iterating, the default job
  for the numbers you report. Record the report file (`*-report-github.md`) with the claim.

## Build failures

Detail in [references/build-failures.md](references/build-failures.md). Build with `-bl` the first time
something is unclear, and read the binlog (binlog MCP server, the MSBuild Structured Log Viewer, or a replay to
text), never `cat` it. Find the **first** error in evaluation or target order; the rest are usually cascades.
Fix the project or the package graph, never by pinning around it or deleting `obj/` until it goes away.

## Trimming and Native AOT

Detail in [references/aot.md](references/aot.md). Set `<IsAotCompatible>true</IsAotCompatible>` on libraries
and `<PublishAot>true</PublishAot>` where the app ships AOT. Fix warnings in this order: source-generate
(JSON, regex, logging, interop) → flow `[DynamicallyAccessedMembers]` from the innermost reflection call outward →
refactor what breaks annotation flow → `[RequiresUnreferencedCode]` / `[RequiresDynamicCode]` as an honest,
propagating label. **Never** `#pragma warning disable` or `[UnconditionalSuppressMessage]` an IL warning to get
to zero: the warning is the trimmer telling you the program will break at run time. Zero warnings is necessary,
not sufficient - run the published binary's tests.

## Publishing

Detail in [references/publishing.md](references/publishing.md). Publish to nuget.org with **trusted publishing
(OIDC)**: `NuGet/login` in a tag-triggered workflow with `id-token: write`, no long-lived API key. Pack and
inspect locally first - a package version, once pushed, is permanent. The tag and the project version must agree,
checked by the workflow, not by memory.

## Standards

The bar is the **engineering-standards** skill; the gate mechanics are the **test-gate** skill. In .NET terms:

- Root cause, never a suppression. A `NoWarn`, a `#pragma`, an `[UnconditionalSuppressMessage]`, a `!`, a skipped
  test or a widened tolerance that makes a red go away is a hidden defect unless it states why it is correct.
- No fallbacks. A `try { exact } catch { fuzzy }`, a reflection path "in case the generator missed it", or a
  second serializer for old callers is a second, wrong answer to a question the first path should answer.
- One mechanism per job: one serializer, one DI container, one logging abstraction, one test framework per
  solution. Two coexisting mechanisms is a defect even when both work.
- Every check is seen to fail once. A new test, analyzer rule, benchmark assertion or CI gate is pointed at the
  defect (or an old revision) before its green counts.
- Report calibrated to evidence: say which command ran, on which build, with what count. "Tests pass" without a
  `Total:` line and "faster" without a ratio and a report file are not findings.

## Project hooks

This skill is generic. A repository records its specifics in `CLAUDE.md` (or `CONTRIBUTING.md`) and those win
on conflict:

- the solution to build, the target framework, and the analyzer / warnings-as-errors settings
- the test framework and runner (VSTest or Microsoft.Testing.Platform), each tier's exact filter, and the baseline
  counts, so a vanished population is visible
- the benchmark project, its baseline results, and where reports are kept
- whether any assembly ships trimmed or Native AOT, and its smoke test
- the publish workflow filename and the nuget.org trusted-publishing policy owner
