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
