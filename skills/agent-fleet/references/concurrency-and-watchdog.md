# The concurrency budget, liveness and the stall watchdog

The full text of agent-fleet section 5. Read it before sizing a fleet, starting a background workflow, or deciding that an agent is stalled or dead.

## 5. The concurrency budget and stopping before the limit

- **Default budget: 1 lander + a handful of implementers (~3–6) + one read-only chunk ~4 wide.** Run big
  fan-outs as `parallel()` chunks inside a loop, not as one very wide pipeline.
  *Why: in one measurement, ~28 concurrent agents burned ~20 % of a session window in 11 minutes, and ~50
  exhausted a window in ~2.5 h.* *(Practice — not yet validated: no before/after measure of conflicts or quota under the budget.)*
- **Tokens are what the quota rations, not slots.** The turn caps control spend. The budget is for containing
  errors. *Why: a few long agents cost more than many short ones.*
- **A fleet of more than ~40 agents means you should split the work.** Don't wait it out.
- **Keep a running tally** of subagent tokens since the window began. At ~75 % of the working budget, dispatch
  only finishers and landers of nearly finished work. At ~85–90 %, stop everything gracefully.
  *Why: the limit kills every live agent at once, including landers partway through a landing.* *(Practice — not yet validated: no evidence the tally, rather than the real usage meter and the STOP file, prevented a kill; drive it from the meter.)*
- **Use a graceful STOP file.** Every dispatch prompt includes: *"Before each new step, check for
  `{SCRATCH}/STOP`. If it exists, checkpoint-commit, write STATUS.md NEXT, and return status SPLIT. Never
  start a build or gate once STOP exists."* To stop, create the file, wait for the agents to return, and only
  then kill any stragglers. *Why: workflow agents can't be messaged, and a hard kill lands mid-step.* *(Validated 2026-09-28.)*
- **Judge a background workflow's liveness by its processes and its journal, never by transcript file times.**
  Alive means: the workflow's own run status and progress journal are advancing, or its agents' processes (builds,
  test runs) are running in their worktrees, or their worktrees are gaining commits and changed files. A watchdog
  or restart decision keys on those. If you must read a transcript, one that ends on a tool call with no result
  yet is LIVE for up to that tool's maximum duration, and no longer (so a killed agent's dangling call does not
  count as alive forever). *Why, measured: (1) a tool call writes nothing to the agent's transcript until it
  returns: one line when the call starts and one when its result arrives. A gate wait of the form
  `timeout 580 … tail -f <log> | grep -m1 …` is a ~580-second silence; each of four agents in one run showed 5–7
  silences over 120 s, the longest 582–585 s, every one opened by a shell tool call, so a check on a short modification-time window
  calls a live agent dead during every long tool call. (2) Clearing or restarting the orchestrating session moves
  the still-running agents' transcripts to the NEW session's directory while the workflow journal stays in the old
  one; a watchdog reading the old directory saw 20+ minutes of silence for that reason alone. Restarting a live
  fleet duplicates its work and races its worktrees.* *(Practice — not yet validated: not yet exercised across several waves, including a restart during a running fleet.)*
- **Run `references/stall_watch.py <workflow transcript dir>` in the background next to EVERY fleet workflow.** It
  exits, and so wakes the orchestrator, the moment a pending agent's transcript has been silent:
  - more than 10 minutes while waiting on the MODEL (its last record is not an open tool call), or
  - more than 12 minutes INSIDE one tool call,
  or the moment the workflow has had NO agent in flight and no agent activity for 10 minutes (IDLE). IDLE does
  not take the scheduler's word that it is running: a workflow reported running with no agent working is hung in
  its own scheduler. *Once, an agent died on an API error, a scheduler bug left its successor waiting forever,
  and the workflow showed "running" for 16 hours. Replaying that workflow's journal, IDLE fires 10 minutes after
  the last agent finished.* An agent the journal records as `failed` is reported as dead, never as waiting, and a death
  during the watch EXITS the watcher: the scheduler moves on, but the dead agent's checkpoint needs a finisher. *Three
  of six implementers in one wave died near the end with no error recorded, and nothing woke the orchestrator.* Stop
  the watcher when the workflow's completion notice arrives; otherwise its IDLE exit is one false wake-up.
  It reads each record's own timestamp, not file times. *Why, measured over 150 transcripts (~27,800
  silences): model waits were under 94 s at the 99.9th percentile; tool calls peaked at 585 s. A model call CAN
  hang: two implementers in one wave stopped producing tokens after a successful tool result, one of them after it
  had finished and gated all its work. Nothing noticed for 90 minutes, and the wave's final train waited on it.* *(Practice — not yet validated: the thresholds are measured, but the watcher has not yet caught a stall in production.)*
- **A stalled agent: let the others finish, then stop the workflow and dispatch the remainder by hand.** A workflow
  cannot stop one of its own agents, and nothing outside it can either. A hung agent's commits are on its branch,
  so a fresh finisher resumes from its stamped `STATUS.md`, or a lander takes the branch as it is if its gate was
  green. `rolling-wave.js` also carries a per-implementer ceiling (`implementerCeilingMin`, default 240): an agent
  still running at the ceiling is recorded `STALLED` and the wave moves on, so a hang cannot block a wave forever.
  Landers get no ceiling, because a timed-out lander might still be pushing when the next train starts; for a
  stalled lander, the watchdog alerts a person. *(Practice — not yet validated: the ceiling has not yet fired in production.)*
- **Late in a window, dispatch short jobs that are close to done. Early in a window, dispatch long ones.**
  *Why: that way a burst can't exhaust the window before anything is finished.*
- **An agent never ends its turn while its own background job is running.** It starts the job with output to a
  log, then blocks in the foreground with `timeout 580 bash -c 'until grep -q "<verdict>" <log>; do sleep 5; done'`,
  reissuing that until the verdict prints. *Why: an agent that returns early gets its background gate killed,
  and it reports "PENDING".* *(Validated 2026-09-28.)*
  ⛔ Never block with `tail -f <log> | grep -m1 <verdict>`. `grep` exits on the match, but `tail` only notices at its
  next write, and a verdict is usually the log's LAST line, so the wait idles until its timeout. *Measured: a gate
  went green at 11:56 and its `tail -f` wait returned at 12:03:48 (exit 124). A 10-line test log shows the same:
  `tail -f` returns at the timeout, `until grep` at once.* *(Validated 2026-09-29.)*
