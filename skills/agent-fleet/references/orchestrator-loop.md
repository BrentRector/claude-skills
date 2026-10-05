# The orchestrator as short units, run by a supervisor

*(Practice — validated in live runs of one campaign: a quota-meter unit, a resume unit and a 2.5-hour wave unit ran for
real, and every defect listed below was found by those runs and fixed. Nothing here has been run across several
campaigns, and the measurements are from one.)*

## Where the tokens go

Measure it before optimizing the orchestrator. In one campaign day, from the local telemetry, the orchestrating session's
main thread was about 8 % of the estimated spend (about 480 calls, averaging about 350k tokens of context per call because
the session had grown long) and the agents about 92 % (about 6,300 calls; Opus agents about a third of that). Cutting the
orchestrator's context to about 100k would save roughly 5 % overall. The larger levers are in the agents: the model chosen
per group, turns per agent (the cost law), failed trains that waste a whole group, and re-gating.

## Short units instead of one long session

A supervisor script runs one bounded unit per fresh session (`claude -p`, one wave or one landing or one resume), each
ending by writing a handoff file, then starts the next. A session never gets long, and a crash loses at most one unit.

- Move everything that needs no judgment out of the model: choosing the next wave, allocating ids and codes, rendering
  specs, estimating the quota from local telemetry, generating the status page, pruning worktrees, watching the landing
  script. Local CPU time is free; tokens are not.
- Choose the next unit with a deterministic script from the last handoff and the state on disk (dirty tree, unpushed commits,
  an unlanded branch with a newer commit, a stale quota reading), never from the model's mood.
- Guards the loop needs: a stop file, a single-instance lock, a circuit breaker (a few units that fail stop the loop), a
  budget decision from the quota estimate, and a rule that a decision only the owner can make ends the loop with a question
  instead of a guess.
- To WATCH background agents without paying for it, tail their transcript files in terminal tabs: it spends no tokens and
  does not change how they run. Run agents as separate terminal processes only if a measurement shows the cost is within a
  few percent of background execution.

## What the first live runs taught

Each item is a defect the real runs exposed that a fake-CLI self-test could not, with its cause and the fix. Test the
supervisor against a fake `claude` that emits canned stream-json, but expect the real CLI to disagree.

1. **A one-shot `claude -p` terminates background tasks 600 seconds after its model ends a turn.** A unit launched a
   workflow of eight agents, wrote "waiting for the workflow", ended its turn, and the process killed the workflow at 600 s
   (its stderr: `Background tasks still running after 600s; terminating. Set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 to
   wait indefinitely.`). A prompt rule telling the model to keep waiting is not a design; it depends on the model obeying.
   **Make the supervisor own the session's lifetime.** Start the unit with `--input-format stream-json`, send the prompt as
   the first `{"type":"user","message":{"role":"user","content":...}}` line, and keep stdin OPEN. An open stdin never enters
   the exit wait: probed with the ceiling set to 5 s, a session whose model had ended a turn was still alive 30 s later and
   was woken by the background task's completion notification. The supervisor then closes stdin only when the unit is over:
   the model has ended a turn (a `result` event arrived), the last `system/background_tasks_changed` event lists no running
   task, and the stream has been quiet for a short interval (a finishing task's completion event arrives just after its list
   empties, so closing at the first idle instant can cut a woken turn off). Keep the prompt's advice to wait with foreground
   calls as a second line of defence, never the only one.
2. **Read the unit's stderr before its stream.** The stream's tail (`end_turn`, tasks `killed`) read like "the model ended
   its turn, so the process exited", which was the wrong mechanism; the stderr file named the real one. The first resume
   unit found it. Save stderr beside the stream log, always.
3. **Frequent handoffs.** A handoff written only when a unit ends is lost with the unit. Three layers, ordered by how little
   they trust the model: (a) a checkpoint file the SUPERVISOR writes at unit start, every few minutes, whenever the set of
   background tasks changes and at the end (stream counters, each worktree's head, commits ahead of the base, uncommitted
   file count, the headline of its status file); (b) one line the unit's model appends per milestone (a decision and its
   reason, what landed), for what the supervisor cannot see; (c) a handoff the supervisor SYNTHESIZES from the checkpoint,
   the last milestones and the worktrees as they are now when a unit ends without a valid one (outcome split, next unit
   resume, flagged synthesized, and still counted as a failure by the breaker). A checkpoint that survives into the next
   supervisor start means the supervisor itself died mid-unit, so turn it into the missing handoff first.
4. **STOP is a wind-down, not a kill.** A stop file honoured only between units leaves a multi-hour unit running. While a
   unit runs, the supervisor creates the unit's own stop file and the fleet's graceful-stop file, so every implementer
   checkpoint-commits and returns split and the unit hands off for a resume, waits, and only then ends the loop; a kill comes
   only after a grace period. Clear the fleet's stop file at the start of the next unit, or it stops that fleet at its first
   step. Give the owner one command that creates, reports and clears the stop.
5. **A fast unit that wrote a valid done handoff is not a failure.** A "fewer than N seconds is a crash" rule scored a
   legitimate 40-second quota-read unit as a failure, and three of them would have tripped the breaker. Treat a short unit as
   a failure only when it did not hand off done.
6. **Pass the budget decision to the unit.** The supervisor's gate had the owner's borrowed-day allowance, but the unit's own
   planner call defaulted it to zero and planned an empty wave. Anything a decision depends on that is an argument of the
   supervisor must be substituted into the unit's prompt.
7. **Plan from the disk, not from remembered reports.** After a killed wave the planner scheduled finishers for the
   half-done work from the base branch, and dropped the work-in-progress branches that carried it. State that survives a
   crash is branches and worktrees; derive the plan from them, and make a finisher's spec name the branch it must resume.
8. **A headless session may lack tools the attended one has.** It had no artifact-publishing tool (asked, it answers no), so
   the owner's status page could not be published by a unit. Split the work where the capability is: the unit renders the
   page, a small script compares the page's stamp with the last published one, the supervisor announces an owed publish after
   every unit, and the attended session publishes and marks it.
9. **Never write to a child's stdin synchronously before you are reading its stdout.** The CLI writes a large `init` event
   (tools, MCP servers, slash commands) to stdout BEFORE it reads stdin. Once that fills the stdout pipe the child blocks until
   you read; a synchronous write of a prompt larger than the stdin pipe buffer (about 4 KB on Windows) blocks until the child
   reads. Each waits for the other: a unit sat two hours with a 0-byte log and a child at under a second of CPU. It appeared only
   when a unit prompt grew past the buffer (a 3 KB prompt always worked), so a green history proves nothing about it. Write the
   prompt as a task and start the read loop at once, and add a startup watchdog: a unit that has emitted NO event after a number
   of loop ticks is killed and its handoff synthesized. Count ticks (one per second waited), not wall time, so a suspended
   machine cannot trip it. Test it with a fake CLI that writes several hundred KB before reading stdin, run under a time bound so
   a regression fails instead of hanging the suite; a fake that merely stays quiet must emit NOTHING, not even `init`, or it
   disarms the watchdog it is meant to test.
10. **Recovery was measured, not assumed.** After the killed wave, a resume unit (141 s, about one dollar) read the six
   worktrees, committed the uncommitted work in four of them, wrote a status file in each, and named the next unit; nothing was
   lost. The next wave then ran 2.5 hours, well past the old 600-second ceiling, and landed all eight groups in two trains with
   none dropped.

## Measured in that campaign (one campaign, so a starting point rather than a law)

The supervisor-launched unit that drove a rolling wave made 79 model calls in 2.5 hours; the agents it started did the rest.
Rows closed per percent of weekly quota stayed about the same across supervised trains and the unattended wave (about 14 to 15
rows per percent). Compare tokens per closed item across your own runs before concluding the loop is cheaper; the main
benefits seen were that a long run no longer needs an attended session and that a death costs minutes, not the unit.

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
