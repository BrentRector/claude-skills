---
name: spec-compliance-audit
description: Use when auditing a whole implementation against a written standard (language standards, ECMA-335, RFCs, file formats, protocol specs) - decompose the standard into a rule catalog, one agent per rule with a self-contained input, a fixed verdict vocabulary, mechanically checked citations, an adversarial refuter on every closing verdict, findings clustered into tracked work, and a traceability inventory whose GAP count is the progress metric.
---

# Spec compliance audit

## Attribution

Adapted from [trailofbits/skills](https://github.com/trailofbits/skills)
`plugins/spec-to-code-compliance/skills/spec-to-code-compliance/` (commit `0cc1c73`, author Omar Inuwa, Trail of
Bits), licensed **CC-BY-SA 4.0**. This skill is distributed under the same license: see [LICENSE](LICENSE). The rest
of this repository is MIT; this directory is not. Changes: rebuilt the audit around a persistent rule catalog and
traceability inventory instead of a one-shot report; replaced the six upstream verdicts with a closing-oriented
vocabulary that includes owner decisions and documented non-support; made citation checking mechanical (deferring
to `spec-oracle`); required a spec-derived witness to close a row; put the adversarial refuter on closing verdicts
as well as divergences; routed findings into clustered, tracked work items; added measured lessons from
multi-month audits; added the discriminating-witness rules and the never-document-wrong-behaviour rule for
implementor-defined elements; dropped the smart-contract domain material and the bundled workflow script.

## What this is

`spec-oracle` answers one question: "what does the standard require HERE?" This skill runs that question at
audit scale: every normative rule of a standard, checked against an implementation, until the count of unchecked
or unproven rules reaches zero. The typical targets are a language standard against a compiler, ECMA-335 against a
metadata reader or writer, an RFC against a protocol stack, or a file-format specification against a
decoder/encoder.

Two artifacts disagree, and the job is to find where. The standard says what must happen. The code decides what
actually happens. Each gap is either a defect or a documented, deliberate position. Deciding which is the finding.

**Do not audit inline.** Honestly judging one rule means reading its enforcement, the enforcement's callees and
its callers. Doing that for hundreds of rules in one context produces a few real checks followed by plausible
ones, and the transcript looks the same either way. A verdict that rests on a promising function name reads
exactly like one that rests on having read the function. One rule per agent, each in its own context, is what
makes the difference visible.

## 1. Decompose the standard into a rule catalog

- One catalog row per normative rule, not per section: stable id, verbatim rule text, requirement level, editions, and the
  definitions it depends on.
- Generate the catalog mechanically from the standard's text; re-derive it when the text changes.
- For a very large standard, audit a named scope and say which clauses were NOT covered.

Read `references/rule-catalog.md` before building or re-deriving the catalog.

## 2. The traceability inventory: the progress metric

The inventory joins each catalog row to its verdict, its evidence and any work item it points to. It is
**derived**: a generator builds it from the catalog plus the recorded verdicts. **GAP** is the number of rows
without a closed verdict backed by evidence. GAP is the only honest progress number. "Tests passing" and
"features implemented" both count what you looked at, and GAP counts what you have not proven. *(Validated 2026-09-28.)*

Keep one inventory. Do not start side lists, "remaining work" sections or per-campaign trackers. Every open item
belongs in the tracked-work system (§7), linked from its inventory rows. *(Validated 2026-09-28.)*


## 3. One agent per rule, with a self-contained input

- Do not audit inline: one rule group per agent, each with its own input file (rule rows verbatim, cited definitions, known
  code entry points, verdict vocabulary, return schema, the bar).
- State the bar, not only the format: say what makes a well-formed answer worthless.
- Bind the return to a one-record-per-rule schema that names the lines read, the paths walked and the searches run.
- Use the `agent-fleet` skill for checkpointing, budgets and restart-safety.

Read `references/agent-inputs.md` before writing the agent inputs or the return schema.

## 4. The verdict vocabulary

| Verdict | Means | Closes the row? |
|---|---|---|
| `CONFORMS` | the rule holds on every path, shown by a spec-derived witness | yes, with a witness |
| `PARTIAL` | holds on the tested paths and fails on at least one reachable path; name which | no. It becomes work |
| `DIVERGES` | the implementation does something the rule forbids, or fails to do what it requires | no. It becomes work |
| `NOT-IMPLEMENTED` | the construct or behavior is absent. The `searched` record must show where you looked | no. It becomes work |
| `NEEDS-OWNER-DECISION` | the spec leaves latitude, is self-contradictory, or requires a product choice | no. It becomes a decision item |
| `DOCUMENTED-NON-SUPPORT` | the owner decided not to support it, and the conformance document says so, citing the rule | yes, with the doc row |


- Never upgrade a `PARTIAL` to `CONFORMS`, and never downgrade it to `DIVERGES`.
- Latitude is not divergence: apply `spec-oracle`'s documented precedence, record the choice in the conformance document,
  and close the row against that record. A SHOULD the code omits is a documented deviation, not a defect.

## 5. Evidence: citations and witnesses

- Run every citation through the `spec-oracle` citation checker before recording a verdict, including inherited ones.
- A verdict closes only with a spec-derived witness that exercises the governed branch and discriminates THIS rule; reading
  the code closes nothing.
- Never document wrong behaviour as the implementation's choice: document the intended choice and record `DIVERGES`.
- `NOT-IMPLEMENTED` and other absence verdicts rest on the `searched` record (patterns tried, hit counts).

Read `references/verdicts-and-evidence.md` before recording any verdict, writing a witness, or settling an implementor-defined element.

## 6. The adversarial refuter on every CLOSING verdict

- Send every closing verdict (`CONFORMS`, `DOCUMENTED-NON-SUPPORT`) and every divergence to an independent refuter agent;
  drop or downgrade what it knocks down.
- A refuter that fails leaves the verdict **unverified**, not confirmed.
- Check that the refuter agrees with the reasoning, not just the label, and that it checks the premise.

Read `references/refuter.md` before dispatching or judging a refuter.

## 7. Cluster findings by mechanism into tracked work

- Group open rows by root cause; one work item per mechanism, listing every inventory row it claims, recording the rows it
  CLOSED when it lands.
- Rank by what the defect does to a user's program or data, not by label.
- Sweep a cluster's siblings before calling it done.

Read `references/clustering.md` before filing work items or assigning implementers.

## Measured lessons and standards

- A missing documentation row is not a divergence; a missing observation is not a negative one; verdicts close only with a
  witness; run a separate reverse-direction pass from the implementation's dispatch tables.
- The bar is the `engineering-standards` skill: implement the COMPLETE rule, fix the root mechanism, keep one register and one
  inventory current in the same change.

Read `references/lessons-and-standards.md` before trusting a batch of verdicts or closing out an audit.

## Checklist

- [ ] Catalog generated from the standard's text: one row per normative rule, levels and editions recorded
- [ ] Audit scope named; uncovered clauses listed
- [ ] Each agent got a self-contained input with the bar and a return schema
- [ ] Every citation run through the `spec-oracle` checker before recording
- [ ] Every closing verdict has a spec-derived witness that exercises the governed branch
- [ ] Every closing verdict and every divergence survived an independent refuter; failed refutations marked unverified
- [ ] Latitude settled by documented precedence and recorded, not filed as a divergence
- [ ] Findings clustered by mechanism into tracked work items that link their inventory rows
- [ ] GAP regenerated from the inventory and reported. It is the only progress number
