# dotnet-engineering

The .NET-specific layer on top of the generic engineering bar. Most .NET defects that survive review are not
exotic: a `dotnet test --filter` that matched nothing and still exited 0, a test whose expected value was pasted
from the code's own output, a benchmark that measured a constant the JIT folded away, a trim warning suppressed
to reach zero, a NuGet API key sitting in a secret. This skill states what "correct" means in C#, MSBuild,
`dotnet test`, BenchmarkDotNet, the trimmer and NuGet, and keeps the detail in one reference file per topic so
Claude loads only the one the task needs.

## When Claude uses it

Skills load automatically when the task matches the skill's description. This one matches any .NET or C# work:

- writing or reviewing C#;
- running or filtering `dotnet test`, writing tests, or judging whether tests would catch a bug;
- BenchmarkDotNet measurements;
- diagnosing an MSBuild failure from a binlog;
- trimming or Native AOT warnings (IL2026, IL3050 and friends);
- publishing a NuGet package from GitHub Actions.

You can also ask for it by name ("use the dotnet-engineering skill") or describe one of those tasks.

## What it does

`SKILL.md` carries the bar and the "rules that bite" for each topic; the reference files carry the procedure.

| Task | Reference | What it covers |
|---|---|---|
| Running, filtering, writing or auditing tests | [`references/testing.md`](references/testing.md) | VSTest filter grammar and its traps; xUnit v3 and TUnit filter flags; checking a filter before trusting it; writing tests that verify; test-gap analysis by pseudo-mutation; a test-smell catalog ranked by severity |
| Measuring performance | [`references/benchmarking.md`](references/benchmarking.md) | choosing the comparison axis; writing a correct benchmark; the five-part witness; which job to run when |
| A build fails and the console doesn't explain it | [`references/build-failures.md`](references/build-failures.md) | recording a binlog (`-bl`); reading it (binlog MCP server, Structured Log Viewer, or replay to text); finding the first cause; "fixes that are not fixes" |
| Trim / AOT warnings | [`references/aot.md`](references/aot.md) | turning the analyzers on; a table of common IL codes; the fix order; what never to do; running the published binary |
| Publishing to nuget.org | [`references/publishing.md`](references/publishing.md) | pack-and-inspect before the first push; the nuget.org trusted-publishing policy; an OIDC workflow with a tag-equals-version gate; troubleshooting |

The core rules, in brief:

1. **Language and runtime.** One target framework, the latest stable .NET and its C# version; modern idioms;
   strong types over strings; nullable on, warnings as errors, analyzers on; central build configuration in
   `Directory.Build.props` / `Directory.Packages.props`; source generators over reflection; async all the way.
2. **Testing.** A filter that matched nothing is a red. Confirm new tests ran by name. Expected values come from
   the authority. Answer "would the tests catch a bug?" by pseudo-mutation. Rank smells that hide defects first.
   Build the solution before `--no-build`.
3. **Benchmarking.** Name the comparison axis and mark a baseline. Carry a witness. Release, out of process, no
   manual loops, inputs in fields. `--job Dry` to validate, `--job Short` while iterating, the default job for
   reported numbers; keep the `*-report-github.md` file with the claim.
4. **Build failures.** Build with `-bl`, read the binlog with a tool (never `cat` it), fix the first error in
   evaluation or target order.
5. **Trimming and AOT.** Source-generate → flow `[DynamicallyAccessedMembers]` → refactor what breaks the flow →
   `[RequiresUnreferencedCode]` / `[RequiresDynamicCode]` as an honest label. Never suppress an IL warning to
   reach zero, and test the published binary.
6. **Publishing.** Trusted publishing (OIDC) via `NuGet/login` in a tag-triggered workflow with
   `id-token: write`; pack and inspect locally first; the workflow checks that tag and project version agree.

## Why it works this way

| Rule | The failure it prevents |
|---|---|
| A zero-match filter is a red | VSTest prints "No test matches the given testcase filter" and **exits 0**. `~Parser\|~Lexer` and `FullyQualifiedName~Parser\|~Lexer` both match nothing, so a gate built on them is a silent green. Under Microsoft.Testing.Platform zero tests returns exit code 8, which scripts often swallow. |
| Confirm new tests ran by name | A test that was never discovered passes by never running. |
| Expected values from the authority | A value pasted from current output only proves the code still does what it did; a snapshot is a regression net, not a verification. |
| Pseudo-mutation for test gaps | Coverage percentages don't say whether any assertion observes an outcome. An outcome no assertion observes is a gap whatever the percentage says. |
| A benchmark carries a witness | A benchmark that measured a folded constant, an empty filter or a Debug build looks exactly like a fast one. A `[GlobalSetup]` that checks both candidates return the same result also stops "a faster wrong answer" being reported as an optimization. |
| Inputs in fields, results returned | The JIT folds constant expressions and can eliminate an unused result, so you measure a precomputed answer or nothing. |
| First error in build order | Later errors are usually cascades (a missing type in one project produces CS0246 in every project referencing it). |
| No `bin/obj` deletion, `NoWarn` or pinning as a fix | Each hides the defect for the next person. |
| Never suppress IL warnings | The warning is the trimmer saying the published program will fail at run time. `[UnconditionalSuppressMessage]` also tells the trimmer, so it can no longer protect you. Zero warnings is still not sufficient, because the analyzers can't see code reached through strings in configuration. |
| No reflection fallback | A second path "in case the generator missed it" only runs in the configuration nobody tests. |
| Trusted publishing, pack and inspect first | No long-lived secret to leak or rotate. A pushed version is permanent (it can be unlisted, never replaced). |
| One target framework, no polyfills | Compatibility shims for users who don't exist are pure maintenance cost; add them only for a named, real consumer. |
| Suppressions need a stated reason | A `NoWarn`, `#pragma`, `!`, skipped test or widened tolerance that makes a red go away is a hidden defect unless it says why it is correct. |
| Every check is seen to fail once | A new test, analyzer rule, benchmark assertion or CI gate counts only after it has been pointed at the defect (or an old revision) and gone red. |

Reports are calibrated to evidence: "tests pass" needs a `Total:` line, and "faster" needs a ratio and a report
file.

## Using it in your project

The skill is generic. Your repository's `CLAUDE.md` (or `CONTRIBUTING.md`) records the specifics, and those win
on conflict:

- the solution to build, the target framework, and the analyzer / warnings-as-errors settings;
- the test framework and runner (VSTest or Microsoft.Testing.Platform), each tier's exact filter, and baseline
  counts so a vanished test population is visible;
- the benchmark project, its baseline results and where reports are kept;
- whether any assembly ships trimmed or Native AOT, and its smoke test;
- the publish workflow filename and the nuget.org trusted-publishing policy owner.

Prerequisites: the .NET SDK. The references also mention optional tools (BenchmarkDotNet, the MSBuild Structured
Log Viewer, the binlog MCP server).

**Sibling skills.** It sits on top of [`engineering-standards`](../engineering-standards/SKILL.md) (the bar) and
[`test-gate`](../test-gate/SKILL.md) (gate mechanics). For C# duplication checks, symbol sweeps and assembly
inspection, see [`roslyn-analysis`](../roslyn-analysis/README.md).

See [`SKILL.md`](SKILL.md) for the full rules.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The .NET bar, the rules that bite per topic, standards, project hooks |
| [`references/testing.md`](references/testing.md) | Test filters, writing tests, test-gap analysis, test smells |
| [`references/benchmarking.md`](references/benchmarking.md) | BenchmarkDotNet: comparison axes, correctness, the witness, running efficiently |
| [`references/build-failures.md`](references/build-failures.md) | MSBuild binlog capture and failure analysis |
| [`references/aot.md`](references/aot.md) | Trimming and Native AOT compatibility |
| [`references/publishing.md`](references/publishing.md) | nuget.org trusted publishing from GitHub Actions |
| [`references/THIRD-PARTY-NOTICES.md`](references/THIRD-PARTY-NOTICES.md) | Upstream attribution and the MIT license text |

## Credits / license

Adapted from [dotnet/skills](https://github.com/dotnet/skills) (MIT, © .NET Foundation and Contributors),
specifically these upstream skills:

- `plugins/dotnet-test/skills/filter-syntax`, `test-gap-analysis`, `test-smell-detection`
- `plugins/dotnet-diag/skills/microbenchmarking`
- `plugins/dotnet-msbuild/skills/binlog-failure-analysis`
- `plugins/dotnet-upgrade/skills/dotnet-aot-compat`
- `plugins/dotnet-advanced/skills/nuget-trusted-publishing`

Changes: seven skills consolidated into one with a reference file per topic; condensed and reworded;
multi-targeting, .NET Framework, netstandard polyfill and older-SDK guidance dropped; added rules (zero-match
filter is a red, expected values from the authority, benchmarks carry a witness, suppressions are defects, no
fallbacks). Each reference file states its own changes. The full MIT notice is in
[`references/THIRD-PARTY-NOTICES.md`](references/THIRD-PARTY-NOTICES.md).
