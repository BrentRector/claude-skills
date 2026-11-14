# Refuters, cost measurement and routing

The full text of agent-fleet sections 10 and 11. Read it before dispatching a refuter on a closing verdict, and before choosing a lane or a model for a role.

## 10. Adversarial refuters on closing verdicts

Any verdict that **closes** something permanently (an item fixed, a requirement met, a finding dismissed) goes
through a second, independent agent told to **overturn** it, and that agent sees only the claim and the evidence.
Run refuters in small chunks (~4 wide) that are checkpointed per item.
*Why: the first agent's framing is contagious. Only an agent looking for a counter-example finds the
well-formed-but-wrong result.* Refuters check the **substance** of the evidence (for example, was the expected
value derived from the authority), not its format.
- **Keep verdicts per claim AND per piece of evidence.** When one piece of evidence (a test, a golden) supports several
  claims, a refuter's overturn of one claim must not withhold that evidence from the sibling claims it upheld, and
  evidence the refuter never judged must never be recorded because its claim was upheld on something else. Key the
  integration on (claim, evidence); withhold evidence from EVERY claim only when the refuter says the evidence itself is
  invalid (for example, the test input is non-conforming). *Why: pooling overturns by claim silently drops valid
  evidence and records unjudged evidence.*

## 11. Measure cost per unit and route to the cheapest lane

- **Measure tokens per closed unit for each lane** (items closed per agent, cache-read per item) from the
  transcripts, and re-measure at each milestone. *Why: across lanes, cost per unit can differ by ~10×.*
- **Route each item to the cheapest lane that moves the metric you actually report.** For example, writing a
  witness test for already-correct behavior beats re-running a full review fleet. *Why: a large review fleet
  can burn billions of tokens for single-digit movement.*
- **The tier and the effort follow the ROLE, set in the role definition**, in the three tiers
  [`role-agents.md`](../../automating-agent-guardrails/references/role-agents.md) defines. Judgment roles
  (implementer, finisher, analyst, refuter, reviewer) run the **worker tier** at effort `medium`, raised only for a
  role where a measurement shows a gain. Mechanical roles run the **mechanical tier** at `low`: chores that write
  (filing notes, doc sweeps) and READ-ONLY lookups (code sites, orientation and cluster summaries, measurements). A
  mechanical agent that hits a judgment call returns `NEEDS-ESCALATION` for that item. The **orchestrator tier**
  plans and judges the hard cases. A per-call `model` overrides the role's, so a role whose definition names a
  model gets one per call only as a per-item choice (`rolling-wave.js`'s per-group `model`, sized to that group's
  work), and a blanket per-call model (its `args.model`) only for roles that inherit (`model: inherit`). *Why: a
  per-call model passed to every agent runs the mechanical role on the expensive tier, and a lookup pass that
  judges nothing costs what a judgment pass costs.*
- **An orchestrator-tier dispatch is an exception, never a default, unless its quota is truly separate.** Read the
  plan's terms, not the usage page's labels. On a plan where that model "draws from your plan's regular weekly usage
  limits" and uses them faster, with its own row only a CEILING on its share, every unit of its work costs more of
  the same pool. Use it only as a per-item escalation, for one item the worker tier has failed twice.
  **When a person owns the quota, each orchestrator-tier dispatch needs their explicit approval**: name the task,
  why the worker tier is not enough and what it will draw, and wait for a yes for THAT dispatch; one approval never
  carries to the next. *Why: the weekly pool is shared, possibly with other projects of the same owner, so only the
  owner can weigh one dispatch against the rest of the week.*
- **Precompute discovery.** If most of a fleet's turns are spent searching, build a dossier once and hand it to
  every agent.
- **Self-review before a large review fleet.** *Why: a large share of what the fleet finds are defects that the
  same wave introduced.* The form: each implementer's self-review of its own diff, plus a read-only reviewer's pass
  over the whole branch when it is DONE (the `merge-queue-landing` skill).
