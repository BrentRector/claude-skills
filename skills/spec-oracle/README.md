# spec-oracle

When a written standard governs a behavior (a language standard, a protocol, a file format, an RFC, ECMA-335 ...),
it is tempting to treat another implementation, a test suite, golden files or "what the code does today" as the
answer. This skill makes Claude treat **the standard as the only oracle**: derive the expected result from the spec
and write down a mechanically checked citation *before* reading the implementation, building a repro or looking at
a failing diff. Everything else is a regression net: useful, but with holes.

## When Claude uses it

Skills load automatically when the task matches their `description`. This one triggers before implementing,
debugging or deciding any behavior governed by a written standard or spec. Typical moments: "is this a bug?",
"what should this output be?", "is this input legal?", or implementing a construct the standard defines.

You can also invoke it explicitly — name it in your request or pick it from the `/` menu — or by asking in words ("check this against the spec first").

## What it does

1. **Find the governing rule.** Keep the standard's text in the repo as Markdown or plain text so it can be searched
   and checked. Find the *specific* rule for the exact construct, not the nearest general sentence. Look in every
   place the answer can live: syntax/grammar, the construct's semantic rules, shared definitions, conformance and
   requirement-level text (MUST/SHALL), errata, and annexes on implementation-defined behavior or edition
   differences.
2. **Render the page when a figure decides it.** If a diagram, syntax railroad, bit-layout figure or table decides
   the question, render the actual PDF page and look at it rather than trusting extracted text or inferring from
   surrounding prose.
3. **Write down the expected result and a checked citation**, before touching code: the clause and rule number with
   a short verbatim quote; the exact value, output, error or state transition the rule requires; and the edition,
   version or profile it applies to. Then check the citation mechanically: the quote must occur inside *that*
   clause's own text. Test expectations are computed from this rule, never copied from another implementation.
4. **Only now read the code.** Ask "does the code match the cited rule?", checking every branch of the relevant
   dispatch, including its default case.

The skill also covers **latitude** (implementation-defined, undefined or unspecified behavior), **defects in the
standard itself**, and ends with a checklist.

### The bundled citation checker

[`references/citation-checker.md`](references/citation-checker.md) explains how to build a citation checker for any
standard you have as Markdown or text, and includes a stdlib-only Python reference implementation (`cite.py`):

```
cite.py SPEC.md --check 7.3.2 "the receiver MUST ignore"
cite.py SPEC.md --find "the receiver MUST ignore"
```

- `--check <clause> "<quote>"` passes only if the quote is in that clause's own region (heading to next heading of
  any level). On failure it reports where the quote actually occurs. An unresolvable id reports "unknown clause",
  a distinct failure from "quote not found".
- `--find "<quote>"` lists every clause whose own text contains the quote.
- `--markdown-headings` treats only `#` lines as headings; `--include-subclauses` lets `--check` search nested
  clauses.

Both sides are normalized the same way (lowercased, punctuation and Markdown emphasis removed, line-break
hyphenation re-joined, whitespace collapsed), so typography does not cause false failures. The checker reads the
source text, not a derived index, because an index can drop or renumber clauses.

## Why it works this way

- **Other oracles are not authority.** A differential test is blind to any violation both sides share, especially
  when your implementation was ported from or tuned against the reference. Conformance suites are mostly happy
  paths. Vendor behavior is a choice the vendor made, often an extension or a known deviation.
- **Order of operations is the whole point.** The usual failure is starting from a failing test, reverse-engineering
  what the code does, and calling that "expected". A repro verifies a spec-derived expectation; it never supplies
  one.
- **Specific rule over general sentence.** A "gap" found in a general sentence usually disappears once you read the
  rule for that argument, field or state.
- **Render figures.** Text extraction loses choice bars, optional brackets, required-keyword underlines, column
  alignment and footnote markers, and the damage is usually one-directional: the syntax looks *more restrictive*
  than it is, so legal input looks illegal.
- **Check every citation mechanically.** The common failure is not inventing a citation but *inheriting* one: the
  quoted text really is in the standard, nobody re-derives the clause number, and it spreads into comments, tests
  and commit messages as if checked.
- **A passing check is not the end.** The skill names three further failure modes, each of which it says has
  shipped real bugs:
  - *A real clause answering a different question*: the quote checks out but the clause does not govern this
    question. It shows up most in comments that justify **not** doing something, where no test ever fails. Ask
    whether the clause's subject is your question and whether a more specific rule overrides it.
  - *A valid rule with an impossible premise*: before building a fix, write the test input and check that it is
    legal. If the fix's own test case cannot be written, the finding is refuted.
  - *A right answer for a wrong reason*: when a second reviewer agrees with a verdict, check that it agrees with the
    reasoning too.
- **Latitude uses a documented precedence, decided by survey.** Where the spec leaves room: the spec wherever it
  still speaks (e.g. "shall be documented"), then the reference or dominant implementation, then other major
  vendors. This settles latitude only and never adopts non-standard extensions. Decide by what implementations
  actually do (docs, error catalogs, test suites, running them), not from memory, and record the choice next to the
  survey so it stays defensible.
- **Record defects in the standard.** Quietly coding around a contradiction or erratum invites a future maintainer
  to "fix" the code back to the wrong behavior.

## Using it in your project

Prerequisites: the standard's text committed to the repo as Markdown or plain text (for a PDF-only standard, the
checker notes suggest extracting it once, e.g. with `pdftotext -layout`, and committing the text); the PDF itself
for rendering pages when a figure decides a question; Python 3 if you use the reference checker.

Unlike most sibling skills, `SKILL.md` has no *Project hooks* section. What it asks each project to settle once
is the latitude precedence and a conformance or implementation-defined-behavior document where latitude choices
and defects in the standard are recorded; the repository's `CLAUDE.md` is the natural place to point at both, and
at the spec file and checker command.

How it composes with sibling skills:

- **engineering-standards** is the bar. For spec-governed work that means implementing the complete feature per the
  spec rather than what a test references, implementing the operation the rule names, treating deferral or
  rejecting legal input as debt, citing the clause at the implementation site, and sweeping sibling rules.
- **spec-compliance-audit** applies the same discipline across a whole standard rather than one question.
- **variant-analysis** is the sibling sweep for the last standards point: when one rule fails, find every other
  place it is written.

See [SKILL.md](SKILL.md) for the full rules.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The skill: the four steps, failure modes, latitude and spec-defect handling, standards, checklist. |
| [`references/citation-checker.md`](references/citation-checker.md) | Requirements, design points and a Python reference implementation of a citation checker. |
| `README.md` | This file. |
