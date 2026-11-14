---
name: cross-platform-host-only-witness
description: "A race test reproduces only on the developer's ReFS Dev Drive and never on CI's NTFS runners; cross-platform keeps it as a host-only witness that runs in every local gate, marked by a trait, instead of deleting or quarantining it as flaky."
tags: [cross-platform, skill]
runs: 3
max_turns: 10
timeout_seconds: 480
allowed_tools: [Skill, Read]
expected_outcome: "The test is kept: it is a witness for a filesystem the CI runners do not have, so it gets a trait naming the property (for example Host=ReFS), every local gate runs the tests with that trait whatever the diff, membership comes from the trait, and a drift test checks the known witnesses carry it."
---

We fixed a race in our file-cache cleanup: deleting a file while another handle was still opening it. The new
regression test hammers that path and failed 20 times in 7,200 iterations on my machine before the fix, and 0
after. My source tree is on a Windows Dev Drive (ReFS). On our CI runners (Windows Server, NTFS) the test has never
failed, not even against the old code. A teammate says a test that can't fail in CI is useless and wants to delete
it, or mark it flaky and skip it. What should we do with this test?
