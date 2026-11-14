## 2. Role agent definitions

### Model tiers and effort

This is the one definition of model tiers and effort for every skill and agent in this plugin. Other files name a
tier, never a model, and link here. Concrete aliases and effort values live only in the `model:` and `effort:`
front matter of the role templates (`templates/agents/*.md`) and of the plugin's own agents (`agents/*.md`), because
a model name written in prose goes stale at the next release and nothing re-reads it.

| Tier | What it is for | Starting effort |
|---|---|---|
| **orchestrator tier** | The most capable model. It plans, decides, judges the hard cases, briefs the workers and reads their reports. It is usually the session's own model, not a role. | the session's setting |
| **worker tier** | Everyday judgment: implementing, finishing a branch, analysing, reviewing, refuting. | `medium` |
| **mechanical tier** | The cheapest model. It files, locates, formats and measures: work that needs no judgment about correctness or design, and whose output a script, a diff or a later judge checks. | `low` |

**Effort is the second lever**, set per role together with its tier. A role starts at its tier's level. Raise a
level only where a measured sweep on the project's own tasks shows that the role's quality metric gains at the
higher level. Lower it where the metric holds. Effort, not prose, controls how much a current model thinks, so a
role's prompt never tells it to think more or less.

**Why subagent models matter.** Subagents can be most of a session's cost. An agent type with no `model`, or with
`model: inherit`, runs on the default subagent model when one is configured (`CLAUDE_CODE_SUBAGENT_MODEL`), and
otherwise on the session's model. In an orchestrator-tier session, every unpinned worker and lookup therefore runs on
the orchestrator tier, at the session's effort.

**Re-make the choice when a model ships**, when an alias starts to resolve to a different model, or when a model's
default effort changes:

1. Fix a sample for each role from the project's own closed work, with known outcomes: about ten lookups with their
   right code sites, verdicts the refuters upheld or overturned, landed fixes.
2. Run each sample at the role's current setting and at the candidates: one effort step up and one down on the same
   tier, a cheaper tier at a higher effort, and a more capable tier at a lower effort. Either of the last two can be
   the cheaper way to hold quality.
3. For each run, record the role's quality metric and its tokens or cost per closed unit. Start with the roles that
   run most often (locator, implementer) and the quality gate (refuter).
4. Choose the cheapest setting that holds the quality metric within run-to-run noise. Write it in the role's front
   matter, and record the measurement beside the role's reason below.

**The roles the templates ship:**

| Role | Tier, effort | Why | The metric that would move it |
|---|---|---|---|
| implementer | worker, `medium` | Judgment on code. The refuters and the branch review check its output, so a slip is caught before it lands. | The reviewers' confirmed findings and the refuters' overturn rate on its fixes, red merge-queue runs. |
| finisher | worker, `medium` | Judgment on one stopped branch: a conflict, a bounce, a finding. Its re-gate and the merge queue check it. | Branches it returns that bounce again. |
| analyst | worker, `medium` | Verdicts with evidence. The refuters check the closing verdicts. | The refuters' overturn rate on its verdicts. |
| refuter | worker, `medium` | The quality gate. It stays at the worker tier's level until a sweep shows a gain at a higher one. It is the first role to sweep. | The share of its verdicts that a second refuter or a later fact overturns. |
| locator | mechanical, `low` | Read-only lookups that need recall, not judgment. The implementer re-reads every site it names, so a wrong lookup is cheap to catch. Without this role, lookups run on a judgment role. | Implementers sent to the wrong file. |
| chore | mechanical, `low` | Fully specified writes: filing notes from a structured report, link checks, formatting sweeps. Any step that needs judgment returns `NEEDS-ESCALATION`, and every write it makes passes a diff and the gate. | Rework of its output. |

1. Copy `templates/agents/*.md` and adapt the roles. **Every** role sets `model`, `effort` and `maxTurns`. The turn
   cap exists because cost grows with turns, and a fresh agent started from a checkpoint is cheaper than a long
   transcript.
2. **Every role that waits on gates, builds or CI** sets `experimental:` / `cacheTtl: 1h`. With the default 5-minute
   TTL, each wait longer than 5 minutes ends with the whole context written to the cache again. The 1-hour TTL
   turns those rewrites into cache reads. Roles that never wait keep the default. Measured over 208 agents: every
   wait over 5 minutes was followed by a cache read instead of a rewrite, an estimated net saving of about 44 M
   base-token units at API cache prices, while roles that never waited paid the 1-hour write premium for nothing.
   A `subagentPromptCacheTtl` setting or environment variable takes precedence over the role's value, and a
   subscription in overage ignores `1h`.
3. **Read-only roles carry `readonly_guard.py` in their OWN frontmatter `hooks:`**, with matcher
   `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Don't put it in project settings keyed on the hook input's
   `agent_type`: when that field is missing, such a hook can't tell the role from the main session, and it allows
   the write. The definition must live in the project's `.claude/agents/`: Claude Code ignores `hooks`,
   `permissionMode` and `mcpServers` in an agent file that a plugin ships. The guard blocks file-tool writes,
   repo-changing git and shell writes (`>`, `>>`, `tee`, `Out-File`, `Set-Content`) inside any git tree, resolves Git
   Bash paths (`/e/repo`), and lets scratch writes through. It cannot see a write made inside a script; say so in
   your report.
4. Select roles by name: `agentType: '<role>'` in workflow scripts, and `subagent_type: "<role>"` with the Agent
   tool. **Pass no `model` or `effort` on a call to a role whose definition names them**: a per-call `model`
   overrides the definition for that call, so the role silently leaves its tier. The one exception is a deliberate
   per-item escalation, one item its tier has failed twice, dispatched on a higher tier and recorded as such
   (`agent-fleet` §11; an orchestrator-tier escalation needs the quota owner's approval where a person owns it). An agent type whose definition
   names no model (the general-purpose agent, or `model: inherit`) runs on the model described above unless the
   call passes one; for those the caller chooses, and chooses the cheapest tier that does the job. If you keep a
   brief or workflow checker, make it fail a call that passes a `model` to a role whose definition names one.
5. **Restart, then prove each role.** The agent registry loads at session start, so a new or edited definition
   does nothing until a restart. Then send one short smoke agent per role. Each one reports its model and effort.
   Each read-only role tries a Write inside the repo, which must be BLOCKED, and a Write in scratch, which must
   pass. Record the proof with `python .claude/hooks/readiness_check.py --stamp roles-smoke`. The readiness check
   prints a TODO line until the proof matches the current files.
6. **Roll back on quality.** After lowering a role's model or effort, watch the metric in its row above. If the
   metric drops, move the role back up. Telemetry (§4) supplies the cost side.
