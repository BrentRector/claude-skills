# Tiers: the targeted local gate, CI as the regression net, host-only witnesses, worktree battery

## Who runs what

- **Every change's local gate is the TARGETED leg**, for the implementer and for the landing (enqueue) step alike: the
  change's own tests, the tests likely to go red for this diff, the cases the diff reaches, the host-only witnesses
  (below), and the audits whose inputs changed. Order it so the likely reds run first, fail fast, and run it at low
  priority inside a shared cap on concurrent gates. *Why: local runs are free and fast when narrow, and the targeted
  change is what the author can confirm best ("local testing to confirm the targeted changes are correct; CI should
  primarily ensure no regression on the remaining codebase", the owner's rule in the campaign this comes from).*
- **The targeted leg runs on BOTH hosts the project supports**: natively, then, under the same gate slot, the same
  targeted leg in a clone on the other OS (for a Windows host, a WSL clone), fail-fast native first. *Why both hosts: in one measured campaign 3 of 38 landed changes had reds only on the other OS, all in the changes' OWN tests (a locale golden whose text differs by OS, a lock-race fix red 10 of 10 on Linux, a path-length test), and each was caught by the other-OS run before a CI round trip. A targeted leg there costs the clone and build (about 1–2 min) plus the leg, not the 5–10 min of the whole legs.*
  *(Owner decision 2026-10-11; practice, not yet validated as a gate shape.)*
- **CI's merge-group run is the whole-population run, and the only one.** Under a merge queue, CI runs every
  assembly, unfiltered, on every OS, on the merge group, which IS the merged tree the default branch will become. No
  local whole-population gate on either OS. *Why, in one measured campaign
  (2026-10-10): local whole-population gate runs were 41 % of the landing agents' 567 minutes (7–13 min quiet, 25–53
  min under load, 8 of 15 RED, mostly fixed time limits under load), and CI ran the same population on 20 free runners
  in 13 min.* *(Validated 2026-10-11 (measurement); the redesign's effect is not yet measured.)*
- **CI's FULL legs run locally only to reproduce a CI red; they do not gate** (the `cross-platform` skill).

## The landing gate covers the whole population, never a union of filters

Merging several changes behind `A|B|C|D`, one term per change, leaves out every test that no term names. That
leftover set is where the breakage shows up, and adding one more term after each failure never covers it.
*(Validated 2026-09-28.)* The rule stands; what moved is WHERE it runs: the whole-population landing gate is CI's
merge-group run, not a local run. A targeted local leg is a pre-check that the change is right, never a claim about
the rest of the codebase.

## Host-only witnesses are in every targeted leg

Some tests reproduce only on the developer host: typically a filesystem property CI's runners lack (ReFS deletes
differently from NTFS; a delete race reproduced locally in 20 of 7,200 probes may never reproduce on a runner), a
locale, a device. Give each such test class a trait naming the property (xUnit `[Trait("Host", "ReFS")]`, a pytest
marker, a Jest tag), put every test with the trait in the targeted leg at every gate whatever the diff, and DERIVE the
membership from the trait — never a hand-kept list — with a drift test asserting that the known witnesses carry it.
CI still runs them on its own filesystem, where they may pass vacuously.

## Audits are reused when their inputs are unchanged; no test has a fixed time limit

- **A self-test, a drift-rule regeneration or a citation check whose inputs are unchanged since a recorded PASS is
  reused, never re-run**, at every gate. CI's audits job runs them all on every merge group. *Why: in the measured
  campaign one wave's 18 implementer gates spent 246 of 294 gate-minutes on gates that ran no test leg, because a
  self-test pool timed out under its own load; audits took 80–89 % of a gate's wall under fleet load.*
  *(Validated 2026-10-11 (measurement); the reuse rule's effect is not yet measured.)*
- **No test carries a fixed wall-clock time limit.** Rewrite it as a deterministic witness, or, where a process must
  be timed, scale the limit from a baseline measured on the same host; add a guard that fails on a new literal time
  limit in a test. *Why: the top recurring red under load was a 120-second harness limit, and every such red cost a
  re-run plus an attribution.*

## Sizing, serial work, rejections, deliberate changes

- **Size the gate to the blast radius, not to anxiety.** Running the full suite on every commit makes the slow
  gate the bottleneck, and a long run that gets waved off is where a real regression slips through as a "flake".
- **Serial work still gets one whole-population run.** If a batch has to be built one step at a time (a shared
  parser, a shared schema), run the targeted gate after each step; the merge group (or the battery) covers the end.
- **A change that REJECTS input the tool used to accept runs the whole accepted-input corpus in its own targeted
  gate.** A new diagnostic, a tightened validation or a stricter parser is a targeted change with a global blast
  radius: every "this must be accepted" sample, fixture and compatibility matrix is now a candidate red. *Why: an
  implementer gated a tightening on its own tests; the landing gate found 15 compatibility cases (5 samples at 3
  language versions) it had broken.* *(Practice — not yet validated: one use so far.)*
- **The whole-population run will turn up tests that the targeted filters never loaded,** including tests that
  still encode behaviour someone deliberately changed. Fix the test so it asserts the new behaviour. Don't
  exclude it.

## The comprehensive battery runs in its own detached worktree

Legs CI does not run (a slow differential against another implementation, a corpus too large for the runners) run
once per accumulated batch in their own detached worktree, cut at the batch head (`git worktree add --detach <path>
<sha>`, then build and run there), never in a checkout where edits or enqueue steps go on. *Why: a battery that
rebuilds mid-run measures whatever the tree holds at that moment: on the main checkout one measured a half-finished
edit and had to be redone, and nothing could land for its whole run (~45 min of machine time; the landing work that
blocks was modelled at about seven clusters, not measured). From the first worktree battery on, landings continued in
parallel. It still competes for the same cores, so expect other gates to run slower while it does.*
*(Validated 2026-09-28.)*
