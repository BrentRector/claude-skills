# roslyn-analysis

grep matches text; Roslyn reads C# the way the compiler does. This skill gives Claude four small, read-only-by-default
helper programs for questions that must be answered correctly across a whole solution: *is this logic written
twice, even with renamed variables?*, *who else implements this rule?*, *how do I change this shape in 400 files
without breaking one?*, and *what did the compiler actually emit?* A text search misses renamed copies, aliases,
`using static`, explicit interface implementations and extension-method calls, and it matches unrelated symbols that
happen to share a name.

## When Claude uses it

Skills load automatically when the task matches the skill's description. This one matches C#/.NET work where a
review or refactor needs facts from the compiler rather than from grep:

- finding duplicated method bodies and near-clones across a solution;
- listing every implementation, override, caller and reference of a mechanism for a sibling sweep;
- applying one mechanical change across many files with a syntax rewriter that preserves comments and formatting;
- inspecting a built assembly's metadata and IL.

It is **not** for one-off edits or for questions a build or analyzer already answers. You can also ask for it by
name ("use roslyn-analysis to find clones in src/").

## What it does

Pick the lowest layer that answers the question: syntax parsing needs no build and takes seconds; the semantic model
loads the whole solution but binds names to real symbols; metadata answers questions about the built binary.

| Question | Layer | Tool |
|---|---|---|
| Where is this body duplicated, even with renamed variables? | syntax | `references/detect-clones.cs` |
| Every implementation, override, caller and reference of X | semantic model | `references/sweep-symbol.cs`, or the LSP tool |
| Apply one structural edit everywhere | syntax (+ semantic when needed) | `dotnet format` first, then `references/rewrite-template.cs` |
| What did the build actually emit? | metadata / IL | `references/inspect-assembly.cs`, then ILVerify |

### The helper programs

Each is a single-file app run with `dotnet run <file>.cs -- <args>` (.NET 10 SDK or later). They need no project and
do not change the repo. Copy one to a scratch directory before adapting it; don't commit it to your product repo
unless the team wants a standing check. The Roslyn packages are pinned to `5.0.0`.

| Script | Purpose | Invocation |
|---|---|---|
| [`detect-clones.cs`](references/detect-clones.cs) | Fingerprints every method, constructor, operator, accessor, local function and expression-bodied member body and groups equal fingerprints. Default **type-2** mode replaces identifiers with `$id` and literals with `$lit`, so renamed copies match; `--exact` (**type-1**) matches identical text only. Skips `bin`, `obj`, `.git`, `*.g.cs` and `*.Designer.cs`. Prints files scanned, clone sets as `file:start-end`, and duplicated lines with a percentage. | `dotnet run detect-clones.cs -- <root> [--min-tokens 75] [--exact] [--top 25] [--exclude Generated,tests]` |
| [`sweep-symbol.cs`](references/sweep-symbol.cs) | Loads the solution (`.sln` or `.slnx`) with `MSBuildWorkspace` and, via `SymbolFinder`, lists implementations, derived classes, overrides and every reference of a type or one of its members. Candidate (not fully bound) locations are marked, multi-target duplicates removed, and each target ends with a location count. Pass the metadata name (`Outer+Nested`, `` Generic`1 ``). | `dotnet run sweep-symbol.cs -- <path/to/X.sln\|.slnx> <Namespace.Type> [MemberName]` |
| [`rewrite-template.cs`](references/rewrite-template.cs) | A `CSharpSyntaxRewriter` harness. Dry run by default; `--write` applies. Keeps each file's BOM and line endings, never trims whitespace, refuses to write a result that doesn't parse, and reports `HAND-EDIT` for a member whose comment, doc comment or `#if` would be lost. Its example transform removes an attribute by exact simple name (`Obsolete` matches `[Obsolete]`, `[ObsoleteAttribute]`, `[System.Obsolete]`, not `[ObsoleteSoon]`); replace it with your own rewriter. | `dotnet run rewrite-template.cs -- <root> <AttributeName> [--write]` |
| [`inspect-assembly.cs`](references/inspect-assembly.cs) | Reads a built assembly with `System.Reflection.Metadata` only (no packages; the assembly is never loaded or run). With one argument it lists assembly references, manifest resources, types with visibility, and methods. With a type and method it prints the IL of every overload, with call/field/type operands resolved to names and branch targets as labels (exception-handler regions are not printed). | `dotnet run inspect-assembly.cs -- <x.dll>` or `dotnet run inspect-assembly.cs -- <x.dll> <Ns.Type> <Method>` |

### The procedures

1. **Duplication.** Run `detect-clones.cs`, quoting the threshold and mode alongside the percentage. Then triage
   each set with the semantic model: if the bodies call the same members and differ only in a constant, a
   `SyntaxKind` or a delegate, extract one helper; if they call different members in the same pattern, extract only
   when the pattern is the rule; don't merge look-alikes that will diverge. Re-run the detector and add a drift test.
   For fragment clones inside otherwise different methods, lower `--min-tokens` or use a pinned token-window tool
   such as jscpd.
2. **Sibling sweep.** Use the LSP tool first when a C# language server is configured; otherwise `sweep-symbol.cs`.
   Sweep both arms of a pair (reader and writer, sync and async).
3. **Mechanical refactor.** Prefer `dotnet format analyzers <sln> --diagnostics <ID> --severity info` or
   `dotnet format style` when an existing fix expresses the change. Otherwise adapt `rewrite-template.cs`. Step up
   to the semantic model only when the change depends on binding, and compare symbols
   (`SymbolEqualityComparer.Default`), not names. Edit the tree, not the text. The build, the tests and a read of
   the diff are the verdict.
4. **Built assembly.** Use `inspect-assembly.cs`; check generated or rewritten IL with ILVerify; use `ilspycmd` for a
   readable decompile. Both are tool installs: pin the version and get approval first.

## Why it works this way

| Rule | The failure it prevents |
|---|---|
| Roslyn, not grep, for sweeps | Text search misses aliases, `using static`, explicit interface implementations, extension calls and overrides, and matches unrelated same-named symbols. |
| A clone set is only a candidate | Fingerprints are syntax: two bodies with the same shape that call different methods get the same hash. |
| Don't merge look-alikes that will diverge | A false merge that couples independent rules is worse than the duplication. |
| Quote threshold and mode with the percentage | Otherwise the number cannot be reproduced. |
| Sweep both arms | A sweep of one symbol does not cover its twin. |
| Prefer `dotnet format` / an existing code fix | That is one supported mechanism; a custom rewriter beside it is a second one. |
| Preserve BOM and line endings; never trim; never `NormalizeWhitespace()` a file | Trimming whitespace changes verbatim and raw string literals. |
| Refuse unparseable output; report lost comments | The upstream rewriter pasted a lost comment in front of the declaration, which commented the declaration out. |
| Compare symbols, not names; check the replaced expression's type | A name check matches every unrelated type with that name; a `var` local or an overload chosen from the old type silently rebinds. |
| Metadata-only assembly reads | `Assembly.LoadFrom` can run module initializers and fails when a dependency is missing. Use `MetadataLoadContext` if you need the reflection object model. |
| `ManifestResources.Count == 0` is narrow | It says only that the DLL embeds no manifest resource; loose files in the package or output folder are a separate question. |
| Pinned installs, never `npx --yes` | An unpinned install runs whatever is current. |
| All `Microsoft.CodeAnalysis.*` on one version | The files pin `5.0.0` (4.14 cannot open `.slnx`). Bump them together. `MSBuildLocator.RegisterDefaults()` must run before any MSBuild-backed call. |
| Sorted, deterministic output with counts | Two runs can be diffed, and a zero result can be checked. |

The attribution in `SKILL.md` records why the helpers were rewritten rather than copied: the upstream `--exact`
mode still reduced identifiers to their kind, and the upstream assembly inspector used a reflection loader.

## Using it in your project

Prerequisites: the .NET 10 SDK or later (for single-file `dotnet run`), and network access for the NuGet restore of
each script's pinned `#:package` lines; the scripts themselves make no network calls. `inspect-assembly.cs` needs no
packages. A configured C# language server makes the LSP tool the first choice for single-symbol sweeps.

The skill does not list project hooks of its own; adapt the helpers to your needs in a scratch copy (for example,
replacing `rewrite-template.cs`'s example transform). Keep the safety rules when you do: read under the root you
pass, write only with `--write` and only under that root.

**Sibling skills.**

- [`engineering-standards`](../engineering-standards/SKILL.md) is the bar this toolkit serves: one rule in one place,
  every bug is a pattern, standard tools for solved problems, verify values, pin every collapse with a drift test.
- [`variant-analysis`](../variant-analysis/SKILL.md) owns the sweep method (name the mechanism, query every form,
  record the queries); this skill supplies the Roslyn queries.
- [`review`](../review/SKILL.md): its duplication-and-efficiency dimension should run `detect-clones.cs` over the
  changed projects, and `sweep-symbol.cs` for every confirmed finding, citing the output as evidence.
- [`dotnet-engineering`](../dotnet-engineering/README.md) covers the rest of the .NET bar.

See [`SKILL.md`](SKILL.md) for the full rules.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The toolkit: layer choice, the four procedures, safety rules, standards |
| [`references/detect-clones.cs`](references/detect-clones.cs) | Structural (type-2) or exact (type-1) clone detector |
| [`references/sweep-symbol.cs`](references/sweep-symbol.cs) | Semantic sweep of implementations, overrides and references |
| [`references/rewrite-template.cs`](references/rewrite-template.cs) | Safe syntax-rewriter harness with an example transform |
| [`references/inspect-assembly.cs`](references/inspect-assembly.cs) | Metadata listing and IL dump of a built assembly |
| [`references/THIRD-PARTY-NOTICES.md`](references/THIRD-PARTY-NOTICES.md) | Upstream attribution and the MIT license text |

## Credits / license

Adapted from [glennawatson/CSharpAgentSkills](https://github.com/glennawatson/CSharpAgentSkills) (commit
`e28fb30ebb7de61b528d2c14f40f7bcd6586a894`), paths `skills/roslyn-duplicate-detection/`, `skills/roslyn-rewriters/`
and `skills/csharp-assembly-inspection/`, used under the MIT License (Copyright (c) 2026 Glenn Watson and
Contributors). The three skills were merged into one toolkit and the helper programs rewritten after vetting; a
`SymbolFinder` semantic sweep was added, and the unpinned `npx --yes` install, the Sonar framing and the
project-specific examples were removed. The full list of changes is in the attribution block at the top of
[`SKILL.md`](SKILL.md); the license text is in
[`references/THIRD-PARTY-NOTICES.md`](references/THIRD-PARTY-NOTICES.md).
