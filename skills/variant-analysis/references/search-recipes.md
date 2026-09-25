# Search recipes

Starting points for the structural and semantic levels. Adapted from trailofbits/skills
`plugins/variant-analysis/skills/variant-analysis/references/searching.md` (CC-BY-SA 4.0); the recipes are
new. Each recipe is a throwaway. Edit the predicate, run it, read every hit. Before trusting a zero, check that
the recipe hits the original instance.

## C#: Roslyn syntax walker (single-file `dotnet run`)

Structural: finds a shape under any names, and needs no build.

```csharp
#:package Microsoft.CodeAnalysis.CSharp@4.*
using Microsoft.CodeAnalysis; using Microsoft.CodeAnalysis.CSharp; using Microsoft.CodeAnalysis.CSharp.Syntax;

foreach (var path in Directory.EnumerateFiles(args[0], "*.cs", SearchOption.AllDirectories))
{
    var root = CSharpSyntaxTree.ParseText(File.ReadAllText(path), path: path).GetRoot();
    // EDIT: the shape. Here: every switch over a member access ending in ".Kind" that has no default arm.
    foreach (var sw in root.DescendantNodes().OfType<SwitchStatementSyntax>())
        if (sw.Expression.ToString().EndsWith(".Kind") &&
            !sw.Sections.SelectMany(s => s.Labels).OfType<DefaultSwitchLabelSyntax>().Any())
            Console.WriteLine($"{path}:{sw.GetLocation().GetLineSpan().StartLinePosition.Line + 1}: {sw.Expression}");
}
```

Run it with `dotnet run walker.cs -- <repo-root>`. Other useful predicates include every `InvocationExpressionSyntax` whose
name is `Round` with fewer than three arguments, every `if` whose condition compares against a named constant,
and every `switch` expression missing an arm for one enum member.

## C#: semantic queries (resolve symbols, not names)

Use these when aliases, `using static`, extension methods or overloads defeat the name match. Open the solution
with `Microsoft.CodeAnalysis.Workspaces.MSBuild` (`MSBuildWorkspace.Create().OpenSolutionAsync(sln)`), then:

- **Every use of a symbol:** `SymbolFinder.FindReferencesAsync(symbol, solution)`.
- **Every override or implementation of a dispatch method:** `SymbolFinder.FindOverridesAsync` and
  `FindImplementationsAsync`. These are the arms, so list them all.
- **Every `switch` over an enum, per missing member:** `semanticModel.GetTypeInfo(sw.Expression).Type` is the
  enum. Compare its members with the case labels. This finds the arms nobody wrote.
- **Every write to a field:** walk `AssignmentExpressionSyntax` and match
  `semanticModel.GetSymbolInfo(assignment.Left).Symbol` against the field.

Cheap alternative: a Roslyn analyzer with a code fix doubles as the regression guard.

## Grammars: ANTLR

- **Rule siblings, textually:** `rg -n '^\s*(\w+)\s*$' -A1 *.g4` lists the rule heads. `rg -n 'KEYWORD' *.g4`
  finds every rule that mentions the phrase.
- **Rule shapes, structurally:** parse the `.g4` files with ANTLR's own `ANTLRv4Parser` (from
  `antlr/grammars-v4`) and walk it with a listener. For example, list every `alternative` that is a fixed sequence
  of two or more `?`-suffixed elements (an order that may be wrongly fixed), or every rule referenced from only
  one parent.
- **Inputs, structurally:** a `ParseTreeListener` over a corpus of source files, with `Enter<Rule>` counting where
  a construct appears and which alternatives are exercised. An alternative that no test ever takes is an arm with
  no coverage.
- **Semantic predicates:** `rg -n '\{[^}]*\}\?' *.g4` lists every gated alternative. Each gate is a dispatch,
  so probe both sides of it.

## Any language: tree-sitter

```scheme
; every call to round() with exactly two arguments (Python grammar)
(call function: (identifier) @f (#eq? @f "round")
      arguments: (argument_list . (_) . (_) .)) @hit
```

Run it with `tree-sitter query query.scm <files>`, or use the py-tree-sitter bindings to walk a whole tree. Use
tree-sitter when no compiler API exists or the code does not build.

## Any language: Semgrep

```yaml
rules:
  - id: floor-division-as-page-bound
    languages: [python, javascript, typescript, java, csharp, go]
    severity: WARNING
    message: page count computed with floor division drops the last partial page
    patterns:
      - pattern: $COUNT / $SIZE
      - metavariable-regex: {metavariable: $SIZE, regex: '(?i).*(size|page|batch).*'}
```

Generalize one element at a time: metavariables for names, then `...` for arguments, then `pattern-inside`
for context, then taint mode only if presence of the shape is not already evidence. Subtract known-safe forms
with `pattern-not` rather than filtering the hits by hand.

## Textual reconnaissance

- Whole repository, including docs and tests: `rg -n --hidden -g '!.git' '<pattern>'`.
- History of the rule: `git log -S '<constant or condition>' --oneline` finds where a copy was introduced.
- Before claiming an identifier as an expansion axis, check that it exists: `rg -c '\bName\b'`.
