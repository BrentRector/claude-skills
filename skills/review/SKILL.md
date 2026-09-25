---
name: review
description: Use when asked for a code review, architecture review, performance review, or duplication/efficiency analysis of a diff, branch or PR (or a whole subsystem audit) - runs the four review dimensions (architecture, full code review, performance, duplication and efficiency) as parallel agents, requires a concrete failure scenario for every finding, adversarially verifies each finding before reporting it, and sweeps every confirmed defect for its siblings.
argument-hint: "[PR number/URL | branch | path | 'audit <subsystem>'] (optional, defaults to the local diff)"
---

# Review

Four independent review dimensions, run in parallel, followed by an adversarial verification pass that tries to
kill every finding before it reaches the author. The output is a short list of defects that survived an honest
attempt to refute them, each with a scenario that reproduces it.

The premise: a plausible-but-wrong finding costs more than a missed one. It sends the author (or the next agent) to
rewrite working code, and it erodes trust in every later review. So this skill is built to *filter*, not to
generate volume. An empty review is a valid result.

Triage and calibration ideas from carlymr/carlys-claude-skills.

## Step 1 - Establish the target

- **No argument:** the local diff against the default branch (detect it: `git symbolic-ref refs/remotes/origin/HEAD`,
  never assume `main`), including staged and unstaged changes.
- **PR number/URL:** `gh pr diff`, `gh pr view` for the description and linked issue.
- **Branch or path:** diff the branch against its merge base, or review the named files/directories.
- **"Audit" / "be comprehensive" / a subsystem name:** whole-source mode (see *Scale* below).
- **Incremental PR mode:** if the PR already carries a review from a previous run, read the full conversation first
  (`gh pr view --json reviews,comments`), diff only the commits pushed since that review, and open the report with
  `Incremental review - changes since <timestamp>`. Do not re-raise a finding the author already answered with a
  justification. No new commits → say so and stop.

Empty diff → say so and stop.

## Step 2 - Run the free checks first

Before spending judgment, run whatever the repo already mechanizes: the build, the linters/analyzers, the test
suite scoped to the change, and any invariant checkers (Semgrep rules, architecture tests, custom scripts named in
the project instructions). Anything a tool already catches needs no reviewer. And when the review later finds a
defect *class* a rule could catch, propose the rule, not only the instance.

## Step 3 - Triage: which dimensions apply

Skip dimensions that clearly cannot apply, and say which were skipped and why.

| Dimension | Skip when the change is... |
|---|---|
| Architecture | a local fix inside one function with no new types, dependencies or call paths |
| Full code review | never skipped |
| Performance | docs, config, copy, styling or test-only, with no logic on a runtime path |
| Duplication and efficiency | docs-only; **never** skip for new files - new code is where duplication is born |

A genuinely trivial diff (typo, version bump, comment) gets a direct single-pass review with no agents; state that
a full review was not warranted.

## Step 4 - Calibrate: two independent axes

Read the project's instructions (CLAUDE.md, README) for explicit context first; an author's statement beats
anything inferred. The axes are independent - a small internal payroll tool is low-scale and high-consequence.

- **Scale** (tunes architecture and performance): *pre-launch* - drop speculative scale concerns, downgrade perf
  and architecture to suggestions · *early users* - flag clear regressions, no premature optimization · *at scale*
  or *long-lived* (a product expected to be maintained for years) - full rigor; structural debt compounds.
- **Consequence** (tunes correctness): *low* - recoverable, nothing sensitive · *standard* - normal product code ·
  *high* - money, PII, auth, compliance, safety, data loss, or output other systems trust - edge cases are real.

If nothing is stated, assume *early users / standard*, say that you inferred it, and suggest the author add a line
such as `Project context: scale=long-lived, consequence=high` to CLAUDE.md. Pass both axes to every agent.

## Step 5 - The four dimensions, as parallel agents

Launch one agent per selected dimension **in a single message** so they run concurrently. Give each the diff (or
subsystem), the changed-file list, the PR description, the calibration, any project review rules (see *Project
hooks*), and its criteria below. Each agent reads surrounding code as needed - a diff alone hides most defects.

**1. Architecture.** Layout and naming match the codebase's conventions · single responsibility, no god classes ·
clean layer/phase boundaries (no business logic in the parser or controller, no I/O in the domain model, no
compile-time structure carrying runtime concerns) · no cross-layer write-back (a later stage mutating an earlier
stage's model) · **one canonical mechanism per job** - a second parallel mechanism for something that already exists
is a defect even when both work · dependencies point the right way · the shape makes the *next* similar case
automatic rather than making this case small.

**2. Full code review.** Correctness against the requirement the code claims to implement - the cited spec, issue
or contract, not a convenient paraphrase of it · paired and sibling functions agree (encode/decode, read/write,
the two arms of a dispatch) · error handling fails loudly; no silent no-op, swallowed exception or default that
masks bad input · boundary values, empty/null, overflow, concurrency, resource lifetime · comments and docs are
accurate (a comment that lies is worse than none) · idiomatic for the language and its current version · tests
exercise every branch the change added · **no fixed time limit in a test**: an assertion that compares a stopwatch or
elapsed-time reading against a ceiling is a finding - it measures the machine, not the code, and a loaded CI runner
turns it red with no regression. Ask for the property instead: a work count through a test seam, an observed effect in
place of a real sleep or timeout, completion, or a growth ratio of two readings taken in the same run.

**3. Performance.** Hot paths and allocation behavior · data-structure fit · algorithmic complexity over realistic
input sizes (O(n^2) over a collection that grows with the user's data) · redundant I/O, N+1 queries, repeated
parsing · copies where a view would do (e.g. `Span<T>` in .NET, slices in Go/Rust, `memoryview` in Python) ·
caching that is missing, or caching that is stale. A performance finding needs an input size at which it matters.

**4. Duplication and efficiency.** Repeated logic, including near-duplicates that differ by a constant · two
mechanisms doing one job · recomputing what an earlier stage already resolved · one rule written down in more than
one place (the usual reason a single case fails while its siblings pass - the extraction *is* the fix) · anything a
single canonical implementation should absorb. This is the dimension most often skipped; do not skip it.

### Specialist agents

This plugin ships four specialist reviewers in `agents/`. Launch them **alongside** the dimension agents, in the
same message, when the change matches; their findings use the same format and go through the same Step 6
skeptic.

| Agent | Add it when the change touches... |
|---|---|
| `silent-failure-hunter` | error handling, catch blocks, fallbacks, default/sentinel returns, retries, `?.`/`??`, "not implemented" or "unsupported" arms, test filters or gates - or whenever consequence is *high* |
| `pr-test-analyzer` | tests, goldens or fixtures, or any behavioral change (checks scope, where expected values came from, and that new tests actually run) |
| `type-design-analyzer` | new or reshaped types, enums, interfaces or module boundaries |
| `comment-analyzer` | comments, docstrings or citations of a spec, RFC, issue or design doc - especially ones justifying an omission |

They sharpen Full code review and Architecture; they do not replace any dimension.

### What every finding must carry

```
[SEVERITY] path/to/file.ext:L<start>-L<end> - <title>
Scenario: <inputs / state>  ->  <actual wrong result>  (expected: <correct result>)
Why: <the mechanism, pointing at the exact line>
Fix: <approach, and whether it is local or structural>
```

No scenario, no finding. "This could be cleaner" or "consider X" is a style opinion, not a defect; drop it unless
the calibration explicitly asks for suggestions. For duplication, the scenario is the divergence: *change rule R in
place A, and path B still does the old thing.*

## Step 6 - Adversarial verification

Agent output is **candidate findings, not conclusions**. For each candidate, spawn a skeptic whose job is to
REFUTE it: read the code, look for the guard, invariant, framework guarantee or upstream validation that makes the
scenario impossible, and try to actually run the scenario when that is cheap (a unit test, a REPL, a one-line
script). **When uncertain, the skeptic defaults to refuted.** Only findings the skeptic could not kill survive.

What the skeptic checks, beyond "is the code wrong":

- **The premise, not only the rule.** A finding can cite a real requirement correctly and still be impossible -
  the construct it describes cannot syntactically or structurally occur. Check what the input can actually be.
- **The citation answers the question asked.** A comment or finding that justifies an omission often cites a real
  clause about something else. Verify the quoted text says what is claimed, at the location claimed.
- **Reachability is measured, not deduced.** "Nothing calls this" and "not observable yet" are probes to run
  (search the callers, add an assertion, run the test), never conclusions.
- **Right answer, wrong reason.** When the skeptic agrees, check it agrees with the *reasoning*. A correct verdict
  held for a wrong reason is a latent defect; record the corrected rationale.
- **Cost/benefit.** Drop findings whose scenario is theoretically possible but practically unreachable, whose fix
  adds more complexity than the risk warrants, or that defend against something the architecture already prevents.

Then synthesize: de-duplicate (keep the most specific version), drop a suggestion that fixing a critical would
resolve, apply the calibration, and rank Critical → Warning → Suggestion.

## Step 7 - Sweep for siblings

Every confirmed bug is a pattern. For each survivor, ask where else the same shape lives and search for it: the
other arm of the same dispatch (the most common shape - two arms, only one ever fixed), the paired function, the
copy-pasted neighbor, the same idiom elsewhere in the codebase. Report siblings under their parent finding, and say
how the sweep was done (which pattern, which scope) so a zero result is evidence rather than silence.

## Step 8 - Report

```markdown
# Review
**Target:** <diff / PR / subsystem>  **Context:** scale=<...>, consequence=<...> (<stated | inferred from ...>)
**Dimensions run:** <list>; skipped: <dimension - reason>
**Verification:** <N> candidates -> <M> survived

## Critical / ## Warnings / ## Suggestions   (omit empty sections)
### path/file.ext:L10-L25 - <title>
Scenario / Why / Fix, as above.  Siblings: <locations, or "swept <pattern> in <scope>: none">
```

If nothing survives, say so plainly. **Findings become tracked work**: if the project names an issue tracker or work
register, offer to file each surviving defect there rather than leaving it in prose that evaporates.

**Posting is confirm-first.** For a PR, show the report and ask before posting; then write it to a temp file and
post with `gh pr review <n> --comment --body-file <file>` (a file avoids shell-escaping damage). Never approve or
request changes on the author's behalf unless asked.

## Scale

- **"Review this diff"** - the selected dimensions, one finder per dimension, single-skeptic verification.
- **"Audit this subsystem" / "be comprehensive"** - several finders per dimension with different starting points,
  3-5 independent skeptics per finding (majority must fail to refute), plus a **completeness critic** that asks what
  was *not* examined - files, paths, error branches, configurations - and sends finders there.

## Standards

The bar is the **engineering-standards** skill; every rule there is a finding category here. In review context:

- A god class, a second mechanism for a job something already does, or one rule written down in two places is a
  finding even when every test passes. Its scenario is the drift: change it in place A, and B keeps the old rule.
- A workaround, fallback, retry loop, special case to match an expected output, or edit of valid input to dodge a
  bug is a finding. The fix named is the root cause, never a better workaround.
- Every confirmed bug triggers the Step 7 sibling sweep, including the other arm of the same dispatch.
- A fix shaped to the smallest diff where the defect class calls for restructuring is a Warning: name the shape
  that makes the next case automatic.
- Missing invariants or drift tests for a collapse, a feature scoped to what its test references, and docs left
  stale by the change are findings too.

## Project hooks

The skill is generic; a repository specializes it without forking by adding a section to its CLAUDE.md (or
`.claude/review.md`, which the orchestrator reads if present):

```markdown
## Review rules
- Project context: scale=long-lived, consequence=high
- Extra dimension: spec conformance - every behavior cites the governing clause of <standard>; verify the quoted
  text is at that clause, and that the code implements the rule rather than a paraphrase.
- Banned: floating point for money; any persistence outside the repository layer.
- Mechanical checks: `make lint && ./scripts/check-invariants.sh`
- File findings to: <tracker / path>
```

The orchestrator honors these by: adding each **extra dimension** as a fifth (sixth ...) parallel agent with the
stated criteria and the same finding format; giving every agent the **banned/required rules** as hard criteria;
running the **mechanical checks** in Step 2; and using the named **tracker** in Step 8. Standards-driven code
(protocol implementations, compilers, file-format codecs, regulated calculations) should almost always add a
spec-conformance dimension: generic reviewers judge code against intuition, and intuition is not the standard.
