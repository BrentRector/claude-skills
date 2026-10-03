# After a fleet, on restart, and the standards

The full text of agent-fleet section 12 and the Standards section. Read it after any fleet that could touch the tree, after a cutoff, and before writing an implementer brief's quality bar.

## 12. After a fleet, and on restart

**After any fleet that could touch the tree:** run `git status --short` and account for every unexpected path
**before** `git add -A`, or stage explicit paths. *Why: agents drop files into the repo root despite
scratch-only ground rules. The prompt constrains intent, not effects.* *(Practice — not yet validated: no recorded catch; a stray file was still committed after the check was adopted.)*

**On restart after a cutoff:**
1. Read the reset time from the limit message. It is not a fixed hour.
2. Check the dead lander's worktree and its `STATUS.md` (and `git status` on main, if your landers apply there).
   Confirm each step it finished (an idempotent step re-run changes nothing), discard and redo a step the kill
   left half-done, and never promote a WIP commit to main. *(Practice — not yet validated: three killed landings were recovered this way; not yet re-validated.)*
3. Run `git worktree list`, then run `references/status_delta.py <worktree>` on each to see which agents are near
   done and exactly which commits their `STATUS.md` does not cover.
4. Dispatch **fresh** agents from the checkpoints, in landing order. Resume an agent in place (with its context
   intact) only if it is within a step of finishing. Completed workflow stages replay from their on-disk outputs;
   if a resume by run id fails (it did after the owning process died), re-dispatch as a new run. *(Practice — not yet validated: the run-id failure was never reproduced.)*

## Standards

The bar is the **engineering-standards** skill, and agents only meet the bar their brief states. So:

- **Every implementer brief carries the quality bar** (production quality, root cause, complete to spec, one
  mechanism, sibling sweep, docs current) and names the project's own rules. *Why: agents optimize against the
  criterion written down.*
- **Forbid the smallest-diff fix that contradicts the bar.** A brief's scope is an estimate; when the correct fix
  needs restructuring, the agent either does it or stops and reports the real size. It never ships a workaround
  to stay inside the estimate.
- **The report states what was swept** (the pattern and the search) and which invariants or drift tests were
  added, and each one was seen to fail once.
- **Refuters check the standards too:** a fix that papers over a symptom or leaves a sibling is overturned even
  when its tests pass.
