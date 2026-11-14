## 3. One agent per rule group, with a self-contained input

Group rows by subject (a clause, or one construct's rule family). Give each agent its own input file containing
the rule rows verbatim with their ids, the definitions they cite, the code entry points already known, the
verdict vocabulary, the return schema, and the bar (see below). The agent should not rediscover any of that. In
measured campaigns, searching and re-reading took nearly half of an agent's tokens, so the input carries what is
already known. Use the `agent-fleet` skill for checkpointing, budgets and restart-safety.

**State the bar, not only the format.** Tell the agent what makes a well-formed answer worthless: a verdict
without the lines read, an absence without the searches run, or an expected value copied from another
implementation's output.

**Bind the return to a schema**, one record per rule: `rule_id`, `verdict`, `citation` (clause plus verbatim
quote, run through the checker), `derived_expectation`, `enforcement` (file:line ranges read), `paths_walked`
(every branch, including the default), `searched` (pattern and its result, including irrelevant hits),
`witness` (see §5, with the mutation it was seen to fail under), `pre_submit` (the yes/no answers to the
refuters' overturn categories, §6), and `open_questions`. A schema-bound agent must name the lines it read. Free
prose lets it skip that.
