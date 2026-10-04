# The orchestrator as short units, and what Anthropic has published

*(Practice — not yet validated: everything on this page is a measurement from one campaign or a technique read from a
published source; none has been run across several campaigns.)*

## Where the tokens go

Measure it before optimizing the orchestrator. In one campaign day, from the local telemetry, the orchestrating session's
main thread was about 8 % of the estimated spend (about 480 calls, averaging about 350k tokens of context per call because
the session had grown long) and the agents about 92 % (about 6,300 calls; Opus agents about a third of that). Cutting the
orchestrator's context to about 100k would save roughly 5 % overall. The larger levers are in the agents: the model chosen
per group, turns per agent (the cost law), failed trains that waste a whole group, and re-gating.

## Short units instead of one long session

A supervisor script runs one bounded unit per fresh session (`claude -p`, one wave or one landing or one daily resume), each
ending by writing a handoff file, then starts the next. A session never gets long, and a crash loses at most one unit.

- Move everything that needs no judgment out of the model: choosing the next wave, allocating ids and codes, rendering
  specs, estimating the quota from local telemetry, generating the ledger, pruning worktrees, watching the landing script.
  Local CPU time is free; tokens are not.
- Guards the loop needs: a stop file, a single-instance lock, a circuit breaker (a few units that fail fast stop the loop),
  a budget decision from the quota estimate, and a rule that a decision only the owner can make ends the loop with a
  question instead of a guess.
- A workflow run lives inside its process and dies with it, so a unit that dispatches one stays alive until its lander has
  landed.
- To WATCH background agents without paying for it, tail their transcript files in terminal tabs: it spends no tokens and
  does not change how they run. Run agents as separate terminal processes only if a measurement shows the cost is within a
  few percent of background execution.

## Techniques Anthropic has published that bear on this

Read at the source; the first is the closest match to a compiler campaign.

- *Building a C compiler with a team of parallel Claudes* (anthropic.com/engineering/building-c-compiler): tests are the
  task ("write extremely high-quality tests"); a known-good compiler used as an oracle to bisect a stubborn failure; git-based
  task claims; harness output kept small and logged to files because of context pollution and time blindness; a progress
  file per agent; standing specialist agents for duplicate code, performance and documentation. Their own caveat: new
  features frequently broke existing functionality despite strict CI.
- *Harness design for long-running application development* (anthropic.com/engineering/harness-design-long-running-apps): a
  separate, skeptical, tool-grounded evaluator with hard thresholds found the last-mile gaps that self-evaluation missed, at
  about 20 times the cost of a solo run; every harness component encodes an assumption about what the model cannot do, so
  re-test each against the current model and remove what no longer pays.
- *Demystifying evals for AI agents* (anthropic.com/engineering/demystifying-evals-for-ai-agents): capability evals start
  low and regression evals stay near 100 %; grade the outcome, not the path; a 0 % pass rate at a large k usually means a
  broken task, not a weak agent, so after two failed attempts re-scope the item before spending a third agent.
- *How we built our multi-agent research system* (anthropic.com/engineering/multi-agent-research-system): multi-agent runs
  use about 15 times the tokens of a chat, token use explains most of the quality variance, so scale the effort to the
  difficulty of the item.
