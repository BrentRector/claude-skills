# Glossary: the words these skills use for an AI agent fleet

These skills grew out of months of running fleets of Claude Code agents on one large codebase, and they use a lot
of vocabulary that grew up with them. Some of it is standard, some borrows a standard word for a narrower job, and
some was coined along the way. Each entry below says what the term means here, names the closest industry term where
one exists, and points to where it lives in these skills.

## The fleet

**Fleet.** Many AI agents working the same codebase at once, each on its own piece. A typical fleet here is up to
six implementers, a read-only reviewer per finished branch, and a finisher when a branch bounces. → `agent-fleet/references/concurrency-and-watchdog.md` (the concurrency budget).

**Orchestrator.** The one session a person talks to. It plans the work, dispatches agents, reads their reports and
decides what lands. It writes almost no code itself, and it keeps its own transcript short: briefs and reports are
files, and the conversation holds only their paths. *Industry term: the orchestrator in the orchestrator–worker
pattern.* → `agent-fleet`, "Roles".

**Subagent.** Any agent the orchestrator starts. Each gets a narrow job, a fresh context and a turn cap, and returns
a structured report. The model follows the ROLE: judgment roles (implementer, finisher, refuter, reviewer) run the top
everyday model, and mechanical roles (filing notes, lookups) run a cheaper one. → `agent-fleet/references/refuters-and-routing.md`.

**Implementer.** A subagent that fixes a group of related defects. It works in its own **git worktree** (a separate
working copy of the repository on its own branch), so several can run side by side without touching each other's
files. → `agent-fleet/references/inputs-and-briefs.md`, `references/brief-template.md`.

**Enqueue step.** The deterministic SCRIPT that lands one finished branch: fetch, rebase onto the default branch,
run the targeted gate on both hosts under the gate-slot cap, stamp the log entry's number, run the landing checks,
open one pull request and add it to the merge queue. No agent runs it unless it stops. "Landing" a change is Mozilla
and Chromium usage. → `agent-fleet/references/landing.md`.

**Finisher.** A subagent dispatched for ONE branch the enqueue step could not take: a rebase conflict, a merge-queue
bounce, or a reviewer's confirmed findings. It fixes, re-runs the targeted gate and re-enqueues; it never assembles
branches or runs the whole population. → `automating-agent-guardrails/templates/agents/finisher.md`.

**Merge queue, merge group.** The protected branch accepts only queued pull requests. The queue builds a MERGE GROUP
(one or several queued pull requests on top of the default branch), CI runs the whole population on it, and the
branch advances only on green; a red bounces only the pull request that caused it. Merge commits, not squash, so a
branch's commits stay ancestors of the default branch. *Industry terms: GitHub's merge queue, Bors, Zuul, GitLab's
merge trains.* → `agent-fleet/references/landing.md`.

**Lander** *(retired 2026-10-11)*. A subagent that merged several finished branches into a **train**, ran the whole
test suite locally, reviewed, and pushed under a **landing lease**. In one measured campaign ten of them were spent
on six trains, and 41 % of their minutes were local gate runs CI repeated. Replaced by the enqueue step, the merge
queue and the finisher. → `agent-fleet/references/landing.md` ("Retired").

**Train** *(retired 2026-10-11)*. One landing's worth of finished branches (four to six), merged and tested
together. Rational only while each landing carried a large fixed cost; replaced by one pull request per branch.

**Landing lease** *(retired 2026-10-11)*. A lock one lander held from its push through the CI wait, so landings
serialized at about one an hour. The merge queue serializes instead.

**Wave, rolling wave.** One batch of implementer work. It is rolling: when an implementer returns, the next group
starts in its slot at once, a read-only reviewer checks each branch that returns DONE, and each approved branch is
enqueued, so no slot waits for the slowest agent. *Industry terms: batch, worker pool. Not PMBOK's "rolling-wave planning", which is unrelated.*
→ `references/rolling-wave.js`.

**Refuter.** An adversarial reviewer whose only job is to overturn a verdict. It sees the claim and the evidence, not
the reasoning that produced them, so it isn't anchored by it. *Industry terms: red team, adversarial reviewer,
critic.* → `agent-fleet/references/refuters-and-routing.md`.

**Registrar.** The agent that files other agents' leads as work items, re-running each lead's repro once before
filing it. *Industry term: triager.* → `agent-fleet/references/inputs-and-briefs.md`.

## The work

**Register.** The single list of open work: one note per defect or decision, with its severity, its code location
and the rule it violates. There is exactly one, because when there were several, a real defect hid in a paragraph
none of them tracked. *Industry term: backlog, or issue tracker.*

**Cluster, group.** Defects grouped by the source file they live in, so one agent fixes everything in that file in
one pass. The groups are computed from each note's code location, never picked by hand. A file with more defects
than one agent should take gets a **same-file successor**: a fresh agent that inherits the first one's branch and
handoff. → `agent-fleet/references/grouping-fixes.md`, `references/fix_clusters.py`.

**Brief, dispatch spec.** The file an agent is pointed at instead of a pasted prompt: its slice of the work, the
code sites, the repro, the rule, the gate command and the report format. A file survives a restart; a prompt does
not. → `references/brief-template.md`.

**Verdict, adjudication.** For each rule of the specification the software must meet, an agent decides whether the
software conforms and records the evidence: a test, a program, a diagnostic. That decision is a verdict. Adjudicating
means deciding against the specification's own text, never against another implementation's behavior.
→ `spec-oracle`, `spec-compliance-audit`.

**Citation check.** Every reference to the specification, in code, tests or notes, is checked by a script against
the specification's actual text. Agents rarely invent citations, but they often copy a wrong clause number forward
from an earlier note. → `spec-oracle`.

**Differential testing.** Running the same inputs through an independent implementation and comparing the output.
It is a second opinion, not the authority: when the two disagree, the specification decides. *Standard term, since
McKeeman, 1998.* → `test-gate`.

**Discharge.** Closing a work item WITHOUT a fix, because re-running its repro on today's build shows it no longer
reproduces. A discharge closes something, so a refuter checks it like any other closing verdict. *Borrowed from
formal verification's "discharging a proof obligation".* → `agent-fleet/references/inputs-and-briefs.md`.

## The gates

**Gate.** A check that must pass before work moves forward: the targeted local gate before an implementer reports
done and again in the enqueue step, and CI's whole-population run on the merge group before anything reaches the
default branch. *Industry term: quality gate.* → `test-gate`.

**Targeted leg.** A change's own tests, the likely reds for its diff, the cases it reaches and the host-only
witnesses, run natively and then in a clone on the other OS, fail-fast. The local gate for every change; the whole
population is CI's. → `test-gate`, `cross-platform` §1.

**Host-only witness.** A test that reproduces only on the developer host, typically because its filesystem differs
from CI's runners (ReFS versus NTFS deletes). It carries a trait naming that property and runs in every targeted leg;
membership is derived from the trait, never listed. → `test-gate/references/tiers-and-landing.md`, `cross-platform` §1.

**Protected main.** The main branch accepts only queued pull requests: a ruleset requires a pull request and the merge
queue, with the required check evaluated on the merge group, enforced for everyone, the repository's owner included.
A guard hook tells an agent that tries a direct push which command to run instead. → `agent-fleet/references/landing.md`.

**Other-OS repro run.** A local run of CI's FULL legs for the other operating system (for example, CI's Linux jobs
under WSL on a Windows host). Since 2026-10-11 it reproduces a CI red and is no longer a gate; the targeted leg still
runs on both OSes. → `cross-platform` §1.

**Drift test.** A test that holds two things in agreement, so a rule stays true as the code changes: every rule the
specification catalogues has a test, every CI job's projects are covered locally, every brief carries its mandatory
lines. *Closest industry terms: architecture fitness functions, ArchUnit-style architecture tests.*
→ `engineering-standards`, `test-gate`.

**Hooks and guardrails.** Scripts that run on every tool call an agent makes and can refuse it: a forbidden
command, a commit with a stale status file. An instruction in a prompt is a suggestion; a hook that blocks the
command isn't. → `automating-agent-guardrails`.

## Memory and cost

**Transcript.** Everything an agent has read and written in its session. It re-reads all of it on every turn, so
its token cost grows roughly with the square of its length. That one fact drives most of the design: turn caps,
small fresh agents, and splitting work instead of extending it. → `agent-fleet` §1.

**Checkpoint.** Work saved to disk as the agent goes: a commit after each fix, plus a status file. If an agent dies,
a fresh one continues from the checkpoint instead of starting over. → `agent-fleet/references/checkpointing.md`.

**Handoff.** The short written note a finishing agent leaves for the next agent on the same files: what it did,
what it learned, where to look next. The next agent is a fresh agent. It inherits the note and the branch, never
the transcript. The note is navigation, never evidence. → `agent-fleet/references/checkpointing.md` and `agent-fleet/references/grouping-fixes.md`.

**Stamp.** The first line of the status file (`STATUS-AT: <sha>`) names the commit it was written at. A script
compares that with the branch, so the next agent knows whether the note covers everything, or exactly which newer
commits it must read. → `references/status_delta.py`.

**Orientation.** What an agent spends before its first useful edit: reading code and working out where things are.
It was about half of every implementer's tokens. One script now prints a file's outline, its tests, and what earlier
fixes learned about it, in a single call. → `references/orient.py`.

**STOP file.** A file whose presence tells every running agent to checkpoint and return at its next step. Workflow
agents can't be messaged, so this is how a fleet stops gracefully before a usage limit instead of dying mid-step.
→ `agent-fleet/references/concurrency-and-watchdog.md`.

## When agents fail

**Hung agent.** An agent whose model call simply stops: no error, no more output. It is rare, but it happens.

**Watchdog.** A background script that raises an alarm when an agent has been silent longer than normal, or when
the workflow claims to be running but no agent is actually working. Its thresholds are measured, not guessed: 99.9 %
of an agent's waits on the model finish in under 94 seconds. → `references/stall_watch.py`.

**Ceiling.** A time limit per implementer, so one hung agent can't hold up everyone queued behind it.
→ `references/rolling-wave.js` (`implementerCeilingMin`).

## How the process learns

**Devlog.** A running log of every change, decision and mistake, written by the agents as a standing rule: one file
per entry, one entry per landing, numbered when the branch is enqueued, with the newest-first view rendered rather than
committed. It is the project's memory and the raw material for the learnings. → `devlog`.

**Learnings, vetted.** Lessons mined from the devlog. A lesson becomes a rule in a skill only after an independent
check against primary sources and an adversarial refuter. Of 145 candidate lessons, 46 survived. Rules not yet
proven say so where they stand. → [LEARNINGS.md](LEARNINGS.md).

**Skills.** Claude Code's packaged instructions and scripts, this repository. Every vetted lesson lives in one.

---

A term missing here? Open an issue and it will be added.
