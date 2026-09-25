---
name: roslyn-analysis-safe-rewriter
description: A mechanical edit across hundreds of C# files; roslyn-analysis prefers dotnet format / an existing code fix, else its bundled rewrite-template.cs harness (dry run by default, preserves BOM and line endings, refuses unparseable output) - never a whole-file NormalizeWhitespace.
tags: [roslyn-analysis, skill]
runs: 3
max_turns: 8
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob]
expected_outcome: Points at the bundled rewrite-template.cs harness (dry run first, then --write) or dotnet format, rather than a hand-written rewriter that normalizes whitespace.
---

I need to remove every `[ExcludeFromCodeCoverage]` attribute across ~400 C# files in `C:\src\Ledger` (.NET 10 SDK installed). A regex will mangle attribute lists like `[Serializable, ExcludeFromCodeCoverage]`, so I want a Roslyn-based mechanical rewrite. What should I run? Give the command(s) in one code block and at most four lines of explanation.
