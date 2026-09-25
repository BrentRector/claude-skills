---
name: roslyn-analysis-renamed-clones
description: Finding duplicated method bodies across a C# solution even when identifiers were renamed; roslyn-analysis points at its bundled type-2 clone detector (detect-clones.cs).
tags: [roslyn-analysis, skill]
runs: 3
max_turns: 8
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob]
expected_outcome: Gives a `dotnet run ... detect-clones.cs -- <root>` command (default type-2 mode, renamed identifiers match) and says to confirm each clone set with the semantic model before extracting.
---

I'm doing a duplication review of a large C# solution at `C:\src\Ledger` (.NET 10 SDK installed). I suspect several method bodies were copy-pasted and then had their variables renamed, so grep won't find them. What exact command should I run to list the duplicated method bodies? Give the command in one code block and at most three lines of explanation.
