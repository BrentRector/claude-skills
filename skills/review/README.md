# review

A code review that filters instead of generating volume. Four independent review dimensions — architecture,
full code review, performance, and duplication/efficiency — run as parallel agents; then a skeptic tries to
refute every candidate finding before it reaches the author. What remains is a short list of defects, each with
a concrete scenario that reproduces it.

The premise, as the skill states it: a plausible-but-wrong finding costs more than a missed one. It sends the
author (or the next agent) to rewrite working code, and it erodes trust in every later review. An empty review
is a valid result.

## When Claude uses it

The skill loads automatically when a request matches its description: a **code review, architecture review,
performance review, or duplication/efficiency analysis** of a diff, branch or PR, or a whole-subsystem audit.
You can also invoke it explicitly:

```
/review                  # the local diff against the default branch
/review 123              # a PR number or URL
/review feature-branch   # a branch (diffed against its merge base) or a path
/review audit <subsystem>
```

Asking in words ("review this PR", "audit the parser, be comprehensive") works the same way.

## What it does

| Step | What happens |
|---|---|
| 1. Establish the target | Local diff against the detected default branch (never assumed to be `main`), a PR via `gh pr diff`/`gh pr view`, a branch or path, or whole-source audit mode. For a PR that already has a review, it reads the conversation, reviews only commits pushed since, and does not re-raise findings the author already answered. An empty diff stops the review. |
| 2. Run the free checks | Build, linters/analyzers, tests scoped to the change, and any invariant checkers the repo names. Anything a tool catches needs no reviewer; a defect *class* a rule could catch gets a proposed rule. |
| 3. Triage | Skip dimensions that cannot apply, and say why (table below). A trivial diff gets a single direct pass with no agents. |
| 4. Calibrate | Two independent axes, **scale** and **consequence**, read from the project instructions or inferred (default *early users / standard*, stated as inferred). |
| 5. Parallel agents | One agent per selected dimension, all launched in one message, plus specialist agents where the change calls for them. |
| 6. Adversarial verification | A skeptic per candidate tries to refute it; when uncertain it defaults to *refuted*. Survivors are de-duplicated and ranked Critical → Warning → Suggestion. |
| 7. Sibling sweep | For each confirmed bug, search for the same shape elsewhere and report how the sweep was done. |
| 8. Report | A fixed report format. Posting to a PR is confirm-first; the skill never approves or requests changes on the author's behalf unless asked. |

**Triage rules:**

| Dimension | Skipped when the change is... |
|---|---|
| Architecture | a local fix inside one function with no new types, dependencies or call paths |
| Full code review | never skipped |
| Performance | docs, config, copy, styling or test-only, with no logic on a runtime path |
| Duplication and efficiency | docs-only; never skipped for new files |

**Specialist agents.** The repository ships four reviewers in [`agents/`](../../agents/) that run alongside the
dimension agents and go through the same skeptic: `silent-failure-hunter` (error handling, fallbacks, sentinels,
retries, "unsupported" arms, test filters), `pr-test-analyzer` (tests, goldens, any behavioral change),
`type-design-analyzer` (new or reshaped types and boundaries) and `comment-analyzer` (comments and citations,
especially ones justifying an omission).

**Every finding has the same shape:**

```
[SEVERITY] path/to/file.ext:L<start>-L<end> - <title>
Scenario: <inputs / state>  ->  <actual wrong result>  (expected: <correct result>)
Why: <the mechanism, pointing at the exact line>
Fix: <approach, and whether it is local or structural>
```

No scenario, no finding. For duplication, the scenario is the divergence: change the rule in place A, and path B
still does the old thing.

**Scale of the run.** "Review this diff" uses one finder per dimension and a single skeptic. "Audit this
subsystem" or "be comprehensive" uses several finders per dimension with different starting points, 3–5
independent skeptics per finding (a majority must fail to refute it), and a completeness critic that asks what
was *not* examined and sends finders there.

## Why it works this way

- **Filter, don't generate.** Wrong findings cost more than missed ones, so every candidate must survive an
  attempt to kill it, and uncertainty resolves to refuted.
- **A concrete scenario per finding.** "This could be cleaner" is a style opinion, not a defect. A scenario with
  inputs, actual result and expected result is what makes a finding checkable — by the skeptic and by the author.
- **Free checks first.** Judgment is spent only on what tools cannot already catch.
- **Two independent calibration axes.** Scale tunes architecture and performance; consequence tunes correctness.
  They are independent — the skill's example is a small internal payroll tool, low scale and high consequence.
  An author's stated context beats anything inferred.
- **Duplication is never skipped for new code.** New code is where duplication is born, and one rule written in
  two places is the usual reason a single case fails while its siblings pass.
- **What the skeptic checks goes beyond "is the code wrong".** A finding can cite a real rule and still describe a
  construct that cannot occur (check the premise). A citation can be genuine but answer a different question.
  "Nothing calls this" is a probe to run, not a conclusion. A correct verdict held for the wrong reason is a
  latent defect.
- **No fixed time limits in tests.** An assertion comparing elapsed time to a ceiling measures the machine, not
  the code; a loaded CI runner turns it red with no regression. The review asks for a property instead: a work
  count through a test seam, an observed effect, completion, or a growth ratio of two readings in the same run.
- **Drift rules are checked per file.** When the repo has invariant/drift tests, the rules governing each changed
  file are listed and the diff is checked against each — a change that breaks one is a finding even when its
  test was edited to pass.
- **Every confirmed bug is a pattern.** The most common shape is two arms of a dispatch with only one ever fixed.
  Saying which pattern and scope were searched turns a zero result into evidence rather than silence.
- **Findings become tracked work.** If the project names a tracker, the skill offers to file each survivor there
  rather than leaving it in prose that evaporates.

## Using it in your project

Specialize the skill without forking it by adding a section to `CLAUDE.md` (or a `.claude/review.md`, which the
orchestrator reads if present):

```markdown
## Review rules
- Project context: scale=long-lived, consequence=high
- Extra dimension: spec conformance - every behavior cites the governing clause of <standard>; verify the quoted
  text is at that clause, and that the code implements the rule rather than a paraphrase.
- Banned: floating point for money; any persistence outside the repository layer.
- Mechanical checks: `make lint && ./scripts/check-invariants.sh`
- File findings to: <tracker / path>
```

Each **extra dimension** becomes another parallel agent with the same finding format; **banned/required rules**
become hard criteria for every agent; **mechanical checks** run in Step 2; the named **tracker** is used in Step 8.
The skill recommends a spec-conformance dimension for standards-driven code (protocols, compilers, file-format
codecs, regulated calculations), because generic reviewers judge against intuition, and intuition is not the
standard.

Prerequisites: `git`; the `gh` CLI for PR targets and posting; subagent support for the parallel agents.

Composition: [`engineering-standards`](../engineering-standards/README.md) is the bar — every rule there is a
finding category here — and its `references/rule_index.py` is the per-file drift-rule query used in Full code
review. The four specialist agents live in the repository's `agents/` folder.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The review procedure, finding format, verification and report, as instructions to Claude |

## Credits

The skill's triage step and two-axis (scale × consequence) calibration come from
[carlymr/carlys-claude-skills](https://github.com/carlymr/carlys-claude-skills), as credited in `SKILL.md`. The
specialist agents it launches are adapted from Anthropic's `pr-review-toolkit`; see the repository's top-level
README for their license.
