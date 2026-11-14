# Adversarial verification and the sibling sweep (Steps 6 and 7)

## Step 6 detail

Agent output is **candidate findings, not conclusions**. A skeptic's job is to REFUTE each candidate (for a diff,
one skeptic agent takes every candidate; an audit uses 3-5 per finding, `report-and-scale.md` *Scale*): read the
code, look for the guard, invariant, framework guarantee or upstream validation that makes the scenario impossible,
and try to actually run the scenario when that is cheap (a unit test, a REPL, a one-line script).
**When uncertain, the skeptic defaults to refuted.** Only findings the skeptic could not kill survive.
Find-then-verify has found real bugs that green tests missed, and on other diffs it has correctly found nothing: a
null result is a valid outcome, and running the scenario is what verifies a finding.

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

Then synthesize: de-duplicate (keep the most specific version), drop a low finding that fixing a graver one would
resolve, apply the calibration, and rank critical → high → medium → low → info (`report-and-scale.md` *Severity*).

## Step 7 detail

Every confirmed bug is a pattern. For each survivor, ask where else the same shape lives and search for it: the
other arm of the same dispatch (the most common shape - two arms, only one ever fixed), the paired function, the
copy-pasted neighbor, the same idiom elsewhere in the codebase. Report siblings under their parent finding, and say
how the sweep was done (which pattern, which scope) so a zero result is evidence rather than silence.

Reviewing a fix, read the fix's own sweep record the same way. It passes when it is a table: each query
(structural or semantic where the language allows: every caller of the predicate, every consumer of a new value
kind, every arm of the dispatch), the matches it returned and how each was settled (fixed, cleared with its reason,
or a lead), and a calibration line showing the query matched the origin before the fix. A sentence ("swept, no
other instances"), a table with no calibration line, or a table of textual greps only where the mechanism has a
symbol or a dispatch (so a renamed or escaped form could hide) is a finding of at least **medium**: the missed arm is the defect the next reader files. Likewise each new test or witness names the defect
or mutation it was seen to fail under; a witness never seen red is at least **medium**, and one shown unable to
fail is **critical** (`report-and-scale.md` *Severity*).
