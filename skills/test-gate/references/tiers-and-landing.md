# The gate rule, one design that meets it, host-only witnesses

## The rule

**Every case the merge run executes was run green at the head that lands, on this host and toolchain, or a recorded
pass at the same inputs covers it.** The merge run (a merge queue's merge group, or CI on the pushed commit where
there is no queue) is then the first run only of what the local host cannot run: the merged tree, another
operating system, another configuration (Release, a cold compile cache), and CI's own runners. So a red there is
one of those classes, a flake, or infrastructure, never a case nobody ran; classify it as one of them against the
branch's gate record before changing anything (`ci-flakes-standards.md`).

- **Same inputs** means everything the case reads: the sources and data files it loads, the build it runs against,
  the toolchain versions, the configuration. A pass recorded at different inputs covers nothing, and a key that
  leaves an input out is a false green waiting for that input to change.
- **A selection is never the landing gate.** A filter, an impact map or a union of per-change terms (`A|B|C|D`, one
  per change) leaves out every test no term names, and that leftover set is where the breakage shows up; adding one
  more term after each failure never covers it. *Why: in one project's pipeline record about a sixth of the
  defects were false greens, most of them a selection that missed the red, and the fix that held was replacing the
  selection with the whole population.*
- **While developing, run whatever is fast.** An inner-loop run claims nothing; the gate is the run at the head
  that lands, and it is the same gate for an implementer's commit and a re-gate after a fix.

## The worked design: the developer's OS locally, the rest in the merge group

For a project with a merge queue and CI on two operating systems:

- **Locally, on the developer's OS, at the branch head:** a fresh build, then the whole population of every test
  target except the targets a recorded pass at their current inputs covers; every host-only witness (below); the
  audits whose inputs changed. Run it at low priority inside a shared cap on concurrent gates, previous reds first.
- **In the merge group:** every target on the other OS and in the other configurations, and, on the developer's
  OS, each target no recorded pass at the merged tree's inputs covers (the merge changed its inputs). The merge
  group is the only run of the merged tree, so it never skips that half.
- **Why this shape.** Each case the merge group runs on the developer's OS already ran green at that head, so the
  merge group spends its time only on what the host cannot reach. A per-change leg on the other OS locally costs a
  clone and a build on every change; in the project this design comes from, it found one red in 78 records, and
  that one false, while the merge group catches the class on its first run anyway.
- **What it costs.** The whole population per landing is the host's time: without content keys that is the whole
  suite every time (one non-observed case once cost a 58-minute re-run of every passed case). Two practices make it
  affordable: skip what did not change (a target whose inputs are unchanged since its recorded pass is reused, not
  re-run), and no fixed time limits in tests (they were most of the reds a loaded host produced). A red of the other
  OS costs one merge-group round trip.

## When the change's leg should run on both operating systems locally

The older shape, the change's targeted leg natively and then in a clone built on the other OS, under one gate slot
and fail-fast native first, is still right when:

- **there is no merge group**: nothing runs the other OS before the default branch moves, so its reds land on main;
- **the change's own tests often go red only on the other OS**, so a local leg there (about 1–2 min of clone and
  build plus the leg) is cheaper than the round trips. *Why: in one measured campaign 3 of 38 landed changes had
  reds only on the other OS, all in the changes' own tests (a locale golden, a lock-race fix red 10 of 10 on Linux, a
  path-length test), and each was caught by the local other-OS leg before a CI round trip;*
- **a witness reproduces only on a host you have locally** on the other OS.

The other-OS leg is always a clone built on that OS, never the first OS's binaries (`cross-platform`'s
`references/platform-facts.md` says how). CI's full legs on the other OS run locally only to reproduce a CI red; they do not gate.

## Host-only witnesses run in every local gate

Some tests reproduce only on the developer host: typically a filesystem property CI's runners lack (ReFS deletes
differently from NTFS; a delete race reproduced locally in 20 of 7,200 probes may never reproduce on a runner), a
locale, a device. Give each such test class a trait naming the property (xUnit `[Trait("Host", "ReFS")]`, a pytest
marker, a Jest tag), put every test with the trait in the local gate whatever the diff, and DERIVE the membership
from the trait, never a hand-kept list, with a drift test asserting that the known witnesses carry it. CI still
runs them on its own filesystem, where they may pass vacuously.

## Audits are reused when their inputs are unchanged; no test has a fixed time limit

- **A self-test, a drift-rule regeneration or a citation check whose inputs are unchanged since a recorded PASS is
  reused, never re-run**, at every gate. CI's audits job runs them all on every merge group. *Why: in one measured
  wave 18 implementer gates spent 246 of 294 gate-minutes on gates that ran no test leg, because a self-test pool
  timed out under its own load; audits took 80–89 % of a gate's wall under fleet load.*
- **No test carries a fixed wall-clock time limit.** Rewrite it as a deterministic witness, or, where a process must
  be timed, scale the limit from a baseline measured on the same host; add a guard that fails on a new literal time
  limit in a test. *Why: the top recurring red under load was a 120-second harness limit, and every such red cost a
  re-run plus an attribution.*

## Serial work, rejections, deliberate changes

- **Serial work still ends in one whole-population run.** If a batch has to be built one step at a time (a shared
  parser, a shared schema), gate after each step; the last step's gate and the merge group cover the end.
- **A change that REJECTS input the tool used to accept runs the whole accepted-input corpus in its gate**, even
  where the project gates on a selection. A new diagnostic, a tightened validation or a stricter parser has a global
  blast radius: every "this must be accepted" sample, fixture and compatibility matrix is now a candidate red. *Why:
  an implementer gated a tightening on its own tests; the landing gate found 15 compatibility cases (5 samples at 3
  language versions) it had broken.*
- **The whole-population run will turn up tests that encode behaviour someone deliberately changed.** Fix the test
  so it asserts the new behaviour. Don't exclude it.
