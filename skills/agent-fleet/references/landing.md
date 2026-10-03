# Landing finished work

The full text of agent-fleet section 6. Read it before dispatching a lander, running the battery, scripting a rolling wave, or pushing.

## 6. Land finished work before starting new work

- **Land finished work first**, and queue read-only fleets behind landings. *Why: when a limit hit, work that
  was ready still sat waiting on a serialized lander.* *(Practice — not yet validated: landers were still killed mid-landing after it was adopted; the STOP file is what ended that.)*
- **One lander on main at a time, and one landing per lander transcript.** *Why: ordering, and a fresh lander
  keeps each transcript short, since cost grows with turns.* *(Practice — not yet validated: that four landings in one transcript cost about twice as much as four fresh landers is modelled, never measured.)*
- **Batch 4–6 finished clusters per landing**, with one commit per cluster so a red result bisects cleanly.
  *Why: a landing is mostly fixed cost (merge, build, gate, push). Per-cluster cost roughly halves from k=1 to
  k=5, and beyond ~6 the gate becomes hard to attribute.* *(Practice — not yet validated: the per-cluster saving is modelled from the fixed cost, not measured.)*
- **The lander gates the WHOLE test suite, unfiltered**, not the union of the implementers' filters.
  *Why: the tests that no filter names are exactly the ones that go red in CI.* *(Validated 2026-09-28.)*
- **Run the comprehensive battery in its own detached worktree**, cut at the batch head
  (`git worktree add --detach <path> <sha>`), never in the checkout the lander builds in. *Why: the battery
  rebuilds mid-run, so on the shared checkout it measured a half-finished edit (that run was stopped and redone),
  and nothing could land until it finished. One battery took ~45 min of machine time; the lander work that freeze
  blocks was modelled at about seven clusters, not measured. From the first worktree battery on, landings continued
  in parallel. The battery still shares the cores (the lander's gate ran about twice as slow during one), so the
  worktree turns a freeze into a slowdown.* *(Validated 2026-09-28.)*
- **Implementers gate narrowly** (their own tests plus drift and unit checks) at low process priority.
  *Why: when many implementers run the full suite, they triple the lander's gate time.* *(Practice — not yet validated: the slowdown was never measured under control.)*
- **Fill a freed implementer slot in the same turn it frees**, from a standing queue of apply-ready contracts.
  Make it mechanical: run the fix lane as a **rolling wave** (`references/rolling-wave.js`), never as a barrier
  of "N implementers, then one train". N workers pull groups from one queue, so a slot refills the moment its
  agent returns. A lander train starts as soon as enough branches (4–6) are ready, and trains are serialized.
  *Why: idle slots behind landings once held a fix lane under 15 % utilization for days, and under a wave
  barrier every finished slot waits for the slowest group of its wave.* *(Filling a freed slot in the same turn:
  validated 2026-09-28. The rolling-wave script: practice, not yet validated: no A/B against the barrier.)* Keep a workflow script LF-only. *Why: a
  Workflow tool refused a script whose CRLF line endings (from Python's `write_text` on Windows) read as hidden
  control characters.* *(Practice — not yet validated: the LF rule has held since, but has not been re-validated on its own.)*
- **Watch CI for every pushed head.** A red run is a blocking fix, landed alone. *(Validated 2026-09-28.)*
- **Run CI's other-OS legs locally before pushing.** When CI runs on an operating system your agents' gates do not
  (Linux CI, Windows gates), give every gate a local run of those legs, for example under WSL, and write it into
  the briefs and the brief checker, not into memory.
  - Measure the legs before deciding who runs what. In the incident below, the whole other-OS population took about
    5 minutes, so every implementer and every lander runs all of it. A detector that adds the expensive legs only
    for "platform-sensitive" diffs (OS checks, path APIs, drive letters, shells, newlines) was built and dropped
    the same night: at that cost no selection is worth its misses. If your legs are expensive, such a detector may
    ADD a leg, but never remove one or select tests.
  - Reuse the Windows-built binaries where IL is portable, but BUILD on the target OS for any test that embeds build
    paths (`[CallerFilePath]`, source-relative fixtures), or it false-reds.
  - Make git readable from the other OS: a Windows worktree's `.git` file names a Windows path, and mounted trees
    trip git's ownership check.
  - Keep a drift test holding the local legs equal to the CI jobs' test projects.
  *Why: a new test planted a Windows path literal that `Path.GetFullPath` treats as relative on Linux. It was green
  in every Windows gate and red in CI's Linux unit job. The CI round trip cost ~30 minutes and dropped the cluster;
  the local unit leg reproduced exactly that one red in about 2.5 minutes. The practice had existed only as a memory
  note, so no agent ran it.* *(Practice — not yet validated: built after one incident; not yet exercised across
  waves.)*
