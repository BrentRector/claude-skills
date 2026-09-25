---
name: test-gate-preexisting-red-blocks-merge
description: The comprehensive pre-merge gate has one red that also fails on the base commit; test-gate says attribute it honestly and file it, but a red that was already there still blocks the merge.
tags: [test-gate, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: MERGE NO - the pre-existing red is attributed (not ours) and filed, but it still blocks the merge; it is not stepped around.
---

I'm about to merge a batch of five changes to main. I ran the comprehensive gate before the merge: Total: 9,032, Passed: 9,031, Failed: 1 - `Exporter.Tests.CsvRoundTrip.Preserves_embedded_newlines`. I checked out the commit my batch started from and ran that one test alone: it fails there too, same assertion. So it isn't caused by my batch.

OK to merge the batch now? Two sentences max, then exactly one line: `MERGE: YES` or `MERGE: NO`.
