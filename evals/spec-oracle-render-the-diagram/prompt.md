---
name: spec-oracle-render-the-diagram
description: Whether a keyword is required is decided by a general-format diagram whose text extraction is suspect; spec-oracle says render the printed page, where underlining (not the extracted text) decides required vs optional, because extraction skews toward falsely restrictive syntax.
tags: [spec-oracle, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: Does not settle it from the Markdown transcription; says to render the actual PDF page and read the notation (underlined keywords are required, non-underlined are optional), noting extraction tends to make syntax look more restrictive than printed.
---

We implement a parser for the RLF 2.1 record-layout standard, which governs this behavior. We keep a Markdown transcription of the standard (extracted from the licensed PDF) in the repo. In it, the general format of the FIELD entry reads:

    FIELD field-name WIDTH IS integer [ PAD WITH literal ]

Our parser therefore requires both `WIDTH` and `IS`. A user reports that `FIELD AMOUNT WIDTH 6` (no `IS`) is legal per the printed standard and our parser wrongly rejects it. The Markdown text shows no brackets around `IS`.

Before anyone touches the parser: how do I decide who is right? Answer in under 100 words. Use the `spec-oracle` skill for this.
