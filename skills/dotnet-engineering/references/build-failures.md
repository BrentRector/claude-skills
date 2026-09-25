# Diagnosing MSBuild failures with binary logs

Adapted from dotnet/skills `plugins/dotnet-msbuild/skills/binlog-failure-analysis` (MIT, © .NET Foundation and
Contributors). Changes: condensed; root-cause rules and the first-error procedure added.

## 1. Get a binlog

```
dotnet build <Solution>.sln -bl:build.binlog
```

`-bl` records every evaluation, property, item, target, task and message, plus embedded project files. It costs a
few percent of build time; record one whenever console output doesn't explain a failure, and in CI keep it as an
artifact on failure. A binlog contains environment variables and file paths: treat it as sensitive before
attaching it to a public issue.

The `.binlog` is binary. Never `cat`, `head` or `strings` it.

## 2. Read it

In order of preference:

1. **The binlog MCP server** (`Microsoft.AITools.BinlogMcp`, bundled with dotnet/skills' msbuild plugin) when it
   is available: it queries errors, properties, items, evaluation and target execution directly, and can return
   project files embedded in the log when the sources are not on disk.
2. **MSBuild Structured Log Viewer** (`dotnet tool install -g MSBuild.StructuredLogger`, or the GUI) for a human.
3. **Replay to text** when neither is available:

```
dotnet msbuild build.binlog -noconlog -fl -flp:"v=diag;logfile=full.log;performancesummary" -fl1 -flp1:"errorsonly;logfile=errors.log" -fl2 -flp2:"warningsonly;logfile=warnings.log"
```

Then `errors.log` first, and search `full.log` around each code (`grep -n -B2 -A2 "CS0246" full.log`).

## 3. Find the first cause

- **The first error in build order is the one to fix.** A missing type in project A produces a cascade of
  CS0246 in every project that references A. Work out which project built first and failed first.
- **Evaluation before execution.** NETSDK and MSB4xxx errors raised during evaluation (bad SDK, missing import,
  invalid property function) invalidate everything after them.
- **Ask what value a property actually had**, not what the `.csproj` says: `Directory.Build.props`,
  `Directory.Packages.props`, imported targets, environment variables and global properties (`-p:`) all override
  it. The binlog shows the final value and where it was set.
- **Restore failures** (NU1xxx): read the package graph. NU1605 (downgrade) and NU1608 / NU1107 (conflict) mean
  two references disagree; resolve the disagreement in central package management rather than suppressing it.
- **Double writes and ordering**: two projects writing the same output file, or a target that runs before its
  input exists, show up in the binlog's target timeline. The fix is a correct `DependsOnTargets` /
  `BeforeTargets` or distinct output paths, not a retry.
- **Stale outputs**: when the failure disappears with `--no-incremental`, the defect is incremental-build
  metadata (missing `Inputs`/`Outputs` on a custom target, a generated file not added to `FileWrites`). Fix the
  target; don't make `clean` part of the build.

## 4. Fixes that are not fixes

- Deleting `bin/` and `obj/` until it builds, without finding what was stale.
- `<NoWarn>` or `-warnaserror-` to get past a warning that is the real signal.
- Pinning a transitive package to dodge a conflict without recording why the graph disagrees.
- Adding a `<Reference>` to a DLL in someone's `bin` folder.

Each of these hides the defect for the next person. When a workaround is truly unavoidable (an SDK bug), link
the upstream issue next to it and file it in the project's work register.
