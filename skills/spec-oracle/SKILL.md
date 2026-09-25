---
name: spec-oracle
description: Use BEFORE implementing, debugging or deciding any behavior governed by a written standard or spec (language standards, protocols, file formats, RFCs, ECMA-335, ...) — derive the expected behavior from the spec and produce a checked citation before reading or writing code.
---

# Spec oracle

When a written standard governs a behavior, **the standard is the only oracle.** Other implementations, test
suites, golden files, a legacy system and "what the code does today" are regression nets. They are useful and
they have holes, and none of them is authority.

**Order of operations is the whole point.** Derive the expected result from the spec and write down a checked
citation BEFORE you read the implementation, build a repro or look at a failing diff. A repro VERIFIES a
spec-derived expectation. It never supplies one.

The usual way this goes wrong is starting from a failing test and reverse-engineering what the code does,
then calling that "expected". If you catch yourself doing that, stop and restart at step 1.

## Why other oracles are not authority

- **A differential test is blind to any violation both sides share.** If your implementation was ported from,
  or tuned against, the reference, the bug and the oracle came from the same place.
- **Conformance suites are mostly happy paths.** A green suite says nothing about the rules it never runs.
- **Vendor behavior is a choice the vendor made,** often an extension or a known deviation.

Every difference from the expected output counts as a bug until a citation says otherwise. "Close enough" and
"implementation variation" are not answers. If something is a common extension and not standard behavior,
call it that. Never claim conformance without a citation.

## 1. Find the governing rule

Locate the standard's text. Keep it in the repo as Markdown or plain text if you can, so it can be searched and
checked mechanically (see step 3). Then find the **specific** rule for the exact construct, not the nearest
general sentence. A "gap" found in a general sentence usually disappears once you read the rule for that
argument, field or state.

Look in all the places the answer can live: the syntax or grammar, the semantic rules for that construct, the
shared definitions and concepts sections, conformance and requirement-level text (MUST/SHALL, see RFC 2119),
errata, and any annex listing implementation-defined behavior or differences between editions.

## 2. When a diagram, table or figure decides the question

Rule prose usually survives text extraction. **Diagrams, syntax railroads, bit-layout figures and tables often
do not.** Choice bars, optional brackets, underlines that mark required keywords, column alignment and footnote
markers all get lost. The damage is usually one-directional: text extraction makes the syntax look **more
restrictive** than it is, so legal input looks illegal.

- If the figure decides the answer, **render the actual page** (PDF to image) and look at it. Don't work out a
  diagram's meaning from the prose around it, and don't trust extracted text of a figure over the rendered page.
- Tell apart what the notation says is required and what it says is optional. In many standards, underlining
  or bold decides which keywords are required, and brackets only group.
- Rule TEXT that looks garbled may be exactly what was printed. Check the rendered page before "fixing" it.

## 3. Write down the expected result and a CHECKED citation

Before touching code, write down three things:

1. **The citation:** section or clause number, plus rule or paragraph number, plus a short verbatim quote.
2. **The derived expectation:** the exact value, output, error or state transition the rule requires.
3. **Applicability:** the edition, version or profile it holds for, if the standard has more than one.

Then **check the citation mechanically.** Confirm that the quoted text occurs inside that clause's own section,
not merely somewhere in the document. See `references/citation-checker.md` for a small tool that does this and
also reports which section really holds a quote. **A citation you haven't checked isn't a citation.**

Test expected values are **computed from this rule**. Never copy them from another implementation's output.

## 4. Only now read the code

Ask "does the code match the cited rule?", not "what does the code do?". Check every branch of the relevant
dispatch, including its default case, against the rule. A behavior-neutral refactor proves there was no
regression. It never proves correctness.

## Failure modes: each one has shipped real bugs

**Inheriting an unchecked citation.** The usual failure is not making up a citation. It is inheriting one. A
ticket, design doc or code comment carries "§7.3.2 rule 4", the quoted text really is in the standard, and
nobody re-derives the clause NUMBER. It then spreads into comments, tests and commit messages as if someone had
checked it. Re-check every citation you pass on, including ones you wrote yourself last week.

**A real clause answering a different question.** A mechanical check proves the quote is in that clause. It
cannot prove the clause **governs your question**. This shows up most in comments that justify NOT doing
something ("per RFC NNNN §x.y this is implementation-defined, so we skip it"). The citation checks out, the
prose sounds sure of itself, and because it argues against writing code, no test fails. Before accepting it,
ask:

- **Is this clause's subject my question?** A rule about which representations are *available* is not the rule
  that *selects* one. A rule about non-local elements does not govern local ones.
- **Is there a MORE SPECIFIC rule** for this exact construct that overrides the general one?
- Freedom over the *form* of something is never freedom over whether it *exists*. Be suspicious when a design
  doc says "permanently" or "never needed".

**A valid rule with an impossible premise.** A finding can quote a real rule correctly and still ask for
something that can't happen. Before building the fix, write the test input and ask whether it is even legal
under the grammar or format. If the fix's own test case can't be written, the finding is refuted, not hard.
Refuting it is a real result: record the evidence and remove the unreachable code. When a finding explains an
*asymmetry* between two paths, first check whether that asymmetry is simply what a syntax difference implies.

**A right answer for a wrong reason.** When a second review agrees with a verdict, check that it agrees with the
*reasoning* too. Record the corrected reasoning along with the corrected verdict.

## Where the spec leaves latitude

Some behavior really is implementation-defined, undefined or unspecified. Here the spec can't settle the
question, and neither can taste. Use a **documented precedence** and write it down once for the project:

1. **The spec, wherever it actually speaks.** That includes constraints on the latitude, such as "shall be
   documented" or "shall be one of ...".
2. **The reference or dominant implementation** of the standard (for example the reference implementation named
   by the standards body, or the de facto one for the ecosystem).
3. **The other major vendors' implementations.**

This settles latitude only. It never adopts another implementation's non-standard extensions as if they were
required behavior.

**Survey, don't recall.** Decide by what the implementations actually DO. Use their docs, their error
catalogs, their test suites, or run them. Don't reason from first principles or from memory. A table built from
memory is a guess, and you should label it as one. Surveys often overturn the "obvious" choice: what looked like
an open question can turn out to have one answer every implementation agrees on. When the survey is unanimous,
say so and recommend that answer rather than presenting a balanced menu. Respect licenses: observe behavior and
read documentation, don't copy source.

**Record the choice** in a conformance or implementation-defined-behavior document, next to the survey that
justifies it. A survey is expensive to redo, and the record is what makes the choice defensible later.

## When the standard itself is wrong

It happens: contradictory rules, a typo in a table, an erratum. Record the defect and your decision in the
conformance document. Don't quietly code around it, or a future maintainer will "fix" the code back to the
wrong behavior.

## Standards

The bar is the **engineering-standards** skill. For spec-governed work it means:

- **Implement the complete feature per the spec**: enumerate every syntax and general rule the construct owes
  and build all of them. Never scope the work to what a test, a corpus or an oracle happens to reference.
- **Implement the operation the rule names**, not a convenient library equivalent that differs at the edges.
- **Deferral, a documented gap, or a loud rejection of legal input is debt**, and only the owner chooses it.
- **Cite the clause at the implementation site**, and keep the conformance record current in the same change.
- **When one rule fails, check whether it is written down in more than one place**, and sweep the sibling
  rules and paired functions before calling a family done.

## Checklist

- [ ] Found the specific governing rule, not a general sentence
- [ ] Rendered the page if a diagram, table or figure decides it
- [ ] Wrote down citation, expectation and applicability BEFORE reading code
- [ ] Citation mechanically checked (quote occurs in THAT clause)
- [ ] Asked: is this the clause for MY question, and is there a more specific one?
- [ ] Confirmed the premise is expressible (the test input is legal)
- [ ] Latitude? Survey measured, precedence applied, choice recorded
- [ ] Test expectations computed from the rule, not copied from an oracle
