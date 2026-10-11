## Development log

<!-- Paste into the project's CLAUDE.md. Replace devlog/ with your entry directory. Keep the reasons: an agent
     follows a rule it understands. -->

**The `devlog/` directory is this project's only history, and you write it.** Every other document describes the
CURRENT state; what happened, what was tried and why lives here and nowhere else. One file per entry; the newest-first
document is a VIEW (`devlog.py render`), never committed.

1. **Every landing carries exactly one entry, as its own file, written in the branch.** Write it with
   `python <skills>/devlog/references/devlog.py new --title "..." --body-file entry.md`, which creates
   `devlog/pending-<slug>.md` with no number. Checkpoint commits carry none. *Why: an entry written at the end of the
   session loses the reasoning of the moment, and a batch of changes gets one vague entry instead of one per change.*
2. **The number and the time are stamped at enqueue, never by you.** The enqueue step runs `devlog.py stamp --base
   <default branch>` after the final rebase (next free number, time from the clock), then `devlog.py check --base
   <default branch> --one`; CI runs the check again on the pull request and on the merge group. By hand, the time is
   `date "+%Y-%m-%d %H:%M %Z"`, never an estimate. *Why: implementers in parallel cannot know the landing order, so a
   number they pick collides; estimated stamps were caught wrong twice in one day.*
3. **A correction is a NEW entry** that names the entry it overturns. Never rewrite, delete or renumber an old entry.
   *Why: the log records what was believed and when; a rewritten entry hides the mistake the next reader needs to
   see, and breaks the commits and documents that cite it.*
4. **Keep failures, dead ends and overturned verdicts.** *Why: "we tried X and it failed because Y" is the entry
   that saves the most time later, and the one most often left out.*
5. **Each entry says:** the context, what was tried and why (with the alternatives rejected), the result with its
   numbers, the lesson, and what comes next.
6. **Numbers are unique and follow landing order**; a bounced pull request keeps its number, and gaps are fine. Early
   entries that predate a rule are left as they are. Entry files are LF.

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

Opening or queueing a pull request whose branch adds no stamped entry asks for confirmation (`devlog_guard.py`).
Confirm only a deliberate exception; CI's check still decides.
