---
type: llm
focus: last_message
---

The task: a brief for an agent that files leads from implementer reports as work notes; leads often carry a quoted clause from the spec.

PASS if the procedure tells the agent to check each quoted spec clause against the spec itself (re-read or verify the quote at its source) rather than copying it into the note as given.

FAIL if quoted clauses are copied into the note as the report gives them, or if the procedure says nothing about verifying them.
