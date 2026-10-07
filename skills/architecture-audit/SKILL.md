---
name: architecture-audit
description: Use when a whole codebase (not one diff) needs a comprehensive architectural review AND restructuring - god classes to split, duplicate code and duplicate rules to unify, file-system layout, namespaces, file and class names to fix, dependency direction to enforce, and the language and runtime to modernize - without changing behavior. Runs as a campaign - a measured baseline and a behavior-neutrality oracle first, an adversarially reviewed target architecture, a review fleet by subsystem and dimension whose findings become tracked work, then behavior-neutral restructuring waves and analyzer-driven modernization, each proven by output differentials and pinned by architecture tests. Not for reviewing one change (use review) or for fixing defects (findings go to the normal fix lane).
---

# Architecture audit: review and restructure a whole codebase

**Restructure the whole thing without changing what it does, and leave tests behind that keep it that way.** A
whole-codebase review is not a big code review. It is a campaign with three failure modes:
- findings that evaporate as prose;
- refactors that quietly change behavior;
- a structure that decays again the week after.

This skill is built against each one: findings become tracked work, every refactor proves itself neutral against an
oracle recorded before the first change, and every new boundary gets a test that fails when it is crossed.

*(Practice — not yet validated: this skill is the plan for a campaign that has not yet run; each rule is drawn from
review, refactoring and fleet practices elsewhere in these skills.)*

## When to use

- The owner asks for a comprehensive review of "everything", or the design has settled after a period of rapid
  change.
- God classes, parallel mechanisms and layout drift have accumulated past what per-change review keeps up with.
- A language or runtime generation upgrade is due across the codebase.

**Not for:** reviewing one diff or PR (`review`), fixing defects (a defect found here goes to the fix lane as a work
item), or a redesign that changes behavior (that is a feature, with its own spec).

## Preconditions, before any agent is dispatched

- **The design has settled.** No subsystem redesign is in flight; a restructure over moving ground is rework.
- **Code about to be deleted is deleted first.** Never refactor what a planned cut-over removes.
- **A quiet lane.** Restructuring touches every file. Pause or partition other work, or merge conflicts eat the
  campaign.
- **The owner has decided** timing, the runtime/language target (stable only, or a preview allowed), and whether
  public names (packages, assemblies) may change.

**When completion work still remains** (a conformance burn-down, a feature backlog), the start can be SPLIT rather
than waited for: run Phase 0 and Phase 1 now, so the remaining work is written into the target layout instead of
into the classes about to be split; run leaf waves (the layers nothing depends on) and Delete waves in subsystems
the active lane does not touch; keep the hot subsystems' waves for after that work lands. The merge-conflict
mitigation is the partition, enforced by which files a wave may touch, not by hope. The owner decides the split.

## Phase 0: Measure the baseline and record the oracle

Opinions come after measurements.
- **A census** over a semantic model (Roslyn for C#, never grep):
  - per type, including every partial file: lines, members, fan-in, fan-out, and namespace-to-folder agreement;
  - the dependency graph between projects and namespaces;
  - clone families (`roslyn-analysis`, type-2 detection);
  - unreachable code, measured with a probe (`engineering-standards`: reachability is measured, not deduced);
  - dead artifacts beyond code: scripts, configuration, docs, test scaffolds and drift-test literals with no caller
    or reader, measured by a caller query per artifact. A subsystem kept alive "as an oracle" after its goldens
    were baked is the largest item this census usually finds.
- **God-class candidates.** Types past a size threshold, or with more than one reason to change. Name each one's
  responsibilities before deciding anything.
- **The behavior-neutrality oracle** (the contract below), captured at the baseline commit.
- **A performance baseline** (`performance-diagnosis`), so a refactor cannot regress speed unseen.

## The behavior-neutrality contract (every restructuring wave proves all that apply)

Compare case by case, never by totals (`test-gate`).
1. **Generated or emitted artifacts are byte-identical** to the baseline, or each difference is listed and
   explained. That means compiler output, serialized formats and generated code.
2. **Diagnostics and error messages** are the same: codes, severities, positions and text.
3. **Parser changes:** the token-stream and parse-tree shape are the same over the whole input population.
4. **The full test suite** is green, on every OS CI runs (`cross-platform`).
5. **Performance** is not worse than the baseline beyond noise, with conditions recorded.

*Why: a refactor can change behavior through registration order, static initialization or a shared cache while
every test stays green. Output differentials see what tests don't.*

## Phase 1: The target architecture, designed and broken before it is built

An architect agent writes the target; an adversarial reviewer tries to break it; a reviser answers every blocking
finding; the owner approves. (`agent-fleet/references/refuters-and-routing.md` for refuters; the design gets the same treatment as a verdict.)
The target states:
- **Layers and the allowed dependency edges.** Every other edge fails an **architecture test** (a Roslyn or
  metadata-based test, or NetArchTest/ArchUnit-style), so the direction is enforced, not hoped for.
- **Layout rules.** The folder equals the namespace; one public type per file; the file name equals the type; a
  partial type splits only along a named concern.
- **Per god class:** the responsibilities, the types they become, the seam each exposes, and the extraction order.
  Code that is really a table becomes data plus a loader or generator.
- **The language and runtime target** (`dotnet-engineering`, "Modernizing an existing codebase", for .NET).

## Phase 2: The review fleet: findings, not fixes

- **One review agent per (subsystem × dimension)**, run in small parallel chunks, each finding adversarially
  verified (`review`'s procedure, applied to a subsystem instead of a diff).
- **The dimensions:**
  - architecture;
  - full code;
  - performance;
  - duplication and efficiency;
  - modern-language conformance.
- **Every finding carries** its site, the rule it breaks, a concrete scenario, the proposed target and its wave
  kind.
- **Findings become tracked work items, never prose.** File them grouped by the file they touch, so restructuring
  waves are computed from the findings (`agent-fleet/references/grouping-fixes.md`), not picked by hand.
- **A defect found here is not fixed here.** It becomes a normal work item for the fix lane. Mixing fixes into
  refactors destroys the neutrality proof.

## Phase 3: Restructuring waves (behavior-neutral, one mechanism each)

**Five wave kinds.** Each wave is one of them, and each proves the contract:
- **Extract:** one responsibility out of a god class, behind a named seam.
- **Unify:** one clone family, or one duplicated RULE, into one place (`engineering-standards`: one rule, one place).
- **Move and rename:** layout, namespaces, file and type names, with EVERY caller changed in the same change. There
  is no alias, forwarder, `[Obsolete]` twin or shim: a compatibility layer for callers that no longer exist is a
  second mechanism to maintain.
- **Data-ize:** code that is a table becomes data plus one loader or generator.
- **Delete:** a census-measured dead member, type, file, script, doc or scaffold, removed with every caller and
  with the drift test that pinned it. The wave records HOW the item was measured dead. A deletion that changes
  behavior is not a deletion; it is a defect for the fix lane.

**Order.** Leaves first (the layers nothing depends on), then inward. Renames land before extractions in the same
area, so extraction diffs stay readable.

**Every wave:**
- adds or extends the architecture test or drift test that keeps its new boundary true, seen failing once on a
  planted violation;
- updates the design docs it changes.

**Mechanical changes use tools, not hands.** `roslyn-analysis`'s rewriter harness for C# renames and moves, IDE code
fixes via `dotnet format`, and grammar edits followed by the token and parse-tree differential.

## Phase 4: Modernization (analyzer-driven, one rule per wave)

1. Upgrade the SDK, target framework and language version first, with the whole contract.
2. Then one analyzer rule or feature per wave, applied across the whole tree with its code fix or a rewriter.
3. Keep a wave only if the contract and the performance baseline hold. A modern idiom that slows a hot path is
   reverted and recorded.

For .NET, `dotnet-engineering` lists the features and how to apply them at scale.

## Who does what: model tiers

Price a wave per completed wave, not per token, and spend the expensive model only where its error would compound.
- **The frontier model** (the most capable, most expensive tier) writes the Phase 1 target architecture, the one
  artifact every later wave executes against, and runs a second adversarial round only when the mid-tier refuter
  cannot break the design. Each such dispatch gets the owner's explicit approval; it is never a role's default.
- **The mid tier** reviews (Phase 2), refutes, lands trains, and runs the extract and unify waves, where a
  responsibility boundary is a judgment.
- **The small tier** runs the census, the move-and-rename and analyzer waves driven by a rewriter or a code fix,
  and the Delete waves whose items the census already measured dead. The oracle proves a mechanical wave; the
  model does not. A small-tier agent that meets a judgment call returns it to the mid tier instead of guessing.

## Phase 5: Close

- Run the full battery on every OS.
- Re-measure performance against the baseline.
- Update the docs.
- Leave the architecture tests in the suite: they are the reason the structure stays true next year.

## Anti-patterns

- Reviewing a codebase in one giant prompt, or as one agent, instead of by subsystem and dimension.
- Findings kept in a report instead of a tracker, where the next wave can't be computed from them.
- A refactor proven only by "tests pass".
- Fixing a defect inside a refactor wave.
- A rename that leaves an alias "for compatibility" with callers that no longer exist.
- A layering rule written in a document but not in a test.
- Refactoring code that a planned cut-over deletes.
- Keeping a retired subsystem alive "as an oracle" after its goldens are baked: it costs every gate and every
  grammar change, and finds nothing the goldens do not.
- Spending the frontier model on a mechanical wave the oracle already proves.
