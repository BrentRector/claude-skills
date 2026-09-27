---
name: agent-fleet-file-clusters
description: Assigning open defects to parallel implementer slots; agent-fleet says to COMPUTE the groups by clustering defects on the source file their code sites name (bundled references/fix_clusters.py), rank clusters by summed harm, and give each slot one whole cluster, instead of hand-picking a lead item plus keyword siblings.
tags: [agent-fleet, skill]
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Glob]
expected_outcome: The answer clusters the defects by the source file their code sites name (a primary file per note, a small size cap such as 5), ranks clusters by summed harm, gives each slot one whole cluster (one subsystem per slot), and names the bundled fix_clusters.py with its --notes/--src arguments.
---

I have 214 open defect notes in `docs/issues/*.md`. Each has front matter (`id`, `status: open`, `wrong_answer: true|false`, `crashes: true|false`) and prose naming code sites in our C# sources under `src/` (paths, `Type.Member`, type names). I'm about to dispatch 6 parallel implementer agents. How should I decide which defects each implementer gets? Give me the rule and the exact command to produce the assignment, in at most 6 lines. Use the `agent-fleet` skill.
