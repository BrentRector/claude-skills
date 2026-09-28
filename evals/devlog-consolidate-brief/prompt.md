---
name: devlog-consolidate-brief
description: Briefing an agent to consolidate a long working devlog into a learnings document; devlog's consolidation brief asks for problem / root cause / fix / evidence / when per learning, keeps overturned findings with the correction labeled, and closes with an open-problems list and a not-yet-acted-on list.
tags: [devlog, skill]
runs: 3
max_turns: 6
timeout_seconds: 240
allowed_tools: [Skill, Read]
expected_outcome: The brief keeps reversals and overturned findings (labeled as corrections), and closes the document with an open-problems list and a list of lessons not yet acted on.
---

Our working devlog has 1,750 entries from six months of agent work. I want to dispatch one agent to turn it into a LEARNINGS.md that the team and future agents can use instead of reading the whole log. Write the agent's brief, at most 15 lines.
