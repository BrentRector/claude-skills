# The orchestrator as short units, run by a supervisor

For a long or unattended campaign, a supervisor script runs the orchestrator as a series of short `claude -p` units.
A crash then loses at most one unit, and no session grows long. Read this before writing or running that supervisor.

## Where the tokens go

Measure it before optimizing the orchestrator. In campaigns measured from local telemetry, the orchestrating
session's main thread was a small share of the spend and the agents it started were most of it, so cutting the
orchestrator's context saves little. The larger levers are in the agents: the model tier chosen per group
([`role-agents.md`](../../automating-agent-guardrails/references/role-agents.md#model-tiers-and-effort)), turns per agent
(the cost law), failed landings that waste a whole group, and re-gating.

## Short units instead of one long session

A supervisor script runs one bounded unit per fresh session (`claude -p`, one wave or one enqueue or one resume), each
ending by writing a handoff file, then starts the next.

- Move everything that needs no judgment out of the model: choosing the next wave, allocating ids and codes, rendering
  specs, estimating the quota from local telemetry, generating the status page, pruning worktrees, running the enqueue
  step and reading the merge queue. Local CPU time is free; tokens are not.
- **The landing unit is an ENQUEUE unit**: for every DONE branch waiting to land, in priority order, run the project's
  enqueue script; dispatch a finisher for each merge conflict or queue bounce; render the status view; hand off. Its
  model turns are the finisher dispatches and the handoff (the `merge-queue-landing` skill).
- Choose the next unit with a deterministic script from the last handoff and the state on disk (dirty tree, unpushed commits,
  an unlanded branch with a newer commit, a stale quota reading), never from the model's mood.
- Guards the loop needs: a stop file, a single-instance lock, a circuit breaker (a few units that fail stop the loop), a
  budget decision from the quota estimate, and a rule that a decision only the owner can make ends the loop with a question
  instead of a guess.
- To WATCH background agents without paying for it, tail their transcript files in terminal tabs: it spends no tokens and
  does not change how they run. Run agents as separate terminal processes only if a measurement shows the cost is within a
  few percent of background execution.

## Supervisor rules

Test the supervisor against a fake `claude` that emits canned stream-json, and expect the real CLI to disagree: each
rule below is CLI behaviour a fake did not show.

1. **The supervisor owns each unit's lifetime.** A one-shot `claude -p` terminates background tasks 600 seconds after
   its model ends a turn; its stderr says `Background tasks still running after 600s; terminating. Set
   CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 to wait indefinitely.` A prompt rule telling the model to keep waiting
   depends on the model obeying, so it is not the design. Start the unit with `--input-format stream-json`, send the
   prompt as the first `{"type":"user","message":{"role":"user","content":...}}` line, and keep stdin OPEN: an open
   stdin never enters the exit wait, and the session is woken by the background task's completion notification.
   Close stdin only when the unit is over: the model has ended a turn (a `result` event arrived), the last
   `system/background_tasks_changed` event lists no running task, and the stream has been quiet for a short interval
   (a finishing task's completion event arrives just after its list empties, so closing at the first idle instant can
   cut a woken turn off). Keep the prompt's advice to wait with foreground calls as a second line of defence. The
   ceiling and the variable are CLI behaviour: after a CLI upgrade, re-check them by running a unit that ends its turn
   with a background task running and reading its stderr.
2. **Save each unit's stderr beside its stream log, and read it first.** The stream's tail (`end_turn`, tasks
   `killed`) can suggest the wrong mechanism; stderr names the real one.
3. **Write handoffs in three layers**, ordered by how little they trust the model: (a) a checkpoint file the
   SUPERVISOR writes at unit start, every few minutes, whenever the set of background tasks changes and at the end
   (stream counters, each worktree's head, commits ahead of the base, uncommitted file count, the headline of its
   status file); (b) one line the unit's model appends per milestone (a decision and its reason, what landed), for
   what the supervisor cannot see; (c) a handoff the supervisor SYNTHESIZES from the checkpoint, the last milestones
   and the worktrees as they are now when a unit ends without a valid one (outcome split, next unit resume, flagged
   synthesized, and still counted as a failure by the breaker). A checkpoint that survives into the next supervisor
   start means the supervisor itself died mid-unit, so turn it into the missing handoff first.
4. **STOP is a wind-down, not a kill.** While a unit runs, the supervisor creates the unit's own stop file and the
   fleet's graceful-stop file, so every implementer checkpoint-commits and returns split and the unit hands off for a
   resume; the supervisor waits, and only then ends the loop; a kill comes only after a grace period. Clear the fleet's
   stop file at the start of the next unit, or it stops that fleet at its first step. Give the owner one command that
   creates, reports and clears the stop.
5. **Judge a unit by its handoff, not its duration.** A short unit that wrote a valid done handoff (a quota read, say)
   is not a failure; count a unit as failed only when it did not hand off done.
6. **Every standing constraint and budget decision is a supervisor argument**, substituted into each unit's prompt
   and planning command, switched on and off with the supervisor's own command, and pinned by a test that the
   rendered prompt carries it. A steer lasts one unit and a handoff sentence is a summary, so neither carries a rule:
   a drain ("finish started work only") passed on in handoffs is dropped within a few units, and a unit's own planner
   call defaults any argument it was not given.
7. **Plan from the disk, not from remembered reports.** State that survives a crash is branches and worktrees; derive
   the plan from them, and make a finisher's spec name the branch it must resume, or a resume plans finishers from
   the base branch and drops the work in progress.
8. **Check a unit's capabilities instead of assuming the attended session's.** A headless session can lack a tool the
   attended one has (an artifact-publishing tool, for one). Split the work where the capability is: the unit renders
   the page, a small script compares its stamp with the last published one, the supervisor announces an owed publish
   after every unit, and the attended session publishes and marks it.
9. **Read the child's stdout before writing to its stdin.** The CLI writes a large `init` event (tools, MCP servers,
   slash commands) to stdout BEFORE it reads stdin. Once that fills the stdout pipe the child blocks until you read; a
   synchronous write of a prompt larger than the stdin pipe buffer (about 4 KB on Windows) blocks until the child
   reads, and each waits for the other with a 0-byte log. It appears only when a prompt outgrows the buffer, so a green
   history proves nothing about it. Write the prompt as a task and start the read loop at once, and add a startup
   watchdog: a unit that has emitted NO event after a number of loop ticks is killed and its handoff synthesized.
   Count ticks (one per second waited), not wall time, so a suspended machine cannot trip it. Test it with a fake CLI
   that writes several hundred KB before reading stdin, run under a time bound so a regression fails instead of
   hanging the suite; a fake that merely stays quiet must emit NOTHING, not even `init`, or it disarms the watchdog it
   is meant to test.
10. **One orchestrator per branch.** Record the dispatching orchestrator with each group in the dispatch ledger and
    show it in the branch survey; a unit reviews, finishes or plans only its own orchestrator's branches and the ones
    explicitly handed to it; the landing step still lands any branch its owner's review approved. Otherwise a loop
    beside an attended session reviews and finishes that session's in-flight branch, on a tier its owner did not
    choose.

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
