#!/usr/bin/env dotnet run
#:package Microsoft.CodeAnalysis.CSharp@5.0.0

// Structural clone detector (read-only). Fingerprints every method, constructor,
// operator, accessor, local-function and expression-bodied property/indexer body
// as a token-KIND stream and groups equal fingerprints.
//   default  : type-2 - identifiers -> $id, literals -> $lit, so a renamed copy matches
//   --exact  : type-1 - token text kept verbatim (identical code only)
// It is syntactic: two bodies that call DIFFERENT methods with the same shape still
// match in type-2 mode. Triage every set semantically before extracting anything.
//
// Usage: dotnet run detect-clones.cs -- <root> [--min-tokens N] [--exact] [--top K]
//                                       [--exclude dir1,dir2]
// Excluded by default: any path segment bin, obj or .git, and *.g.cs / *.Designer.cs.
// Nothing is written; output is deterministic (files and sets are sorted).

using System.Security.Cryptography;
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

var root = ".";
var minTokens = 75;
var exact = false;
var top = 25;
var excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "bin", "obj", ".git" };
for (var i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--min-tokens": minTokens = int.Parse(args[++i]); break;
        case "--exact": exact = true; break;
        case "--top": top = int.Parse(args[++i]); break;
        case "--exclude": excluded.UnionWith(args[++i].Split(',')); break;
        case var a when a.StartsWith("--"): throw new ArgumentException($"unknown option {a}");
        default: root = args[i]; break;
    }
}

// Exclusion is decided on the path RELATIVE to the root, segment by segment, so a
// checkout that happens to live under a folder named "tools" is not skipped wholesale.
var files = Directory.EnumerateFiles(root, "*.cs", SearchOption.AllDirectories)
    .Select(f => Path.GetRelativePath(root, f))
    .Where(rel => !rel.Split('/', '\\').SkipLast(1).Any(excluded.Contains)
               && !rel.EndsWith(".g.cs") && !rel.EndsWith(".Designer.cs"))
    .Order(StringComparer.Ordinal)
    .ToList();

var groups = new Dictionary<string, List<Body>>();
long totalLines = 0;
foreach (var rel in files)
{
    var tree = CSharpSyntaxTree.ParseText(File.ReadAllText(Path.Combine(root, rel)), path: rel);
    totalLines += tree.GetText().Lines.Count;
    foreach (var body in tree.GetRoot().DescendantNodes().Select(BodyOf).OfType<SyntaxNode>())
    {
        var tokens = body.DescendantTokens().ToList();
        if (tokens.Count < minTokens) continue;

        var fingerprint = new StringBuilder();
        foreach (var token in tokens) fingerprint.Append(Canonical(token, exact)).Append(' ');
        var key = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(fingerprint.ToString())));

        var span = tree.GetLineSpan(body.Span);
        if (!groups.TryGetValue(key, out var set)) groups[key] = set = [];
        set.Add(new Body(rel, span.StartLinePosition.Line + 1, span.EndLinePosition.Line + 1));
    }
}

var cloneSets = groups.Values.Where(g => g.Count > 1).ToList();

// Duplicated lines = every instance past the first, as a UNION of (file, line), so a
// local function nested inside a cloned method is not counted twice.
var duplicated = new HashSet<(string File, int Line)>();
foreach (var set in cloneSets)
    foreach (var b in set.Skip(1))
        for (var line = b.Start; line <= b.End; line++) duplicated.Add((b.File, line));

Console.WriteLine($"Files scanned:    {files.Count}");
Console.WriteLine($"Lines (all):      {totalLines}");
Console.WriteLine($"Clone sets:       {cloneSets.Count}  (>= {minTokens} tokens, {(exact ? "type-1 exact" : "type-2 structural")})");
Console.WriteLine($"Duplicated lines: {duplicated.Count}  ({(totalLines == 0 ? 0 : 100.0 * duplicated.Count / totalLines):F2}%)");
Console.WriteLine();
foreach (var set in cloneSets
             .OrderByDescending(s => (s.Count - 1) * (s[0].End - s[0].Start + 1))
             .ThenBy(s => s[0].File, StringComparer.Ordinal).ThenBy(s => s[0].Start)
             .Take(top))
{
    Console.WriteLine($"  x{set.Count}  ~{set[0].End - set[0].Start + 1} lines each:");
    foreach (var b in set) Console.WriteLine($"      {b.File}:{b.Start}-{b.End}");
}

static SyntaxNode? BodyOf(SyntaxNode node) => node switch
{
    BaseMethodDeclarationSyntax m => (SyntaxNode?)m.Body ?? m.ExpressionBody,   // methods, ctors, operators, finalizers
    LocalFunctionStatementSyntax f => (SyntaxNode?)f.Body ?? f.ExpressionBody,
    AccessorDeclarationSyntax a => (SyntaxNode?)a.Body ?? a.ExpressionBody,
    PropertyDeclarationSyntax p => p.ExpressionBody,
    IndexerDeclarationSyntax x => x.ExpressionBody,
    _ => null,
};

static string Canonical(SyntaxToken token, bool exact) => exact ? token.Text : token.Kind() switch
{
    SyntaxKind.IdentifierToken => "$id",
    SyntaxKind.StringLiteralToken or SyntaxKind.NumericLiteralToken or SyntaxKind.CharacterLiteralToken
        or SyntaxKind.InterpolatedStringTextToken or SyntaxKind.Utf8StringLiteralToken
        or SyntaxKind.SingleLineRawStringLiteralToken or SyntaxKind.MultiLineRawStringLiteralToken => "$lit",
    var kind => kind.ToString(),
};

record Body(string File, int Start, int End);
