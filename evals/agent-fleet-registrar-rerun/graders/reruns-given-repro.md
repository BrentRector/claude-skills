---
type: llm
focus: last_message
---

The task: a brief for an agent that files ~40 leads from implementer reports as work notes; each lead has a repro command, a file:line code site and often a quoted spec clause.

PASS if the procedure has the agent RUN each lead's provided repro on its own current build before filing it and record what it observed (reproduces / already fixed / different) in the note, and does NOT require writing a new probe for leads that already have a runnable repro (a fresh probe only for a lead that lacks one is fine).

FAIL if leads are filed as reported without running their repros (copying the report's measurement forward), if the repro is run only for a sample of leads, or if the agent must write a fresh probe or re-investigate from scratch for every lead.
