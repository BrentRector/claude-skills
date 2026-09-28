---
name: agent-fleet-stamped-handoff
description: Writing the checkpoint/resume block of an implementer brief; agent-fleet stamps STATUS.md with the commit it describes (first line STATUS-AT <sha>, written after the checkpoint commit) and has a resuming or successor agent run the bundled references/status_delta.py to read only the commits the summary does not cover.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: The block makes STATUS.md's first line a STATUS-AT stamp naming the checkpoint commit (written after that commit), and tells a resuming or successor agent to run status_delta.py first and read the summary plus only the commits after the stamp (all commits since the base when unstamped).
---

My implementer agents each work in their own git worktree and leave a `STATUS.md` handoff summary (DONE / NEXT / GATE) next to their WIP commits. When a session limit kills one, a fresh agent resumes from that summary, and a same-file successor merges a finished predecessor's branch and orients from its summary. Last week a summary was one commit behind its branch and the successor missed that commit's work; now my briefs say "ignore STATUS.md and re-read every commit on the branch", which is slow. Write the "Checkpoint and resume" block of the implementer brief, at most 6 lines, with exact file contents and commands. Use the `agent-fleet` skill.
