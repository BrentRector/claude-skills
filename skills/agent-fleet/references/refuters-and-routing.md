# Refuters, cost measurement and routing

The full text of agent-fleet sections 10 and 11. Read it before dispatching a refuter on a closing verdict, and before choosing a lane or a model for a role.

## 10. Adversarial refuters on closing verdicts

Any verdict that **closes** something permanently (an item fixed, a requirement met, a finding dismissed) goes
through a second, independent agent told to **overturn** it, and that agent sees only the claim and the evidence.
Run refuters in small chunks (~4 wide) that are checkpointed per item.
*Why: the first agent's framing is contagious. Only an agent looking for a counter-example finds the
well-formed-but-wrong result.* Refuters check the **substance** of the evidence (for example, was the expected
value derived from the authority), not its format. *(Validated 2026-09-28.)*
- **Keep verdicts per claim AND per piece of evidence.** When one piece of evidence (a test, a golden) supports several
  claims, a refuter's overturn of one claim must not withhold that evidence from the sibling claims it upheld, and
  evidence the refuter never judged must never be recorded because its claim was upheld on something else. Key the
  integration on (claim, evidence); withhold evidence from EVERY claim only when the refuter says the evidence itself is
  invalid (for example, the test input is non-conforming). *Why: pooling overturns by claim silently dropped valid
  evidence and recorded unjudged evidence, and each lander had to hand-check every row.* *(Practice — not yet validated: not yet exercised on later batches.)*

## 11. Measure cost per unit and route to the cheapest lane

- **Measure tokens per closed unit for each lane** (items closed per agent, cache-read per item) from the
  transcripts, and re-measure at each milestone. *Why: across lanes, cost per unit can differ by ~10×.* *(Practice — not yet validated: tokens per closed item are not yet measured the same way for each lane.)*
- **Route each item to the cheapest lane that moves the metric you actually report.** For example, writing a
  witness test for already-correct behavior beats re-running a full review fleet. *Why: a large review fleet
  can burn billions of tokens for single-digit movement.* *(Practice — not yet validated: routing by that figure was not shown to move the metric faster.)*
- **The model follows the ROLE, set in the role definition, never per call.** Judgment roles (implementer,
  lander, analyst, refuter, reviewer) run the top everyday tier. Mechanical roles run a cheaper tier: chores
  that write (filing notes, doc sweeps) and READ-ONLY lookups (code sites, orientation and cluster summaries,
  measurements). A mechanical agent that hits a judgment call returns `NEEDS-ESCALATION` for that item.
  *Why: a per-call `model` overrides the role's own, so "pass the top model on every agent" silently ran the
  cheap chore role on the top tier, and a 30-lookup code-site pass that judged nothing ran on the top-tier
  analyst.* *(Practice — not yet validated: the cost of the override was never measured.)*
- **A premium model is an exception, never a default, unless its quota is truly separate.** Read the plan's
  terms, not the usage page's labels. On a plan where a premium model "draws from your plan's regular weekly
  usage limits" and uses them faster, with its own row only a CEILING on its share, every unit of premium work
  costs more of the same pool. Use it only as a per-item escalation, for one item the everyday tier has failed
  twice. *Why: a "separate weekly limit" label read as free capacity would have moved refuters onto a model
  that drains the shared weekly quota faster for similar results.* *(Practice — not yet validated: the premium model's draw per unit was never measured.)*
- **Precompute discovery.** If most of a fleet's turns are spent searching, build a dossier once and hand it to
  every agent. *(Practice — not yet validated: no like-for-like cost before and after.)*
- **Self-review before a large review fleet.** *Why: a large share of what the fleet finds are defects that the
  same wave introduced.* The form that lasted is each implementer's self-review of its own diff, plus the
  lander's review of the merged batch. *(Validated 2026-09-28.)*
