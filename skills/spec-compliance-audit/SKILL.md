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

One row per **normative rule**, not per section. Syntax rules, general (semantic) rules, constraints in
definitions, table cells that carry requirements, and MUST/SHALL sentences in prose each count. Give each row:

- a stable id (`<clause>/<rule-kind><n>`, for example `8.4.2/GR3` or `RFC9110-8.6/MUST2`);
- the verbatim rule text, extracted from the standard's own text (Markdown or plain text in the repo);
- the requirement level (MUST / SHOULD / MAY, or the standard's equivalent) and the editions or profiles it
  applies to;
- the definitions it depends on. The meaning of a term usually lives in a different clause.

Generate the catalog mechanically from the standard's text, and re-derive it when the text changes. A
hand-maintained catalog loses rules that are written as plain prose. Where a table or diagram carries the rule,
render the page (see `spec-oracle` §2): extracted figures skew toward falsely restrictive syntax.

For a very large standard, audit a named scope and say which clauses were NOT covered. Never imply that a
partial audit covered the whole standard.

## 2. The traceability inventory: the progress metric

The inventory joins each catalog row to its verdict, its evidence and any work item it points to. It is
**derived**: a generator builds it from the catalog plus the recorded verdicts. **GAP** is the number of rows
without a closed verdict backed by evidence. GAP is the only honest progress number. "Tests passing" and
"features implemented" both count what you looked at, and GAP counts what you have not proven.

Keep one inventory. Do not start side lists, "remaining work" sections or per-campaign trackers. Every open item
belongs in the tracked-work system (§7), linked from its inventory rows.

## 3. One agent per rule, with a self-contained input

Group rows by subject (a clause, or one construct's rule family). Give each agent its own input file containing
the rule rows verbatim with their ids, the definitions they cite, the code entry points already known, the
verdict vocabulary, the return schema, and the bar (see below). The agent should not rediscover any of that. In
measured campaigns, searching and re-reading took nearly half of an agent's tokens, so the input carries what is
already known. Use the `agent-fleet` skill for checkpointing, budgets and restart-safety.

**State the bar, not only the format.** Tell the agent what makes a well-formed answer worthless: a verdict
without the lines read, an absence without the searches run, or an expected value copied from another
implementation's output.

**Bind the return to a schema**, one record per rule: `rule_id`, `verdict`, `citation` (clause plus verbatim
quote, run through the checker), `derived_expectation`, `enforcement` (file:line ranges read), `paths_walked`
(every branch, including the default), `searched` (pattern and its result, including irrelevant hits),
`witness` (see §5), and `open_questions`. A schema-bound agent must name the lines it read. Free prose lets it
skip that.

## 4. The verdict vocabulary

| Verdict | Means | Closes the row? |
|---|---|---|
| `CONFORMS` | the rule holds on every path, shown by a spec-derived witness | yes, with a witness |
| `PARTIAL` | holds on the tested paths and fails on at least one reachable path; name which | no. It becomes work |
| `DIVERGES` | the implementation does something the rule forbids, or fails to do what it requires | no. It becomes work |
| `NOT-IMPLEMENTED` | the construct or behavior is absent. The `searched` record must show where you looked | no. It becomes work |
| `NEEDS-OWNER-DECISION` | the spec leaves latitude, is self-contradictory, or requires a product choice | no. It becomes a decision item |
| `DOCUMENTED-NON-SUPPORT` | the owner decided not to support it, and the conformance document says so, citing the rule | yes, with the doc row |

`PARTIAL` is usually the most serious result in an audit. The rule holds on the paths everyone tests and fails
on the path nobody tested, which is how it survived until the audit found it. Never upgrade a `PARTIAL` to
`CONFORMS` because the common path is right. Never downgrade it to `DIVERGES` either: the fix differs.

Latitude is not divergence. Where the rule is implementation-defined, apply `spec-oracle`'s documented precedence
(the spec where it speaks, then the reference implementation, then the other major vendors), record the choice
in the conformance document, and close the row against that record. A SHOULD the code omits is a documented
deviation, not a defect. Reporting it as a defect costs credibility on the MUSTs.

## 5. Evidence: citations and witnesses

**Every citation is checked mechanically.** Use the citation checker from `spec-oracle`
(`references/citation-checker.md` there). The quote must occur inside that clause's own text, not merely
somewhere in the standard. Run the check on every citation an agent returns before you record the verdict. A
citation inherited from a ticket, a design doc or an earlier audit is re-checked like any other. The common
failure is not an invented quote. It is a real quote attached to the wrong clause number, which then spreads
through comments and tests.

**A verdict needs a spec-derived witness to close.** A witness is an executable check, such as a test, a golden
output or a conformance case, whose expected value was **computed from the cited rule**, not copied from another
implementation, a legacy system or today's output. It must exercise the branch the rule governs. Reading the
code closes nothing. It only produces a hypothesis that the witness confirms. Rows that are defective only because
they lack a witness are cheap, bulk work. Batch them into a "witness round", separate from fixing defects.

**A witness must discriminate the rule.** It fails for an implementation that gets THIS rule wrong - including one
that ignores it. A negative case is illegal ONLY under the rule it witnesses; a generic or "not implemented" error
witnesses nothing specific; a documented-choice case uses inputs on which another plausible choice differs; and no
expected value leans on an undecided default. A rule with no observable consequence ("may", "undefined") closes by a
recorded determination, not by a test that cannot fail. (`pr-test-analyzer` check 4 carries the same list.)

**Never document wrong behaviour as the implementation's choice.** For an implementor-defined element whose current
behaviour violates the standard, the documentation states the INTENDED, conforming choice (resolved by the standard
where it controls, else by the precedence your project sets - e.g. a reference implementation), and the verdict is
`DIVERGES` (the documentation says one thing, the implementation does another) with the defect that owns the fix. The
row closes when the code catches up - never by rewriting the documentation to match the bug.

**`NOT-IMPLEMENTED` and absence verdicts rest on the `searched` record.** List the patterns you tried, including
synonyms for the standard's vocabulary, the dispatch tables, the callers and the base types, with the hit counts.
"Looked, found nothing" is not evidence. "0 hits for X, Y, Z. The dispatch at file:L40 has no arm for it" is.

## 6. The adversarial refuter on every CLOSING verdict

The agent that produced a verdict is biased toward it. Send every verdict that would CLOSE a row
(`CONFORMS`, `DOCUMENTED-NON-SUPPORT`) and every divergence (`PARTIAL`, `DIVERGES`, `NOT-IMPLEMENTED`) to at
least one independent agent that did not produce it. Its instruction is to refute: re-read the rule, look for a
more specific rule that overrides it, walk the paths again, and check that the witness actually exercises the
governed branch. Drop or downgrade whatever it knocks down. If the refuter itself fails, the verdict is
**unverified**, not confirmed. Record it that way.

When the refuter agrees, check that it agrees with the REASONING, not just the label. A right verdict reached for
a wrong reason gets its reasoning corrected in the record.

The refuter also checks the premise. A finding can quote a real rule correctly and still describe input that the
grammar or format makes impossible. If you cannot write the witness's input legally, the finding is refuted.

## 7. Cluster findings by mechanism into tracked work

Do not file one ticket per rule. Group the open rows by **root cause**: the same dispatch, the same table, the
same rule written down in two places. File one work item per mechanism, listing every inventory row it claims.
When the fix lands, the item records which rows it CLOSED (or why it closed none), and GAP moves in the same
change. A finding that exists only in an audit report or a log paragraph is invisible to every work list and
will rot there.

Rank the work by what the defect DOES to a user's program or data: a wrong answer, a crash, or rejecting legal
input. Do not rank by the label a finding happened to get. Fix one mechanism per implementer, and sweep its
siblings (paired functions, other arms of the same dispatch) before calling the cluster done.

## Measured lessons

- **A missing documentation row is not a divergence.** When the conformance document lacks an entry for an
  implementation-defined item, the behavior may be entirely correct. The finding is a documentation row to
  write. It is not a code defect, and filing it as one sends an implementer to "fix" correct code.
- **A missing observation is not a negative one.** A run that produced no output for a rule proves nothing about
  that rule. Before trusting a batch of verdicts, check that every rule in the population was actually observed.
- **Verdicts close only with a witness.** Audits that closed rows on code reading alone reopened them later. The
  code had matched the reader's expectation, not the rule's.
- **A real clause can answer a different question.** A citation that passes the checker can still come from the
  wrong rule, most often in a comment justifying why something was left out. Ask whether the clause's subject is
  your question and whether a more specific rule governs.
- **Differential oracles are blind to shared bugs.** Agreement with a reference implementation is regression
  evidence. It is not a witness unless the expected value was derived from the rule independently.
- **Green tests can hold a GAP open.** A passing test that pins a rejection of legal input reads as a decision.
  Audit such tests against the rule. Only an owner decision makes non-support legitimate.
- **Severity is consequence, not distance from the text.** A requirement met by a different mechanism is not a
  finding. A quietly worded rule can hide the most serious gap. State the consequence concretely, or state what
  would have to be true for it to matter. Never invent one.
- **The reverse direction exists.** Behavior the code has that no rule mentions, such as extensions, stricter
  checks or undocumented constraints, cannot be found by a pass driven by rules. Run a separate pass from the
  implementation's own dispatch tables and record what you find as documented extensions or defects.

## Standards

The bar is the **engineering-standards** skill. For an audit that means: implement the COMPLETE rule when fixing
a finding, never just the case the witness exercises. Fix the root mechanism, not the reported symptom. Treat
deferral, a documented gap or a loud rejection of legal input as debt that only the owner can accept. Keep one
work register and one inventory, both current in the same change as the fix. Every closed row carries its checked
citation at the implementation site.

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
