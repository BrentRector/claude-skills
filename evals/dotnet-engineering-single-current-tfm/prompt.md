---
name: dotnet-engineering-single-current-tfm
description: Starting a new library with no named legacy consumer; dotnet-engineering requires one TFM, the current one - no netstandard2.0 and no multi-targeting.
tags: [dotnet-engineering, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The csproj has a single <TargetFramework> for current .NET (net10.0 or later), not <TargetFrameworks> and not netstandard2.0.
---

I'm starting a new open-source C# class library (a parser for a config format) that I want as many people as possible to be able to use. No specific consumer has asked for anything yet. Write me the complete `.csproj` for it. Only the csproj in one code block, then one line of explanation. Use the `dotnet-engineering` skill for this.
