## Verdict and evidence detail

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
