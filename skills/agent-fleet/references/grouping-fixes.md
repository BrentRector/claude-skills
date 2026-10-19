# Grouping related fixes for each implementer

The full text of agent-fleet section 7. Read it before filling implementer slots or assigning defects to implementers.

## 7. Group related fixes for each implementer

- **The unit you fill a slot with is a group**: the top-ranked item plus every open item that shares its source
  files or rule family (3–4 items, one branch, one gate, one report with a section per item). Inside the group,
  each item is still fixed at its root and checkpointed separately.
  *Why: separate implementers on the same files produced merge conflicts and composition defects that neither
  could see.* *(Practice — not yet validated: no before/after measure of conflicts or composition defects per landing.)*
- **Compute the groups from code sites; don't pick them by hand.** Resolve every open defect's named code sites
  (paths, `Type.Member`, type names) to real source files, give each note a PRIMARY file (its heaviest site, ties
  to the more specific file), and cluster notes by it: cap ~5 per cluster, split larger ones by harm, absorb a
  singleton into a cluster whose file it also names (another singleton included: two one-note files that name
  each other are one pass). Rank clusters by SUMMED harm and fill each slot with the top cluster of a subsystem
  not already in flight. `references/fix_clusters.py` does this over a directory of front-matter notes
  (`--notes`, `--src`, `--ext`, `--harm`, or `.agent-fleet.json`); a site counts only if it resolves to a real
  file (a stale path to a moved file is not a site, and generated code is excluded with `--exclude-dir`). It is a
  view recomputed each run, never a second list to maintain.
  *Why: hand-picked groups (a lead plus keyword siblings) carried 1–3 notes each and split one file's defects
  across two implementers who then edited it separately; computed clusters turned 411 open defects into 125
  groups (42 of five), so a six-slot wave carried ~25–30 fixes instead of ~10, each file read and gated once.* *(Practice — not yet validated: no before/after measure of fixes landed per wave.)*
- **A file with more open items than the cluster cap gets SAME-FILE SUCCESSORS**, not a second independent group.
  The second cluster declares its predecessor (`after`). It merges the predecessor's branch and orients from the
  predecessor's handoff notes (its report's "for the next implementer" section and checkpoint file) instead of
  re-surveying the file. The same chaining works across one technological area (a runtime file, then its emitter). A
  dispatch check can refuse two groups on one primary file that are not linked this way.
  *Why: orientation (reading and searching before the first edit) was about half of every implementer's tokens,
  so two groups that each orient on the same file pay that twice. The cap exists because cost grows with the
  square of a transcript's turns. That is also why the successor is a FRESH agent that inherits the context,
  not a longer transcript that inherits the cost.* *(Practice — not yet validated: no A/B against independent groups.)*
- **Nothing is held for a successor: each link lands on its own, and a successor merges its predecessor's REVIEWED
  head.** The predecessor is reviewed the moment it returns, in its own slot, and enqueued the moment its review ends
  CLEAN. The successor starts once that review loop has ended (CLEAN, FINDINGS at the round cap, or a review or
  finisher that did not finish), merges the predecessor's FINAL head (the finisher's, when one ran), and is told how it
  ended: reviewed CLEAN, so it lands now and the successor's pull request merges on top; or FINDINGS, so the successor's
  branch carries them and is enqueued only after they are answered. The landing order is communicated, never enforced
  by holding. The successor's round-1 review leaves the predecessor's content reviewed CLEAN alone, does not record
  again findings capped in the predecessor's own findings file, and covers as its own any predecessor content whose
  review or finisher did not finish. A predecessor branch with no clean review at its tip is contained in the successor
  and lands through it: the landing survey reads it in flight via its carrier, never as a branch to decide or review
  again.
  *Why: holding a predecessor to land "through" its successor dates from trains, when two same-file branches had to
  ride one; with one pull request per branch through a merge queue it saves nothing and only postpones. In one wave a
  six-link chain had six groups DONE over seven hours and none landed: a predecessor reviewed by 08:43 waited for its
  successor, another was reviewed only after its successor returned, and a successor built on its predecessor's UNFIXED
  head made its reviewer restate the predecessor's findings.* *(Validated 2026-10-18 on one campaign: the chain that had
  landed nothing in seven hours; the new rule's landing times are not yet measured.)*
- **Fill parallel slots with one group per subsystem**, not the next N items down the rank list.
  *Why: consecutive items in one area serialize on conflicts.* *(Practice — not yet validated: conflicts per landing were not measured before and after.)*
- **Cluster leads by root cause before dispatching.** *Why: one mechanism, one fix; the group above is how
  related mechanisms share one agent.*
- **Don't put two unrelated mechanisms in one transcript.** Related ones that share files are grouped (above),
  because they share orientation. *(Practice — not yet validated: the cost argument once given for it was modelled, never measured.)*
