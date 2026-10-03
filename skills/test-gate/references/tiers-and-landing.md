# Tiers: sizing, serial work, landing gates, worktree battery

- **Size the gate to the blast radius, not to anxiety.** Running the full suite on every commit makes the slow
  gate the bottleneck, and a long run that gets waved off is where a real regression slips through as a "flake".
- **Serial work still gets one comprehensive gate.** If a batch has to be built one step at a time (a shared
  parser, a shared schema), run the targeted gate after each step and the comprehensive gate once at the end.
- **A landing gate covers the whole affected assembly, not a hand-picked union of filters.** Merging several
  changes behind `A|B|C|D`, one term per change, leaves out every test that no term names. That leftover set is
  where the breakage shows up, and adding one more term after each failure never covers it. The unfiltered run
  costs less than a red CI run plus a re-push. *(Validated 2026-09-28.)*
- **A change that REJECTS input the tool used to accept runs the whole accepted-input corpus.** A new diagnostic, a
  tightened validation or a stricter parser is a targeted change with a global blast radius: every "this must be
  accepted" sample, fixture and compatibility matrix is now a candidate red. Add that corpus to the change's own gate,
  not only the landing gate. *Why: an implementer gated a tightening on its own tests; the landing gate found 15
  compatibility cases (5 samples at 3 language versions) it had broken.* *(Practice — not yet validated: one use so far.)*
- **The comprehensive gate will turn up tests that the targeted filters never loaded,** including tests that
  still encode behaviour someone deliberately changed. Fix the test so it asserts the new behaviour. Don't
  exclude it.
- **Run the comprehensive gate in its own detached worktree**, cut at the batch head
  (`git worktree add --detach <path> <sha>`, then build and run there), never in the main checkout, when other
  work (edits, landings) goes on while it runs. *Why: a battery that rebuilds mid-run measures whatever the tree
  holds at that moment: on the main checkout one measured a half-finished edit and had to be redone, and nothing
  could land for its whole run (~45 min of machine time; the landing work that blocks was modelled at about seven
  clusters, not measured). From the first worktree battery on, landings continued in parallel. It still competes
  for the same cores, so expect other gates to run slower while it does.* *(Validated 2026-09-28.)*
