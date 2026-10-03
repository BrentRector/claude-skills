# Adversarial verification and the sibling sweep (Steps 6 and 7)

Moved out of `SKILL.md` verbatim. Read it before spawning the Step 6 skeptics, and again before the Step 7 sweep.

## Step 6 detail

Agent output is **candidate findings, not conclusions**. For each candidate, spawn a skeptic whose job is to
REFUTE it: read the code, look for the guard, invariant, framework guarantee or upstream validation that makes the
scenario impossible, and try to actually run the scenario when that is cheap (a unit test, a REPL, a one-line
script). **When uncertain, the skeptic defaults to refuted.** Only findings the skeptic could not kill survive.
Find-then-verify has found real bugs that green tests missed, and on other diffs it has correctly found nothing: a
null result is a valid outcome, and running the scenario is what verifies a finding. *(Practice — not yet validated: this narrowed claim has not been re-validated; an earlier claim that it finds real bugs in every phase was refuted.)*

What the skeptic checks, beyond "is the code wrong":

- **The premise, not only the rule.** A finding can cite a real requirement correctly and still be impossible -
  the construct it describes cannot syntactically or structurally occur. Check what the input can actually be. *(Validated 2026-09-28.)*
- **The citation answers the question asked.** A comment or finding that justifies an omission often cites a real
  clause about something else. Verify the quoted text says what is claimed, at the location claimed. *(Validated 2026-09-28.)*
- **Reachability is measured, not deduced.** "Nothing calls this" and "not observable yet" are probes to run
  (search the callers, add an assertion, run the test), never conclusions.
- **Right answer, wrong reason.** When the skeptic agrees, check it agrees with the *reasoning*. A correct verdict
  held for a wrong reason is a latent defect; record the corrected rationale. *(Validated 2026-09-28.)*
- **Cost/benefit.** Drop findings whose scenario is theoretically possible but practically unreachable, whose fix
  adds more complexity than the risk warrants, or that defend against something the architecture already prevents.

Then synthesize: de-duplicate (keep the most specific version), drop a suggestion that fixing a critical would
resolve, apply the calibration, and rank Critical → Warning → Suggestion.

## Step 7 detail

Every confirmed bug is a pattern. For each survivor, ask where else the same shape lives and search for it: the
other arm of the same dispatch (the most common shape - two arms, only one ever fixed), the paired function, the
copy-pasted neighbor, the same idiom elsewhere in the codebase. Report siblings under their parent finding, and say
how the sweep was done (which pattern, which scope) so a zero result is evidence rather than silence. *(Validated 2026-09-28.)*
