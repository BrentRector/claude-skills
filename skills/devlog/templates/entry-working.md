<!-- A working-history entry: one per landing, written by the agent that did the work, in its branch.
     Save the body (without the header) as entry.md and run:
       python devlog.py new --title "Short, specific title: what changed and the finding" --body-file entry.md
     That writes devlog/pending-<slug>.md headed `## Entry pending — Title`: NO number and NO time. The enqueue step
     runs `devlog.py stamp`, which renames it NNNN-<slug>.md and completes the header as
     `## Entry N — YYYY-MM-DD HH:MM TZ — Title` from the clock. Never type the number or the time yourself.
     Write for a reader six months from now who has only this entry. Delete these comments. -->

**Context.** Why this change, and what state things were in. Quote the request or the failure that started it.

**Tried.** What was done, the alternatives considered and why they were rejected. If an earlier entry tried the
same thing, cite it (`Entry 212`) and say what is different now.

**Result.** What happened, with the numbers: tests, timings, counts, before and after. A failure is a result.

**Lesson.** What the next person or agent should know. If this overturns an earlier entry, say so here:
"Entry 212's diagnosis was wrong: …". Do not edit Entry 212.

**Next.** What follows: the open question, the follow-up, or "nothing".
