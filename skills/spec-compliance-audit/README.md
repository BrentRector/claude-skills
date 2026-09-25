# spec-compliance-audit

Auditing a whole implementation against a whole written standard: a language standard against a compiler,
ECMA-335 against a metadata reader or writer, an RFC against a protocol stack, a file-format specification
against a decoder or encoder. The standard says what must happen and the code decides what actually happens. The
job is to find every place they disagree and decide, for each one, whether it is a defect or a documented,
deliberate position. The audit is done when the count of unchecked or unproven rules reaches zero.

Where [`spec-oracle`](../spec-oracle/SKILL.md) answers one question ("what does the standard require HERE?"),
this skill runs that question at audit scale, across every normative rule.

## When Claude uses it

Claude loads a skill automatically when the request matches its `description`. This one matches requests to
audit an implementation against a written standard: language standards, ECMA-335, RFCs, file formats and
protocol specs. You can also ask for it directly, for example "run a spec compliance audit of clause 8 against
the parser", or name the skill (`spec-compliance-audit`) in your request.

It is not for a single "is this a bug?" question. That is `spec-oracle`'s job.

## What it does

| Step | What happens |
|---|---|
| 1. Rule catalog | The standard is decomposed into one row per **normative rule** (not per section): syntax rules, semantic rules, constraints inside definitions, table cells that carry requirements, MUST/SHALL sentences in prose. Each row gets a stable id (e.g. `8.4.2/GR3`, `RFC9110-8.6/MUST2`), the verbatim rule text, its requirement level and editions or profiles, and the definitions it depends on. The catalog is generated mechanically from the standard's text and re-derived when the text changes. |
| 2. Traceability inventory | A derived table joining each catalog row to its verdict, evidence and work item. **GAP** (rows without a closed, evidenced verdict) is the only progress number. |
| 3. One agent per rule group | Rows are grouped by subject (a clause, or one construct's rule family). Each agent gets its own self-contained input: the rules verbatim with ids, the definitions they cite, known code entry points, the verdict vocabulary, a return schema, and the bar. |
| 4. Verdicts | Each rule gets one verdict from a fixed vocabulary (below). |
| 5. Evidence | Every citation is checked mechanically; every closing verdict needs a spec-derived witness; every absence verdict rests on a `searched` record. |
| 6. Refuter | An independent agent tries to refute every closing verdict and every divergence. |
| 7. Tracked work | Open rows are clustered by root-cause mechanism into work items that list the rows they claim; a landed fix records which rows it closed, and GAP moves in the same change. |

For a very large standard, the audit covers a named scope and says which clauses it did NOT cover.

### The return schema

One record per rule: `rule_id`, `verdict`, `citation` (clause plus verbatim quote, run through the checker),
`derived_expectation`, `enforcement` (file:line ranges read), `paths_walked` (every branch, including the
default), `searched` (patterns and results, including irrelevant hits), `witness`, and `open_questions`.

### The verdict vocabulary

| Verdict | Means | Closes the row? |
|---|---|---|
| `CONFORMS` | holds on every path, shown by a spec-derived witness | yes, with a witness |
| `PARTIAL` | holds on tested paths, fails on at least one reachable path | no, becomes work |
| `DIVERGES` | does what the rule forbids, or fails to do what it requires | no, becomes work |
| `NOT-IMPLEMENTED` | absent; the `searched` record shows where you looked | no, becomes work |
| `NEEDS-OWNER-DECISION` | latitude, a self-contradiction, or a product choice | no, becomes a decision item |
| `DOCUMENTED-NON-SUPPORT` | the owner decided not to support it and the conformance document says so | yes, with the doc row |

## Why it works this way

- **Do not audit inline.** Judging one rule honestly means reading its enforcement, its callees and its callers.
  Doing that for hundreds of rules in one context produces a few real checks followed by plausible ones, and the
  transcript looks the same either way. One rule group per agent, each in its own context, makes the difference
  visible.
- **One row per rule, generated from the text.** A hand-maintained catalog loses rules that are written as plain
  prose. Where a table or diagram carries the rule, the page is rendered, because extracted figures skew toward
  falsely restrictive syntax.
- **GAP is the only honest progress number.** "Tests passing" and "features implemented" count what you looked
  at; GAP counts what you have not proven. There is one inventory: no side lists, "remaining work" sections or
  per-campaign trackers.
- **Self-contained agent inputs.** In the skill's measured campaigns, searching and re-reading took nearly half of
  an agent's tokens, so the input carries what is already known.
- **State the bar, and bind a schema.** The agent is told what makes a well-formed answer worthless (a verdict
  without the lines read, an absence without the searches run, an expected value copied from another
  implementation). A schema forces it to name the lines it read; free prose lets it skip that.
- **`PARTIAL` is its own verdict.** It is usually the most serious result: the rule holds on the paths everyone
  tests and fails on the one nobody tested. It is never rounded up to `CONFORMS` or down to `DIVERGES`, because
  the fix differs.
- **Latitude is not divergence.** Implementation-defined behaviour is settled by `spec-oracle`'s documented
  precedence and recorded in the conformance document. An omitted SHOULD is a documented deviation; reporting it
  as a defect costs credibility on the MUSTs.
- **Citations are checked mechanically.** The common failure is not an invented quote but a real quote attached
  to the wrong clause number, which then spreads through comments and tests. Inherited citations are re-checked
  like any other.
- **A witness closes a row, and it must discriminate.** Code reading only produces a hypothesis. The witness's
  expected value is computed from the rule, not copied from another implementation or today's output, and it
  must fail for an implementation that gets this rule wrong. Audits that closed rows on reading alone reopened
  them later.
- **Never document wrong behaviour as the implementation's choice.** If an implementor-defined element violates
  the standard, the documentation states the intended conforming choice, the verdict is `DIVERGES`, and the row
  closes when the code catches up.
- **An adversarial refuter.** The agent that produced a verdict is biased toward it. The refuter re-reads the
  rule, looks for a more specific overriding rule, re-walks the paths, checks that the witness exercises the
  governed branch, and checks the premise (a finding describing input the grammar makes impossible is refuted).
  A failed refuter leaves the verdict **unverified**, not confirmed.
- **Cluster by mechanism.** One ticket per rule scatters a single root cause. A finding that lives only in a
  report or log paragraph is invisible to every work list. Work is ranked by what the defect does to a user's
  program or data (wrong answer, crash, rejecting legal input), not by its label.

The skill also lists measured lessons: a missing documentation row is not a divergence; a missing observation is
not a negative one; differential oracles are blind to shared bugs; green tests can hold a GAP open; severity is
consequence, not distance from the text; and a rule-driven pass cannot find behaviour no rule mentions, so a
separate reverse pass starts from the implementation's own dispatch tables.

## Using it in your project

Prerequisites: the standard as text in the repository (Markdown or plain text) so rules can be extracted
verbatim, and, where diagrams carry rules, a way to render the page.

Your repository supplies the concrete pieces the skill names generically: the catalog generator, the verdict
recording and inventory generator, the conformance document where latitude choices and non-support are recorded,
and the tracked-work system that findings flow into. A project's `CLAUDE.md` can tighten the rules, for example
by setting the precedence for implementation-defined choices (the skill gives "a reference implementation" as an
example).

It composes with sibling skills:

- [`spec-oracle`](../spec-oracle/SKILL.md): the per-rule question, the documented latitude precedence, page
  rendering, and the citation checker (`references/citation-checker.md` there).
- [`agent-fleet`](../agent-fleet/SKILL.md): checkpointing, budgets and restart-safety for the per-rule agents.
- [`engineering-standards`](../engineering-standards/SKILL.md): the bar for fixing findings (implement the
  complete rule, fix the root mechanism, sweep siblings).
- The `pr-test-analyzer` agent's check 4 carries the same witness-discrimination list.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The full procedure, verdict vocabulary, evidence rules, measured lessons and checklist |
| [`LICENSE`](LICENSE) | Creative Commons Attribution-ShareAlike 4.0 International |
| `README.md` | This overview |

## Credits / license

Adapted from [trailofbits/skills](https://github.com/trailofbits/skills)
`plugins/spec-to-code-compliance/skills/spec-to-code-compliance/` (commit `0cc1c73`, author Omar Inuwa, Trail of
Bits), licensed **CC-BY-SA 4.0**. This directory is distributed under the same license; see [LICENSE](LICENSE).
The rest of the repository is MIT; this directory is not.

Changes from the upstream skill, as recorded in `SKILL.md`: the audit was rebuilt around a persistent rule catalog
and traceability inventory instead of a one-shot report; the six upstream verdicts were replaced with a
closing-oriented vocabulary that includes owner decisions and documented non-support; citation checking was made
mechanical (deferring to `spec-oracle`); a spec-derived witness is required to close a row; the adversarial
refuter covers closing verdicts as well as divergences; findings are routed into clustered, tracked work items;
measured lessons from multi-month audits were added, along with the discriminating-witness rules and the
never-document-wrong-behaviour rule; the smart-contract domain material and the bundled workflow script were
dropped.
