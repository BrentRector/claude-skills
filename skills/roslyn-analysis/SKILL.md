---
name: roslyn-analysis
description: Use in C#/.NET code when a review or refactor needs facts from the compiler rather than from grep - finding duplicated method bodies and near-clones across a solution, listing every implementation, override, caller and reference of a mechanism for a sibling sweep, applying one mechanical change across many files with a syntax rewriter that preserves comments and formatting, or inspecting a built assembly's metadata and IL to check what the compiler actually emitted. Read-only by default. Not for one-off edits or for questions a build or analyzer already answers.
---

> **Attribution.** Adapted from [glennawatson/CSharpAgentSkills](https://github.com/glennawatson/CSharpAgentSkills)
> `skills/roslyn-duplicate-detection/`, `skills/roslyn-rewriters/` and `skills/csharp-assembly-inspection/`
> (MIT; notice in `references/THIRD-PARTY-NOTICES.md`). Changes: merged into one toolkit organized around the
> review dimensions; the helper programs were rewritten after vetting found defects in the originals.
> - Clone detector: the `--exact` mode now keeps token text (the original still reduced identifiers to their kind).
>   Excludes are matched on root-relative path segments, nested bodies are counted once, and output is sorted.
> - Rewriters: files keep their BOM and line endings, and whitespace is not trimmed (trimming changed verbatim and raw
>   strings). Attributes match by exact name, not substring. A comment that would be lost is reported instead of
>   being pasted in front of the declaration, which commented the declaration out. A result that does not parse is
>   refused.
> - Assembly inspection: the reflection loader was replaced with metadata-only reads, and an IL listing was added.
> - Removed: the unpinned `npx --yes` install, the Sonar framing, and the project-specific examples.
> - Added: a semantic sweep using `SymbolFinder`.

# Roslyn analysis

grep matches text. Roslyn reads C# the way the compiler does. Use it when the answer has to be correct across the whole
solution: *is this logic written twice?*, *who else implements this rule?*, *change this shape in 400 files
without breaking one*, and *what did the compiler actually emit?* This skill gives the owner's **duplication and
efficiency** and **sibling sweep** review steps a tool that finds renamed copies, aliases, explicit interface
implementations and extension-method calls, which a text search misses.

The four helper programs are in `references/`. Each is a single-file app that runs with `dotnet run <file>.cs --
<args>` (.NET 10 SDK or later). They need no project and do not change the repo. Copy one to a scratch directory
before you adapt it. Do not commit it to the product repo unless the team wants a standing check.

| Question | Layer | Tool |
|---|---|---|
| Where is this body duplicated, even with renamed variables? | syntax | `references/detect-clones.cs` |
| Every implementation, override, caller and reference of X | semantic model | `references/sweep-symbol.cs`, or the LSP tool |
| Apply one structural edit everywhere | syntax (+ semantic when needed) | `dotnet format` first, then `references/rewrite-template.cs` |
| What did the build actually emit? | metadata / IL | `references/inspect-assembly.cs`, then ILVerify |

Pick the lowest layer that answers the question. Parsing syntax needs no build and takes seconds. The semantic
model loads the whole solution, which is slower but binds names to real symbols. Reading metadata answers
questions about the built binary, which neither source layer can.

## 1. Duplicated logic and near-clones

`detect-clones.cs <root> [--min-tokens 75] [--exact] [--top 25] [--exclude Generated,tests]` fingerprints every
method, constructor, operator, accessor, local function and expression-bodied member body. In the default
**type-2** mode it replaces identifiers with `$id` and literals with `$lit`, so a copy that only renamed things still
matches. `--exact` (**type-1**) matches identical text only. The output lists clone sets as `file:start-end`, plus
the duplicated line count and percentage. Always quote the threshold and mode with the percentage, or the number
cannot be reproduced.

A fingerprint only nominates candidates. It is syntax, not meaning: two bodies with the same shape that call
different methods get the same hash. For each set, check it with the semantic model before you act:

1. **Compare what the bodies bind to.** Look up the invoked members (use `sweep-symbol.cs` or the LSP tool on each
   call site). If the bodies call the same members and differ only in a constant, a `SyntaxKind` or a delegate,
   they are one rule written twice. Extract it into a single helper with a domain name and parameterize only the
   parts that differ.
2. **If they call different members in the same pattern,** you have a shared algorithm with different steps.
   Extract it only if the pattern is the rule (the same traversal or the same validation order).
   Otherwise leave it alone and note why in the review.
3. **Do not merge look-alikes that will diverge.** A false merge that couples independent rules is worse than
   the duplication. State the reason instead of forcing it.
4. **Run the detector again afterwards.** The extracted set must disappear. Add a drift test that fails if the
   second copy comes back (see engineering-standards §5).

The detector works on whole bodies. It will not find a six-line run inside two otherwise different methods.
For fragment clones, lower `--min-tokens` on the detector, or run a token-window detector such as jscpd. Install
a **pinned** version deliberately. Never run `npx --yes` on an unpinned package.

## 2. Every implementation and caller: the sibling sweep

When a defect is confirmed, the sweep needs every place the same mechanism lives. Text search misses aliases,
`using static`, explicit interface implementations, extension calls and overrides. It also matches unrelated
symbols that share the name.

- **The LSP tool comes first** when a C# language server is configured. `findReferences`, `goToImplementation`
  and call hierarchy answer one symbol at a time without a separate build.
- **`sweep-symbol.cs <sln> <Namespace.Type> [Member]`** lists implementations, derived classes, overrides and every
  reference in the whole solution through `SymbolFinder`. Candidate (not fully bound) locations are marked, and
  duplicates from multi-targeted projects are removed. Pass the metadata name: `Outer+Nested`, `` Generic`1 ``.
- **Two arms:** sweep both halves of a pair, such as the reader and the writer, the validating twin and the
  value-producing twin, or the sync and async versions. A sweep of one symbol does not cover its twin.

The sweep method belongs to the **variant-analysis** skill: name the mechanism, query every form it takes, and
record the queries so that a zero result counts as evidence. This skill supplies the Roslyn queries only.

## 3. Mechanical refactors with syntax rewriters

Use this when the same structural change is needed in many files and a regex would guess at C# structure
(generics, trivia, strings, `#if`).

1. **Prefer the official tool.** If an analyzer or IDE code fix already expresses the change, apply it across
   the solution with `dotnet format analyzers <sln> --diagnostics <ID> --severity info`, or
   `dotnet format style` for IDE rules. That is one supported mechanism, so do not write a second one.
2. **Otherwise adapt `rewrite-template.cs`.** It is a `CSharpSyntaxRewriter` harness that runs as a dry run by
   default and applies changes only with `--write`. It keeps each file's BOM and line endings, never trims
   whitespace, refuses to write a result that does not parse, and reports a member for a hand edit rather than
   silently dropping a comment, doc comment or `#if` directive. Its example transform removes an attribute
   by exact simple name.
3. **Step up to the semantic model only when the change depends on binding**, such as "only when the receiver
   is already `IQueryable<T>`" or "only calls to *our* `Parse`". Load the solution as `sweep-symbol.cs` does.
   Compare the symbol, not its name: `SymbolEqualityComparer.Default.Equals(model.GetSymbolInfo(node).Symbol,
   target)`. A check that matches the name alone also matches every unrelated type with that name. Before
   you remove or replace an expression, check that nothing depends on its **type**. A `var` local or an overload
   chosen from the old type silently rebinds.
4. **Edit the tree, not the text.** Use `ReplaceNode(s)`, `With*` and `SyntaxFactory`. Never call
   `NormalizeWhitespace()` on a whole file. Take new line endings from the file, not from the platform.
5. **The build is the verdict.** Run `dotnet build` with warnings as errors, then the tests, then read `git
   diff` on a sample that includes the odd cases. The harness exiting cleanly does not prove the edit is
   correct.

## 4. Inspecting the built assembly

Source analysis cannot tell you what shipped. When the question is "did the compiler or generator emit
what we meant?", read the binary:

- **`inspect-assembly.cs <x.dll>`** lists assembly references, manifest resources, types (with visibility) and
  methods. **`inspect-assembly.cs <x.dll> <Ns.Type> <Method>`** prints the IL of every overload of that method,
  with call, field and type operands resolved to names and branch targets as labels. It uses
  `System.Reflection.Metadata` only, so it installs no package and never loads or runs the assembly.
- **Do not use `Assembly.LoadFrom` for inspection.** Loading can run module initializers and fails when a
  dependency is missing. If you need the reflection object model (member signatures, custom attributes as
  objects), use `System.Reflection.MetadataLoadContext`, which loads metadata only.
- **Check that the IL is valid** with ILVerify (`dotnet-ilverify`, from dotnet/runtime) for any assembly you
  generated or rewrote. For a readable decompile, use `ilspycmd` (third-party, MIT). Both are tool installs, so
  pin the version and get approval before installing.
- `ManifestResources.Count == 0` means only that the DLL embeds no manifest resource. Loose files in the package
  or output folder are a separate question. List those with `unzip -l x.nupkg` or a directory listing.

## Safety rules for any helper you adapt

- It reads under the root you pass and writes only with `--write`, and only files under that root. It makes
  no network calls at run time. The only network use is the NuGet restore of its pinned `#:package` lines.
- Keep every `Microsoft.CodeAnalysis.*` package on the **same** version; the files pin `5.0.0` (4.14 cannot open
  `.slnx`, 5.0.0 can). Bump them together to the latest stable: the helpers ship nothing, so they need not match
  the target repo's compiler. `MSBuildWorkspace` also needs `Microsoft.Build.Locator`, and `RegisterDefaults()`
  must run before any MSBuild-backed call.
- Output is sorted and deterministic, so two runs can be diffed. Every report states the count it found, so a zero
  result can be checked.

## Standards

The bar is the **engineering-standards** skill. This toolkit serves these rules from it:

- **One rule in one place, one mechanism per job.** A clone set is a candidate. When the semantic check
  confirms it, the extraction is the fix, and every copy moves to the helper in the same change.
- **Every bug is a pattern.** The semantic sweep supplies the evidence for the sibling sweep. Show the query and
  its count, because "swept" without a query is only an assertion.
- **Use the standard tool for a solved problem.** Use `dotnet format` or an existing code fix before a custom
  rewriter, and Roslyn before regex. Never write a second parser beside the compiler.
- **Verify the values, not "it ran".** A rewrite is done when the build, the tests and a read of the diff agree.
  A generator is done when its emitted IL has been inspected and passes ILVerify.
- **Pin every collapse with a drift test,** so a duplicate that has been removed cannot quietly return.

The **review** skill's duplication-and-efficiency dimension should run `detect-clones.cs` over the changed
projects. It should also run `sweep-symbol.cs` for every confirmed finding and cite the output as that finding's
evidence.
