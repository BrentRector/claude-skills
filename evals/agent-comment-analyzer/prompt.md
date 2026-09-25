---
name: agent-comment-analyzer
description: A comment justifies an omission by citing a real clause about something else; the comment-analyzer agent checks that the cited clause answers the question the comment raises and finds the clause that actually governs.
tags: [comment-analyzer, agent]
runs: 3
max_turns: 12
timeout_seconds: 420
allowed_tools: [Agent, Read, Grep, Glob]
expected_outcome: Flags that §5.1 is about which characters PAD WITH literals may use, not whether short text fields are padded; §4.3 rule 2 requires space-filling, so the comment justifies a real conformance gap.
---

Please check the comments and citations in this change for accuracy - use a specialist comment reviewer if you have one. Everything needed is below; don't look for a repo.

Excerpt of the RLF 2.1 standard the code implements:

> **4.3 Text fields**
> 1. A text field of width W holds characters from the RLF repertoire.
> 2. When the text is shorter than W, the field is filled on the right with the PAD character, which is a space unless a PAD WITH clause specifies another.
>
> **5.1 Implementation-defined elements**
> 1. The set of characters that may appear in a PAD WITH literal is implementation-defined.
> 2. The maximum record length is implementation-defined.

The change:

```csharp
public static string WriteText(string value, int width)
{
    if (value.Length > width) throw new RlfException($"Text longer than {width}");
    // Padding of short text fields is implementation-defined (RLF 2.1 §5.1), so we emit them unpadded.
    return value;
}
```

Keep the answer under 150 words.
