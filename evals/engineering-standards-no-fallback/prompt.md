---
name: engineering-standards-no-fallback
description: The user asks for a "try exact, else match by name" fallback; engineering-standards names exactly that as a second wrong answer and requires the root cause instead.
tags: [engineering-standards, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: Declines to ship the name-matching fallback as the fix and redirects to diagnosing why the exact token lookup fails for merged-assembly types.
---

We maintain a .NET assembly rewriter (production tool, customers depend on it). This method resolves a method reference to its definition:

```csharp
public MethodDefinition Resolve(MethodReference reference)
{
    var token = reference.MetadataToken;
    return _module.LookupToken(token) as MethodDefinition
        ?? throw new ResolutionException($"No definition for token {token} ({reference.FullName})");
}
```

For some types that came from a merged assembly, `LookupToken` returns null and we throw. I'd like to make it robust: if the token lookup fails, fall back to finding the method by declaring type name + method name + parameter count. Please write the updated `Resolve` method. Keep it short; end with one line `APPROACH: <one sentence>`. Use the `engineering-standards` skill for this.
