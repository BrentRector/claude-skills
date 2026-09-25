# Specialist review agents

Four read-only reviewers, each focused on one class of defect that general code review tends to miss:
code that fails silently, tests that cannot fail, types that let illegal states compile, and comments or citations
that no longer tell the truth. Each one reports only findings it can back with a concrete scenario, in the same
format the [`review`](../skills/review/SKILL.md) skill uses, so their output can be merged with the four review
dimensions and pushed through the same adversarial verification.

| Agent | Hunts for | Question it asks |
|---|---|---|
| [`silent-failure-hunter`](silent-failure-hunter.md) | swallowed errors, default-value returns, fallbacks, no-op filters and gates, stubs reached at run time | *Where does something go wrong and the program carry on as if it had not?* |
| [`pr-test-analyzer`](pr-test-analyzer.md) | tests scoped to one bug, expected values copied from the program's own output, tests that never run, time-limit assertions | *Would these tests fail if the behavior were wrong?* |
| [`type-design-analyzer`](type-design-analyzer.md) | god classes, stringly-typed state, primitive obsession, illegal states, duplicated mechanisms | *What misuse compiles, and what future change drifts?* |
| [`comment-analyzer`](comment-analyzer.md) | comments the code contradicts, citations that do not hold, comments justifying a gap, stale history | *Would a reader who trusts this comment go wrong?* |

## What a subagent definition is

A Claude Code subagent is a Markdown file: YAML frontmatter followed by a system prompt. When Claude delegates to
it, the subagent runs in its own context window with only the tools the frontmatter allows, and returns a report.
Each file here uses these fields:

| Field | Meaning in these files |
|---|---|
| `name` | the identifier Claude (or you) uses to call the agent |
| `description` | when to use it; Claude reads this to decide whether a task matches |
| `tools` | `Read, Grep, Glob, Bash` for all four: they read code and can run things (a test, a search, a citation checker), but have no edit tools |
| `model` | `inherit`: the agent runs on the same model as the session that calls it |
| `color` | the label color Claude Code shows for the agent |

The body is the agent's instructions: what to find, how to rank harm, the finding format, and what not to report.

## Using them standalone

Installing the plugin (see the [top-level README](../README.md#install)) registers all four agents; the plugin
manifest lists them explicitly. You can then:

- **Let Claude pick.** When a task matches an agent's `description` (for example, "check the error handling in this
  change"), Claude can delegate to it on its own.
- **Ask by name.** "Run the pr-test-analyzer on my staged changes", "have the comment-analyzer check the citations in
  `parser.c`".
- **Copy a file** into your repo's `.claude/agents/` (or your user-level agents folder) if you want one agent without
  the plugin, keeping its change notice and the Apache-2.0 terms (see *License* below).

Run standalone, an agent's findings are candidates: nothing refutes them for you. Inside `review`, a skeptic does.

## When the `review` skill brings them in

The `review` skill launches these **alongside** its four dimension agents (architecture, full code review,
performance, duplication and efficiency), in the same parallel batch, when the change matches:

| Agent | Added when the change touches... |
|---|---|
| `silent-failure-hunter` | error handling, catch blocks, fallbacks, default/sentinel returns, retries, `?.`/`??`, "not implemented" or "unsupported" arms, test filters or gates - or whenever the review's consequence calibration is *high* |
| `pr-test-analyzer` | tests, goldens or fixtures, or any behavioral change |
| `type-design-analyzer` | new or reshaped types, enums, interfaces or module boundaries |
| `comment-analyzer` | comments, docstrings or citations of a spec, RFC, issue or design doc - especially ones justifying an omission |

They sharpen the Full code review and Architecture dimensions; they do not replace any dimension. Their findings go
through the same Step 6 skeptic as every other candidate, then the Step 7 sibling sweep.

## The agents

### silent-failure-hunter

Audits for any path where something went wrong and the program continues as though it had not. It ranks harm
explicitly, worst first:

1. **Silent wrong answer** - a plausible, incorrect result (a default, a truncated collection, a skipped record).
2. **Silent no-op** - the work did not happen and nothing says so (an empty catch, a filter that matched nothing).
3. **Late loud failure** - a stub that throws at run time for input the front end already accepted.
4. **Unactionable loud failure** - an error that loses its cause.

Targets include swallowed errors and discarded `Result`/`Option` values, default-value returns on failure,
unannounced fallback chains, lossy coercion, null-propagation that skips required work, partial success reported
as success, stubs reached at run time, and no-op gates ("zero failures" from a population of zero). Each finding
carries `Harm`, `Scenario`, `Why`, `Hides` (other errors the handler would swallow), `Fix` and `Siblings`.

**Why it is built this way.** A crash is not the worst outcome: a silent wrong answer is, because nobody knows to
look and downstream systems trust it. So the agent never recommends replacing a crash with a default, and the fix it
names is always the root cause (narrow the catch, propagate, reject early, implement the arm) - "never a better
fallback". It must look for the guard that makes a scenario impossible before reporting, and every confirmed
finding triggers a search for the same idiom elsewhere, reported with its scope so an empty result is evidence.

### pr-test-analyzer

Reviews test coverage by asking whether the tests would go red on a wrong implementation. Five checks:

1. **Scope** - enumerate the requirement's cases (branches, boundaries, error paths, both arms of a pair or
   dispatch, negative cases) and map tests to them. A fix tested only on the reported input is a finding.
2. **Oracle** - where did each expected value come from? Derived from the authority is good; captured from the code
   under test pins the bug. A test asserting "not supported yet" for legal input pins a gap as a decision.
3. **Discovery** - run the tests scoped to the change and check the **count executed**, not the exit code, since
   many runners exit 0 when a filter matches nothing. Where cheap, break the code and confirm the test goes red.
4. **Strength** - weak assertions, over-mocking, and tests that do not discriminate the rule they claim (a negative
   test whose input another rule also rejects; a generic error standing in for a specific diagnostic; a test of an
   implementation choice that every plausible choice passes).
5. **Determinism** - fixed time limits, wall-clock dates, unseeded randomness, order dependence, shared fixed paths.
   For a time-limit assertion it names a deterministic replacement: a work count, an observed effect, completion, or
   a growth ratio of two readings in the same run.

Findings carry `Check`, `Scenario` (the regression and which tests still pass), `Why` and `Fix`. It is read-only
except for running the suite to confirm discovery.

**Why it is built this way.** "Is there a test" is the wrong question. A golden file created from the program's own
output passes forever, a test that is never collected is "a green lie", and a stopwatch assertion "measures the
machine, not the code" and will eventually fail on a loaded CI runner with nothing wrong. Tests verify behavior; they
must not quietly shrink the behavior to the one case that prompted the change.

### type-design-analyzer

Reads each added or reshaped type - its definition, constructors, mutation points and a sample of callers - against
the bar "make illegal states unrepresentable, give each job exactly one mechanism, and prefer the shape that makes
the next similar case automatic." It looks for god classes, stringly-typed state, primitive obsession, illegal
states representable (a kind enum plus fields valid for only some kinds), invariants enforced by convention,
duplicated mechanisms (it must find and name the existing one first), and wrong-direction dependencies.

A type-design scenario is either a **misuse** (a call that compiles and yields a wrong state) or a **drift** (a
future change that updates one place and leaves another on the old rule). Findings carry `Smell`, `Scenario`,
`Why`, `Fix` (including whether it is local or a restructuring) and `Siblings`.

**Why it is built this way.** Design defects rarely fail today's tests; they fail the next change. Framing each
finding as a concrete misuse or drift keeps it out of taste territory, which the agent is told not to report. It
weighs long-term cost over diff size, prefers compile-time and construction-time guarantees, and pairs any
recommended consolidation with a drift test or invariant check so the fix stays true.

### comment-analyzer

Audits comments and documentation for **accuracy** only: claims the code contradicts; citations that do not hold;
comments that justify a gap ("not supported", "handled elsewhere", "nothing reads this"); and stale comments
describing a previous design. For every citation of a spec clause, RFC section, issue or design doc it opens the
source and confirms that the location exists, the quoted text is there, and it answers the question the comment
raises. If the project has a mechanical citation checker, it runs it.

Findings carry `Scenario` (what a reader who trusts the comment does, and the wrong outcome), `Evidence` and `Fix`.

**Why it is built this way.** "A comment that lies is worse than no comment: the next reader trusts it instead of the
code." The common citation failure is not an invented reference but an inherited one - real text, wrong clause -
or a real clause about something else used to justify an omission. Comments that justify a gap are treated as
claims to verify, because they are exactly where an unimplemented, reachable path hides. Style, verbosity and
grammar are out of scope unless they change meaning.

## The shared finding format

All four agents use the `review` skill's shape, each adding its own classification line:

```
[SEVERITY] path/to/file.ext:L<start>-L<end> - <title>
Scenario: <inputs / state>  ->  <actual wrong result>  (expected: <correct result>)
Why: <the mechanism, pointing at the exact line>
Fix: <approach, and whether it is local or structural>
```

Severity is **Critical**, **Warning** or **Suggestion**, defined per agent in its file; Suggestions are reported only
when asked. No scenario, no finding. Each agent is also told to say plainly when nothing survives and to list what it
examined, so an empty report is evidence rather than silence.

These rules replace the upstream versions' 1-10 ratings and general advice: the aim is a short list of defects that
reproduce, not a volume of opinions.

## Files

| File | Role |
|---|---|
| [`silent-failure-hunter.md`](silent-failure-hunter.md) | subagent: silent failures, ranked by harm |
| [`pr-test-analyzer.md`](pr-test-analyzer.md) | subagent: scope, oracle, discovery, strength and determinism of tests |
| [`type-design-analyzer.md`](type-design-analyzer.md) | subagent: type and module design |
| [`comment-analyzer.md`](comment-analyzer.md) | subagent: accuracy of comments and citations |
| `README.md` | this file |

## License

The four agent files are modified versions of the agents in the `pr-review-toolkit` plugin of
[anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official), Copyright Anthropic,
licensed under the Apache License, Version 2.0. As modified they remain under Apache-2.0, not the repository's MIT
license. Each file carries a notice at its top stating that it was changed and summarizing the changes. See the
repository [NOTICE](../NOTICE) and [LICENSES/Apache-2.0.txt](../LICENSES/Apache-2.0.txt).
