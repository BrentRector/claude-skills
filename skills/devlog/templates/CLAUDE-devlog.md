## Development log

<!-- Paste into the project's CLAUDE.md. Replace DEVLOG.md with your log's path (a file, or a directory of
     NNNN-YYYY-MM-DD-slug.md entries). Keep the reasons: an agent follows a rule it understands. -->

**`DEVLOG.md` is this project's only history, and you write it.** Every other document describes the CURRENT state;
what happened, what was tried and why lives here and nowhere else.

1. **Every commit carries its entry, in the same commit.** Add it with
   `python <skills>/devlog/references/devlog.py new --title "..." --body-file entry.md` (number = newest + 1, time
   from the clock, the file's line endings kept). *Why: an entry written at the end of the session loses the
   reasoning of the moment, and a batch of changes gets one vague entry instead of one per change.*
2. **The time comes from the clock** (`devlog.py` stamps it; by hand, `date "+%Y-%m-%d %H:%M %Z"`). Never write a
   time you estimated. *Why: estimated stamps were caught wrong twice in one day, and a wrong stamp misorders the
   history that later readers reconstruct from it.*
3. **A correction is a NEW entry** that names the entry it overturns. Never rewrite, delete or renumber an old entry.
   *Why: the log records what was believed and when; a rewritten entry hides the mistake the next reader needs to
   see, and breaks the commits and documents that cite it.*
4. **Keep failures, dead ends and overturned verdicts.** *Why: "we tried X and it failed because Y" is the entry
   that saves the most time later, and the one most often left out.*
5. **Each entry says:** the context, what was tried and why (with the alternatives rejected), the result with its
   numbers, the lesson, and what comes next.
6. **Newest entry first**, directly under the ordering note. Numbers are unique; early entries that predate a rule
   are left as they are.

**Using it.**
- Do NOT read the log at session start. Read the current-state document; search the log only when a question
  needs its history.
- Before retrying an approach, search for it: `python <skills>/devlog/references/devlog.py search -i "<words>"`. If
  it was tried, say what is different this time.
- When the log is long, turn it into learnings in three stages. The log records everything. Consolidation
  (`templates/consolidate-brief.md`) produces CANDIDATE learnings in `LEARNINGS-CANDIDATES.md`. Validation
  (`templates/validate-brief.md`, a fresh adversarial agent per batch) rules each candidate VETTED, UNPROVEN or
  REFUTED. **Only VETTED learnings enter `LEARNINGS.md`, and only vetted learnings are encoded into skills or
  rules.** VETTED requires all four: the root cause confirmed, the evidence re-checked against primary sources, no
  later entry contradicting it, and the fix used and shown useful. Refuted candidates stay in the record, marked
  refuted, never silently dropped. *Why: a log records hypotheses as well as conclusions, and some are later
  refuted: in one project a published explanation of an observed silence was refuted the same day. A learnings file
  compiled straight from the log inherits those errors, and a skill that encodes them spreads them.*

A commit whose staged changes carry no log entry asks for confirmation (`devlog_guard.py`). Confirm only a
deliberate exception, such as rewording the last commit's message.
