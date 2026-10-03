---
name: engineering-standards
description: Use whenever writing, changing, designing or reviewing production code - it states the non-negotiable quality bar (commercial-grade, decades-maintainable), the structural rules (no god classes, one mechanism per job, one rule in one place), the root-cause and every-bug-is-a-pattern discipline, and when re-architecture is required rather than optional.
---

# Engineering standards

The bar every change is held to. These rules were each earned by a real correction on long-lived production
work: a compiler, a binary rewriter, format decoders, libraries meant to outlive their authors. They are
deliberately short. Each is a rule and the reason it exists; where a rule is easy to misread, an example shows
what it rules out.

A change that breaks one of these is not "done with caveats". It is debt, and it is reported as debt.


Each section below lists the rules as one-line imperatives. The reasons, examples and validation labels live in
`references/`; a rule you have not read the reason for still binds.

## 1. The quality bar

- Build production quality, commercial-grade, maintainable for a decade; build what you would ship if you owned it for five years.
- No hacks, shims, fallbacks, dead code or left-behind TODOs.
- Use the latest stable language and runtime; carry no backward-compatibility baggage unless a real user needs it.
- Break ties by usability, understanding, support, maintenance.

## 2. Design and structure

- No god classes; one mechanism per job; one rule in one place (search for the RULE, not the construct).
- Change the dispatch, not the callers; model the rule's full shape before fixing a table or schema.
- Keep phases one-directional; resolve to typed objects at load time and encode only at the boundary; build output from the model, never patch input in place.
- Use the standard tool for a solved problem; construct registries explicitly where trimming or AOT is in play; check what already exists before proposing a design.
- A stated scope is an estimate, never a ceiling: re-architect when the work needs it, prefer the shape that makes the NEXT case automatic (with a drift test), re-architect at the third patch to one component, and answer the structural question first.

Read `references/quality-and-structure.md` before designing or restructuring anything, and whenever a rule here is unclear (it carries the reasons, examples and the full re-architecture rules).

## 3. Correctness and root cause

- Fix the root cause; never paper over a symptom, never change valid input to dodge a tool bug, never relabel a bug a "quirk".
- On a correction, fix the interpretation, not the output.
- Every bug is a pattern: sweep for siblings in the same change and show the query you ran; ask which arm of a two-arm dispatch you fixed.
- Implement the named operation, not a convenient equivalent.
- Diagnose from evidence; a remembered pattern is a hypothesis; re-measure a work item's premise on today's code.
- Apply a coordinated set of fixes as one change; keep output reproducible.

## 4. Completeness

- Implement the COMPLETE feature to its spec or design; tests verify, they do not scope.
- Deferral is debt and only the owner may choose it; never ship a half-feature; handle every legal input shape; take the hardening path.

Read `references/correctness-and-completeness.md` before fixing a bug, scoping a feature or proposing a deferral.

## 5. Verification and invariants

- Propose invariants, validators and drift tests unprompted; prefer structural guarantees to conventions; pin every collapse with a drift test.
- Surface the governing drift rules before the edit from one home (`references/rule_index.py`); never copy the rules into docs or skills.
- Make every new check fail once, for the right reason; ask what a check's scope excludes.
- Verify values, not "it ran"; compute expected results from the authority; give every measurement a witness; measure reachability; vary the axis your subject holds fixed; compare against an independent implementation.

Read `references/verification-and-invariants.md` before writing or trusting a test, a guard, a probe or a measurement.

## 6. Docs and honesty

- Keep docs current in the same change set; implement from the design doc; sweep docs on discovery.
- Comments carry the WHY; cite the authority in the code; write forensic commit messages.
- Report honestly, calibrated to the evidence; say at once when you were wrong.

Read `references/docs-and-honesty.md` before writing docs, comments, a commit message or a closing report.

## Using this skill

- **Before writing code:** read the governing spec or design, answer the structural question (section 2), and
  decide the complete scope (section 4).
- **While fixing a bug:** root cause, then sibling sweep, then the other arm, then the drift test (sections 3
  and 5).
- **Before calling it done:** the change is complete, swept, one-mechanism, verified by a check that has been
  seen to fail, and its docs are current. If any of these is not true, report it as debt, not as done.
- **In review:** every rule above is a finding category. A god class, a duplicated mechanism, a workaround or an
  unswept sibling is a defect even when the tests pass.

## Project hooks

This skill is the generic floor. A repository tightens it or adds to it in its `CLAUDE.md` (or `AGENTS.md`,
`CONTRIBUTING.md`) under a section such as **"Engineering standards"**:

```markdown
## Engineering standards
- Authority: <standard or spec, and the precedence when it leaves latitude>
- Architectural commitments: <settled decisions not to relitigate>
- Language/runtime: <versions, warnings-as-errors, analyzers>
- Docs that must stay current: <design docs, README, changelog, fix log>
- Work register: <the one place new defects and deferrals are filed>
```

**Project rules win on conflict.** Where a project sets a stricter rule, follow it. Where it deliberately relaxes
one (for example, a prototype that is explicitly throwaway), follow it and say so once. Settled architectural
commitments in the project instructions are designed within, not reopened.
