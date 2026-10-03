# Standards and project hooks

Moved out of `SKILL.md` verbatim. Read it when the target repo has engineering standards or a CLAUDE.md `Review rules` section (or `.claude/review.md`), and before Step 2.

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
