## 2. Role agent definitions

1. Copy `templates/agents/*.md` and adapt the roles. **Every** role sets `model`, `effort` and `maxTurns`: the
   quality gate (refuter) gets the highest effort, implementers and analysts get high, and the two MECHANICAL
   roles get a cheaper model and lower effort: `chore` for work that writes (filing notes, doc sweeps) and
   `locator` for READ-ONLY lookups (code sites, orientation or cluster summaries, measurements). Without a
   read-only mechanical role, lookups end up on the top-tier analyst by default.
2. **Every role that waits on gates, builds or CI** sets `experimental:` / `cacheTtl: 1h`. With the default 5-minute
   TTL, each wait longer than 5 minutes ends with the whole context written to the cache again. The 1-hour TTL
   turns those rewrites into cache reads. Roles that never wait keep the default. Measured over 208 agents: every
   wait over 5 minutes was followed by a cache read instead of a rewrite, an estimated net saving of about 44 M
   base-token units at API cache prices, while roles that never waited paid the 1-hour write premium for nothing. *(Validated 2026-09-28.)*
3. **Read-only roles carry `readonly_guard.py` in their OWN frontmatter `hooks:`**, with matcher
   `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Don't put it in project settings keyed on the hook input's
   `agent_type`: when that field is missing, such a hook can't tell the role from the main session, and it allows
   the write. The guard blocks file-tool writes, repo-changing git and shell writes (`>`, `>>`, `tee`, `Out-File`,
   `Set-Content`) inside any git tree, resolves Git Bash paths (`/e/repo`), and lets scratch writes through. It
   cannot see a write made inside a script; say so in your report. *(Practice — not yet validated: no recorded production block yet.)*
4. Select roles by name: `agentType: '<role>'` in workflow scripts, and `subagent_type: "<role>"` with the Agent
   tool. Never set model or effort per call: a per-call `model` OVERRIDES the role's frontmatter. One campaign's
   "pass the top model on every agent" rule silently ran its cheaper chore role on the top tier. If you keep a
   brief or workflow checker, make it fail a mechanical role's call that carries a `model`. *(Practice — not yet validated: the cost of the override was never measured.)*
5. **Restart, then prove each role.** The agent registry loads at session start, so a new or edited definition
   does nothing until a restart. Then send one short smoke agent per role. Each one reports its model and effort.
   Each read-only role tries a Write inside the repo, which must be BLOCKED, and a Write in scratch, which must
   pass. Record the proof with `python .claude/hooks/readiness_check.py --stamp roles-smoke`. The readiness check
   prints a TODO line until the proof matches the current files. *(Practice — not yet validated: not yet a standing practice with a recorded catch.)*
6. **Roll back on quality.** After lowering a role's model or effort, watch its quality metric: the refuters'
   overturn rate on its output, rework, or red CI. If the metric drops, move the role back up. Telemetry (§4)
   supplies the cost side. *(Practice — not yet validated: no before/after overturn rate per role yet.)*
