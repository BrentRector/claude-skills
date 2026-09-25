#!/usr/bin/env dotnet run
#:package Microsoft.Build.Locator@1.7.8
#:package Microsoft.CodeAnalysis.CSharp.Workspaces@5.0.0
#:package Microsoft.CodeAnalysis.Workspaces.MSBuild@5.0.0

// Semantic sibling sweep (read-only). Loads the solution, resolves a type (and
// optionally one member name) by metadata name, and prints every implementation,
// derived class, override and reference in the WHOLE solution - bound symbols, not
// text matches, so an alias, a `using static`, an explicit interface implementation
// or an extension-method call is found and a same-named unrelated symbol is not.
//
// Usage: dotnet run sweep-symbol.cs -- <path/to/X.sln|.slnx> <Namespace.Type`1> [MemberName]
// Keep every Microsoft.CodeAnalysis.* package on the SAME version; bump all together.

using Microsoft.Build.Locator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.MSBuild;

MSBuildLocator.RegisterDefaults();   // before any MSBuild-backed call
using var workspace = MSBuildWorkspace.Create();
workspace.RegisterWorkspaceFailedHandler(e => Console.Error.WriteLine($"[workspace] {e.Diagnostic}"));
var solution = await workspace.OpenSolutionAsync(args[0]);

INamedTypeSymbol? type = null;
foreach (var project in solution.Projects)
{
    type = (await project.GetCompilationAsync())?.GetTypeByMetadataName(args[1]);
    if (type is not null) break;   // one compilation's symbol suffices; SymbolFinder maps it across projects
}
if (type is null) { Console.Error.WriteLine($"type {args[1]} not found in any project"); return 1; }

ISymbol[] targets = args.Length > 2 ? [.. type.GetMembers(args[2])] : [type];
if (targets.Length == 0) { Console.Error.WriteLine($"{args[1]} has no member {args[2]}"); return 1; }

foreach (var target in targets)
{
    Console.WriteLine($"== {target.ToDisplayString()}");
    var lines = new SortedSet<string>(StringComparer.Ordinal);   // dedupes multi-target (linked) documents

    if (target is INamedTypeSymbol { TypeKind: TypeKind.Interface } iface)
        foreach (var s in await SymbolFinder.FindImplementationsAsync(iface, solution)) lines.Add(Line("implements", s));
    else if (target is INamedTypeSymbol cls)
        foreach (var s in await SymbolFinder.FindDerivedClassesAsync(cls, solution, transitive: true)) lines.Add(Line("derives", s));

    if (target is IMethodSymbol or IPropertySymbol or IEventSymbol)
    {
        foreach (var s in await SymbolFinder.FindOverridesAsync(target, solution)) lines.Add(Line("overrides", s));
        foreach (var s in await SymbolFinder.FindImplementationsAsync(target, solution)) lines.Add(Line("implements", s));
    }

    foreach (var referenced in await SymbolFinder.FindReferencesAsync(target, solution))
        foreach (var location in referenced.Locations)
        {
            var span = location.Location.GetLineSpan();
            var note = location.IsCandidateLocation ? $"  (candidate: {location.CandidateReason})" : "";
            lines.Add($"  ref        {span.Path}:{span.StartLinePosition.Line + 1}{note}");
        }

    foreach (var line in lines) Console.WriteLine(line);
    Console.WriteLine($"  -- {lines.Count} location(s)");
}
return 0;

static string Line(string relation, ISymbol symbol)
{
    var span = symbol.Locations.FirstOrDefault(l => l.IsInSource)?.GetLineSpan();
    return $"  {relation,-10} {symbol.ToDisplayString()}  {span?.Path}:{span?.StartLinePosition.Line + 1}";
}
