# Correctness, root cause and completeness (engineering-standards sections 3 and 4)

## 3. Correctness and root cause

- **Fix the root cause. Never paper over a symptom.** No retry loops, no "skip this case", no environment flag
  that hides the output, no special-casing to match an expected answer.
  *Why: a workaround leaves the defect in place to hit the next input, and hides it while it waits.*
- **Never change valid input to dodge a bug in the tool.** If a valid program, file or query fails, the tool is
  broken; the failure is the signal pointing at the bug. A written rule reduces this, but has not
  stopped it. *(Validated 2026-09-28.)*
- **Never relabel a bug a "quirk" or "known limitation".** Honest diagnosis has always turned out to be a real bug.
- **When a correction arrives, fix the interpretation, not the output.** Treat "this result is wrong" as evidence
  that the model is wrong, and find the general flaw that makes every observation fall out correctly.
  *Why: special-casing to the correction overfits and breaks on the next case.*
- **Every bug is a pattern: sweep for its siblings in the same change.** Name the pattern, search the whole
  codebase (code and docs), fix every instance, and add a test that catches a recurrence.
  *Why: every time this was skipped, the siblings existed.* Show the search you ran; "swept" without the query is
  an assertion, not evidence. *(Validated 2026-09-28.)*
- **Two-arm dispatch: ask which arm you fixed, and what the other one is.** Exact vs approximate path,
  validating vs value-producing twin, read vs write half, debug vs release.
  *Why: a repro exercises one arm, the existing tests follow the same arm, and the other arm survives a green
  suite.* At the second occurrence, restructure so both arms share one rule.
- **Implement the named operation, not a convenient equivalent.** When a spec or contract names an exact
  operation or rounding or error condition, implement that, not a nearby library call that behaves slightly
  differently.
- **Diagnose from evidence, never from a plausible story.** State what is known, then read the code, dump the
  data, reproduce in isolation. "Probably because..." is not a diagnosis.
- **A remembered pattern is a hypothesis.** When a known bug shape fits the symptom, find its mechanism in THIS
  code before acting. If you cannot point at it, the pattern does not apply. Likewise re-measure a work item's stated premise on today's code before fixing it: it may
  have been reasoned rather than measured, or already fixed by another change. *(Validated 2026-09-28.)*
- **Apply a coordinated set of fixes as one change and test once.** Cherry-picking pieces of an interdependent
  fix, then reverting some of them, creates states worse than either end.
- **Output must be reproducible.** The same input produces the same output: no process-randomized hashes, no
  wall-clock stamps in artifacts.
  *Why: nondeterminism makes every later comparison meaningless.*

## 4. Completeness

- **Implement the COMPLETE feature to its spec or design. Tests verify; they do not scope.** Enumerate every rule
  the feature owes and build all of it.
  *Why: a slice shaped by one test fails the next real input and re-litigates the design.* *(Validated 2026-09-28.)*
- **Deferral is debt, and only the owner may choose it.** "Documented limitation", "follow-up pass", "staged",
  and a loud rejection of valid input are all forms of unfinished work. If the full job is genuinely large,
  surface the size as a decision; do not pre-decide the deferral.
- **Never ship a half-feature.** Parsing something and silently doing nothing is worse than an error: the program
  runs and produces wrong results. The feature, its tests and its docs land together. *(Validated 2026-09-28.)*
- **Handle every legal input shape, not the shapes you happen to use.** A bug found on your own code is a bug a
  user will hit; fence it with a standalone regression test.
- **Future-proof when the option exists.** Take the hardening path (the extra validator, the gate, the
  re-verification trigger) rather than labeling it optional.

