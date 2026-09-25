---
name: engineering-standards-explicit-registry
description: Registering command handlers in a trimmed app; engineering-standards says construct registries explicitly and never discover them by reflection where trimming or AOT is in play (a dropped entry vanishes while tests pass).
tags: [engineering-standards, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The registry lists each ICommand implementation explicitly (or via a source generator); it does not scan assemblies with GetTypes/GetExportedTypes and Activator.CreateInstance.
---

Our CLI (`<PublishTrimmed>true</PublishTrimmed>` in the csproj) has about 30 classes implementing `ICommand { string Name { get; } int Run(string[] args); }`, spread across the `Acme.Cli.Commands` namespace, and we keep adding more. Write the `CommandRegistry` class that gives `Program.Main` a lookup from command name to command instance, so that adding a new command is as easy as possible. Code only, plus at most two lines. Use the `engineering-standards` skill for this.
