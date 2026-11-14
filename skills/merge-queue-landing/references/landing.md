# Landing: the detail behind the skill

The reasons, specifications and settings behind the `merge-queue-landing` SKILL.md. Read it before writing the enqueue
script, the findings reader or the branch survey, or before changing the CI triggers or the ruleset.

## Why the pipeline has this shape

One whole-population run, in the merge queue; nothing serial held through a CI wait; no agent does every landing step.
Done the other way, each of those makes landings slow: a host that runs what CI runs and then waits for CI to run it
again, a lease held through the CI wait that makes big batches rational (so one red re-gates the batch), and one agent
that runs long enough to need successors.

## What the enqueue step's partition check may block

A file-set partition orders only INDEPENDENT work that touches the same file. In-flight work that DESCENDS from the
landing branch (their merge-base lies beyond the default branch: a successor, a finisher or a carrier that merged
some head of it) never blocks the landing, because it lands on top of it; and a worktree with no commit beyond the
default branch blocks nothing. *Why: a successor that merged an OLDER head of its predecessor shares files with
the predecessor's reviewed branch, and an empty finisher worktree in mid-merge looks the same; treating either as
independent work stops a landing whose gates are green.*

## The ruleset and CI triggers

- **One pull request per finished branch.** *Why: with a queue, a red bounces one branch while the others land; a
  batch of branches in one pull request re-gates the whole batch for one red.*
- **A ruleset on the protected branch** (classic branch protection has no merge queue): require a pull request; require
  the merge queue with merge method **merge commit**; the required check evaluated on the merge group; enforced for
  administrators (often the account that makes every push); a minimum group size of 1, a maximum of a handful, a check
  timeout about four times CI's wall. *Why merge commits, not squash: a squashed head is never an ancestor of the default
  branch, so every lifecycle tool that asks "is this branch landed?" (`git branch --merged`, `git cherry`, a prune script)
  would have to key on the merged-PR record instead. With merge commits the branch's commits stay ancestors, and
  `git log --first-parent` reads one merge commit per landing whose message is the forensic record.*
- **CI triggers:** the full matrix on `merge_group` and on manual dispatch; cheap checks on `pull_request`; a record run on
  `push` to the default branch. Keep one aggregate required job whose `needs:` lists every job, with a drift check that
  every job is wired into it.
- **On the default branch**, the `push` run keeps only a cheap record job, and the `pull_request` run keeps only the
  cheap checks (audits, the log-entry and work-register checks), so twenty open pull requests do not queue eighty
  matrix jobs behind a public repository's concurrent-job limit.

## The findings file's integrity rule

The findings file is the source of truth for a hold, so a damaged file must never read more permissively than the
whole file would have.

- **Find findings files by NAME only.** Discovery lists every file matching the naming pattern where the files live,
  plus every file a report stamp names, and never opens one to decide whether it is one. A filter that opens files drops
  exactly the damaged ones (a read denied, a byte-order mark from an editor) before the reader can hold them.
- **Any tear HOLDS every branch the file names**, until an operator repairs the file by hand. A tear is any content
  problem: no final newline, a line that is not JSON or not a record under the schema, bytes that are not UTF-8, a
  byte-order mark, a file with no record, a file that cannot be opened or read (gone, a directory in its place, a read
  denied), and a stamp naming a file that is missing. No verdict is read from a torn file, whatever its records say: the
  records before a tear can read CLEAN when the whole file reads FINDINGS (a FINDINGS record that lost only its
  newline, with the next record glued onto its line). The hold covers every branch the file names and every branch that
  contains a head it names; a file that names none holds the branches of the item its name binds it to.
- **Every writer refuses a torn file** before writing, naming the repair command, so nothing is ever glued onto a torn
  line. Only an operator runs the repair (it keeps a last record that only lost its newline, removes a byte-order mark
  and any other torn tail, and deletes a file left with no record); no wave, survey or reviewer does.
- **Nothing raises out of the survey or the lane.** The reader returns a torn reading (with the reason, file, line and
  byte offset) instead of an exception: an exception from one undecodable byte stops every landing.
- **One record schema**, shared by the writers and the reader: each record kind's required fields and their types.
  A writer refuses a record that fails it; the reader reads such a line as a tear; extra fields are allowed.
- **The command-line reader and the survey give one answer**: the CLI prints the same reading, torn included, and
  exits 0, so a caller reads the verdict from the reading, never from an exit code.
- **Prove it with a property test, not cases.** Take a sample findings file with several rounds and a non-ASCII
  character, cut it at every byte offset, alone and with a whole record glued after the cut, and assert that no cut
  reads more permissively than the whole: a cut inside a record reads TORN and holds; a cut at a record boundary reads
  exactly its records' verdict; the repaired bytes are accepted by every writer. Assert the strong form: "TORN or the
  whole records' verdict" passes a reader that drops a glued FINDINGS record. Add one case per discovery path (read
  denied, byte-order mark, empty file, directory, missing file) and one per schema mutation (each required field
  dropped, each given a wrong type).

*Why a property test: each case-by-case fix of a reader misses another reading (a torn line that drops every hold in
its file, a torn line that swallows a whole record so the prefix returns the CLEAN round before it, discovery that drops
a file it cannot open, a record missing a field that releases the hold); cutting at every byte offset finds them all.*

## The branch survey

A survey that gives every branch a lifecycle state (in flight, waiting for review, waiting to land, decision) reads
the review verdicts too.

- **A branch reviewed CLEAN at its tip keeps its own state, contained or not**: it is waiting to land, even when a
  successor's branch contains it.
- **A branch with no clean review at its tip that is contained in a reviewed or in-flight carrier** (one a finisher
  merged, an unfinished or unreviewed predecessor) is IN FLIGHT via that carrier: it lands through the carrier, and is
  neither a decision row nor a second review. Once the carrier lands, it reads landed and is deleted.
- **A branch waiting to land that carries another item's unanswered blocking findings** (its unlanded commits contain
  the head of a FINDINGS last verdict, or any head or name of a torn file) is IN FLIGHT, waiting on that item, until the
  findings are answered or that head is on the default branch. A finisher of the same item carries them on purpose and
  lands.

*Why: a containment rule that reads a CLEAN predecessor inside its successor as in flight holds finished work, and
reading an unreviewed predecessor as waiting for review sends a second reviewer over content its successor's review
covers.*

## Conflict-free landing files: the tree holds sources, views are rendered

Two queued pull requests that both insert at the top of one file collide, and the second bounces; the queue is only as
parallel as the files are disjoint. A landing adds or edits files that are ITS OWN; anything derived is rendered on demand.

- **The log is one file per entry**, its number stamped at enqueue so number order is landing order; the descending view
  is rendered, never committed; a CI check asserts every landing adds exactly one stamped entry (the `devlog` skill).
- **Generated indexes leave the tree** (gitignored, rendered by their script on demand); CI's audits job fails when one no
  longer renders. A view DEFINITION (a saved query) is a source and stays.
- **Shared prose** (the live-state page, a plan's status section) is edited only by its own pull request, never inside a
  fix.
- **One line-ending format, LF, enforced** (the `cross-platform` skill): a Windows gate and a Linux gate must test the same
  bytes, and a workflow script with a carriage return may be refused as containing control characters.

## Measure per landing

Record, per pull request: DONE → enqueued → merged, the bounces and their causes, and CI's wall time. Summarize changes
landed per hour and minutes and tokens per landing, and compare against the measurement taken before the change. Judge the
pipeline by that comparison, not by the absence of complaints.
