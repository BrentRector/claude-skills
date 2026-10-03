# Verification and invariants (engineering-standards section 5)

## 5. Verification and invariants

- **Propose invariants, validators and drift tests unprompted.** With each change, ask "what could go wrong?" and
  encode the answer as a check that fails.
  *Why: they should arrive with the change, not after someone asks.*
- **Prefer structural guarantees to conventions.** An exhaustive generated switch, a dependency graph asserted at
  construction, or a type that cannot represent the invalid state beats a comment asking the reader to remember.
- **Pin every collapse with a drift test.** When two copies become one, add a test that fails if a copy
  reappears; when a model restates what an engine decides, add a test that cross-checks them.
- **Surface the drift rules BEFORE the edit, from one home.** Each structural test states its rule in its own doc
  comment — that is the rule's only home. Generate an index from them and answer "which rules govern this file?" before
  anyone edits it (`references/rule_index.py`: `--tests "<glob>"` regenerates the index, `--check` in CI fails when it
  is stale or a test states no rule, `<file>` lists the governing rules). Never copy the rules into docs or skills.
  *Why: 200+ drift tests whose rules lived only in the tests were rediscovered one red gate at a time; copying them
  into a skill would have made a second copy of every rule to drift.*
- **A guard that cannot fail is not a guard. Make every new check fail once, for the right reason.** Restore the
  defect or point it at an old revision before trusting its green.
  *Example: a test that verified a registry against the same reflection scan that populated it asked "did the
  scan find what the scan found?" and could never fail.* *(Validated 2026-09-28.)*
- **Ask what a check's scope EXCLUDES, and whether each exclusion's premise is still true.** Couple every
  exemption to the precondition that justifies it. *(Validated 2026-09-28.)*
- **Verify the values, not "it ran".** Assert on specific output values, never on exit codes alone. *(Validated 2026-09-28.)*
- **Compute expected results from the authority** (the spec, the contract), never by copying an oracle's output. *(Validated 2026-09-28.)*
- **Every measurement carries a witness** (a count, a version, a marker) that proves it did the work, and you
  check the witness before reporting. A stale binary, a swallowed argument or a filter that matched nothing all
  look like a pass.
- **Reachability is measured, not deduced.** "Nothing calls this" and "not observable" are claims with a probe
  attached. Run the probe and record the result.
- **Vary the axis your current subject holds fixed.** A probe built while working on X inherits X's premise, so
  flip that property before believing a green result. *(Validated 2026-09-28.)*
- **Compare against an independent implementation, not a round trip of your own.** A model that loses the same
  information on read and write passes its own round trip perfectly.

