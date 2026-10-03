# The four dimensions and the specialist agents (Step 5)

Moved out of `SKILL.md` verbatim. Read it before launching the Step 5 agents: it holds the criteria each agent is given.

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
place of a real sleep or timeout, or completion. A timing ratio of two readings in the same run is not a
replacement: one went red on unchanged code *(Practice — not yet validated: the no-ceiling rule has been exercised once so far.)* · **the
structural rules that govern each changed file**: when the repo has invariant/drift tests, list the rules for every
changed file (`engineering-standards/references/rule_index.py --tests "<glob of your drift tests>" <file>`, or the repo's own query) and check the diff
against each; a change that breaks one is a finding even when its test was edited to pass.

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

They sharpen Full code review and Architecture; they do not replace any dimension. *(Practice — not yet validated: the evals show they change what Claude does; no catch in real work is measured yet.)*
