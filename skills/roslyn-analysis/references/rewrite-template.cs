#!/usr/bin/env dotnet run
#:package Microsoft.CodeAnalysis.CSharp@5.0.0

// Safe syntax-rewriter harness. DRY RUN by default; --write applies.
// Example transform: remove an attribute by exact simple name from every member
// (`Obsolete` matches [Obsolete], [ObsoleteAttribute], [System.Obsolete]; it does NOT
// match [ObsoleteSoon]). Replace RemoveAttribute with your own CSharpSyntaxRewriter.
//
// Safety properties this harness keeps - keep them when you adapt it:
//  - only files under <root> are touched, and only when the text actually changed;
//  - the file's BOM and line endings are preserved (no normalization, no trimming:
//    trimming whitespace would change verbatim and raw string literals);
//  - a result that no longer parses is refused, not written;
//  - a member whose removed attribute list carries a comment is REPORTED for a hand
//    edit instead of silently dropping the comment.
//
// Usage: dotnet run rewrite-template.cs -- <root> <AttributeName> [--write]

using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

var write = args.Contains("--write");
var positional = args.Where(a => !a.StartsWith("--")).ToArray();
var (root, attributeName) = (Path.GetFullPath(positional[0]), positional[1]);
string[] excluded = ["bin", "obj", ".git"];

var changed = 0;
foreach (var path in Directory.EnumerateFiles(root, "*.cs", SearchOption.AllDirectories).Order(StringComparer.Ordinal))
{
    if (Path.GetRelativePath(root, path).Split('/', '\\').SkipLast(1).Any(excluded.Contains)) continue;

    var bytes = File.ReadAllBytes(path);
    var hasBom = bytes is [0xEF, 0xBB, 0xBF, ..];
    var text = File.ReadAllText(path);
    var tree = CSharpSyntaxTree.ParseText(text, path: path);

    var rewriter = new RemoveAttribute(attributeName);
    var newText = rewriter.Visit(tree.GetRoot())!.ToFullString();
    foreach (var skipped in rewriter.NeedsHandEdit) Console.WriteLine($"HAND-EDIT {path}:{skipped}");
    if (newText == text) continue;

    var errors = CSharpSyntaxTree.ParseText(newText).GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).ToList();
    if (errors.Count > 0) { Console.WriteLine($"REFUSED   {path}: result does not parse ({errors[0]})"); continue; }

    changed++;
    if (write) File.WriteAllText(path, newText, new UTF8Encoding(hasBom));
    Console.WriteLine($"{(write ? "rewrote" : "would rewrite")} {path}");
}
Console.WriteLine($"{changed} file(s) {(write ? "rewritten" : "would change; re-run with --write, then build, test and read the diff")}.");

sealed class RemoveAttribute(string name) : CSharpSyntaxRewriter
{
    public List<int> NeedsHandEdit { get; } = [];

    public override SyntaxNode? Visit(SyntaxNode? node)
    {
        var visited = base.Visit(node);
        return visited is MemberDeclarationSyntax member ? Strip(member, original: node!) : visited;
    }

    // `original` is the node in the parsed tree (for line numbers); `member` is its rewritten copy.
    private MemberDeclarationSyntax Strip(MemberDeclarationSyntax member, SyntaxNode original)
    {
        var kept = new List<AttributeListSyntax>();
        var removedAny = false;
        var firstRemoved = false;
        foreach (var list in member.AttributeLists)
        {
            var survivors = list.Attributes.Where(a => SimpleName(a) != name).ToList();
            if (survivors.Count == list.Attributes.Count) { kept.Add(list); continue; }
            removedAny = true;
            if (survivors.Count > 0) { kept.Add(list.WithAttributes(SyntaxFactory.SeparatedList(survivors))); continue; }

            // The whole list goes. Its leading trivia is kept below only when it is the FIRST
            // list (that trivia is the member's own); anything else inside or after it is lost.
            var isFirst = list == member.AttributeLists[0];
            firstRemoved |= isFirst;
            var lost = (isFirst ? list.GetTrailingTrivia() : list.GetLeadingTrivia().AddRange(list.GetTrailingTrivia()))
                .Concat(list.DescendantTrivia(list.Span));
            if (lost.Any(IsSignificant)) return HandEdit(member, original);
        }
        if (!removedAny) return member;

        var result = member.WithAttributeLists(SyntaxFactory.List(kept));
        if (!firstRemoved) return result;

        // The member's doc comment and indentation lived on the removed first list. Move them to
        // the new first token, whose own leading trivia (normally bare indentation) they replace.
        if (result.GetFirstToken().LeadingTrivia.Any(IsSignificant)) return HandEdit(member, original);
        return result.WithLeadingTrivia(member.GetLeadingTrivia());
    }

    private MemberDeclarationSyntax HandEdit(MemberDeclarationSyntax member, SyntaxNode original)
    {
        NeedsHandEdit.Add(original.GetLocation().GetLineSpan().StartLinePosition.Line + 1);
        return member;
    }

    // Comments, doc comments and preprocessor directives must never be dropped silently.
    private static bool IsSignificant(SyntaxTrivia t) => t.IsDirective
        || t.IsKind(SyntaxKind.SingleLineCommentTrivia) || t.IsKind(SyntaxKind.MultiLineCommentTrivia)
        || t.IsKind(SyntaxKind.SingleLineDocumentationCommentTrivia) || t.IsKind(SyntaxKind.MultiLineDocumentationCommentTrivia);

    private static string SimpleName(AttributeSyntax attribute)
    {
        var simple = attribute.Name switch
        {
            QualifiedNameSyntax q => q.Right.Identifier.Text,
            AliasQualifiedNameSyntax a => a.Name.Identifier.Text,
            SimpleNameSyntax s => s.Identifier.Text,
            var other => other.ToString(),
        };
        return simple.EndsWith("Attribute", StringComparison.Ordinal) ? simple[..^"Attribute".Length] : simple;
    }
}
