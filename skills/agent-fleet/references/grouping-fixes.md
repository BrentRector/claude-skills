# Grouping related fixes for each implementer

The full text of agent-fleet section 7. Read it before filling implementer slots or assigning defects to implementers.

## 7. Group related fixes for each implementer

- **The unit you fill a slot with is a group**: the top-ranked item plus every open item that shares its source
  files or rule family (3–4 items, one branch, one gate, one report with a section per item). Inside the group,
  each item is still fixed at its root and checkpointed separately.
  *Why: separate implementers on the same files produced merge conflicts and composition defects that neither
  could see.* *(Practice — not yet validated: no before/after measure of conflicts or composition defects per train.)*
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
  The second cluster declares its predecessor (`after`). It waits for the predecessor to return, merges its
  branch, and orients from the predecessor's handoff notes (its report's "for the next implementer" section and
  checkpoint file) instead of re-surveying the file. The predecessor's branch is held from the trains and lands
  THROUGH the successor, which contains it; if the successor produces nothing landable, the predecessor lands
  alone. The same chaining works across one technological area (a runtime file, then its emitter). A dispatch
  check can refuse two groups on one primary file that are not linked this way.
  *Why: orientation (reading and searching before the first edit) was about half of every implementer's tokens,
  so two groups that each orient on the same file pay that twice. The cap exists because cost grows with the
  square of a transcript's turns. That is also why the successor is a FRESH agent that inherits the context,
  not a longer transcript that inherits the cost.* *(Practice — not yet validated: no A/B against independent groups.)*
- **Fill parallel slots with one group per subsystem**, not the next N items down the rank list.
  *Why: consecutive items in one area serialize on conflicts.* *(Practice — not yet validated: conflicts per train were not measured before and after.)*
- **Cluster leads by root cause before dispatching.** *Why: one mechanism, one fix; the group above is how
  related mechanisms share one agent.*
- **Don't put two unrelated mechanisms in one transcript.** Related ones that share files are grouped (above),
  because they share orientation. *(Practice — not yet validated: the cost argument once given for it was modelled, never measured.)*
