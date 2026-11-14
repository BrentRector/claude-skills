# The concurrency budget, liveness and the stall watchdog

The full text of agent-fleet section 5. Read it before sizing a fleet, starting a background workflow, or deciding that an agent is stalled or dead.

## 5. The concurrency budget and stopping before the limit

- **Default budget: a handful of implementers (~3–6) + a read-only reviewer per DONE branch + one read-only chunk
  ~4 wide; finishers as conflicts and bounces arrive.** Landing is a script, so it takes no agent slot. Run big
  fan-outs as `parallel()` chunks inside a loop, not as one very wide pipeline.
  These are defaults, not limits: re-measure the draw on your own plan and model. *Why: concurrent agents draw the
  same window in parallel, and a few dozen of them can exhaust it in hours.*
- **Tokens are what the quota rations, not slots.** The turn caps control spend. The budget is for containing
  errors. *Why: a few long agents cost more than many short ones.*
- **A fleet of more than ~40 agents means you should split the work.** Don't wait it out.
- **Drive the stop thresholds from the real usage meter** the project names (not a hand-kept tally of tokens). At
  ~75 % of the working budget, dispatch only finishers of nearly finished work. At ~85–90 %, create STOP.
  *Why: the limit kills every live agent at once, including any partway through a merge or a fix.*
- **Use a graceful STOP file.** Every dispatch prompt includes: *"Before each new step, check for
  `{SCRATCH}/STOP`. If it exists, checkpoint-commit, write STATUS.md NEXT, and return status SPLIT. Never
  start a build or gate once STOP exists."* To stop, create the file, wait for the agents to return, and only
  then kill any stragglers. *Why: workflow agents can't be messaged, and a hard kill lands mid-step.*
- **Verify every launch started.** Within a few minutes of a dispatch, each agent has a `started` record in the
  workflow journal or a transcript of its own. Check it once, by item identity: an agent that failed to spawn (an API
  error, a rejected `agent()` call) leaves neither, so the watchdog below, which watches started agents, cannot see
  it, and its items sit idle until someone looks.
- **Run `references/stall_watch.py <workflow transcript dir>` in the background next to EVERY fleet workflow.** It
  exits, and so wakes the orchestrator, the moment a pending agent's transcript has been silent:
  - more than 10 minutes while waiting on the MODEL (its last record is not an open tool call), or
  - more than 12 minutes INSIDE one tool call,
  or the moment the workflow has had NO agent in flight and no agent activity for 10 minutes (IDLE). IDLE does
  not take the scheduler's word that it is running: a workflow reported running with no agent working is hung in
  its own scheduler (an agent that dies on an API error can leave its successor waiting forever while the
  workflow reads "running"). An agent the journal records as `failed` is reported as dead, never as waiting, and a death
  during the watch EXITS the watcher: the scheduler moves on, but the dead agent's checkpoint needs a finisher (or
  a recorded decision to abandon the branch) before the next watch starts, and an agent can die with no error recorded. Stop
  the watcher when the workflow's completion notice arrives; otherwise its IDLE exit is one false wake-up.
  It reads each record's own timestamp, not file times. Point it at the transcript directory of the CURRENT
  orchestrating session: clearing or restarting that session moves the still-running agents' transcripts to the new
  session's directory, so a watcher on the old one sees silence that is not a stall. *Why these thresholds, measured over 150 transcripts (~27,800
  silences): model waits were under 94 s at the 99.9th percentile; tool calls peaked at 585 s (a 580 s blocking gate
  wait). A model call CAN hang, even after the agent has finished and gated its work, and nothing else notices.*
- **A stalled agent: let the others finish, then stop the workflow and dispatch the remainder by hand.** A workflow
  cannot stop one of its own agents, and nothing outside it can either. A hung agent's commits are on its branch,
  so a fresh finisher resumes from its stamped `STATUS.md`, or the enqueue step takes the branch as it is if a
  green gate record covers its head. `rolling-wave.js` also carries a per-implementer ceiling (`implementerCeilingMin`, default
  240): an agent still running at the ceiling is recorded `STALLED` and the wave moves on, so a hang cannot block a
  wave forever. The enqueue step is a script with its own timeouts, so no landing agent can hang a wave.
- **An agent never ends its turn while its own background job is running.** It starts the job with output to a
  log, then blocks in the foreground with `timeout 580 bash -c 'until grep -q "<verdict>" <log>; do sleep 5; done'`,
  reissuing that until the verdict prints. *Why: an agent that returns early gets its background gate killed,
  and it reports "PENDING".*
  ⛔ Never block with `tail -f <log> | grep -m1 <verdict>`. `grep` exits on the match, but `tail` only notices at its
  next write, and a verdict is usually the log's LAST line, so the wait idles until its timeout (exit 124)
  while `until grep` returns at once.
