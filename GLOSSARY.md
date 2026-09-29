# Glossary: the words these skills use for an AI agent fleet

These skills grew out of months of running fleets of Claude Code agents on one large codebase, and they use a lot
of vocabulary that grew up with them. Some of it is standard, some borrows a standard word for a narrower job, and
some was coined along the way. Each entry below says what the term means here, names the closest industry term where
one exists, and points to where it lives in these skills.

## The fleet

**Fleet.** Many AI agents working the same codebase at once, each on its own piece. A typical fleet here is up to
six implementers, one lander and a few read-only reviewers. → `agent-fleet` §5 (the concurrency budget).

**Orchestrator.** The one session a person talks to. It plans the work, dispatches agents, reads their reports and
decides what lands. It writes almost no code itself, and it keeps its own transcript short: briefs and reports are
files, and the conversation holds only their paths. *Industry term: the orchestrator in the orchestrator–worker
pattern.* → `agent-fleet`, "Roles".

**Subagent.** Any agent the orchestrator starts. Each gets a narrow job, a fresh context and a turn cap, and returns
a structured report. The model follows the ROLE: judgment roles (implementer, lander, refuter, reviewer) run the top
everyday model, and mechanical roles (filing notes, lookups) run a cheaper one. → `agent-fleet` §11.

**Implementer.** A subagent that fixes a group of related defects. It works in its own **git worktree** (a separate
working copy of the repository on its own branch), so several can run side by side without touching each other's
files. → `agent-fleet` §2, `references/brief-template.md`.

**Lander.** A subagent that merges finished branches and puts them on the main branch. It re-runs the whole test
suite on the merged result, checks each claimed fix against its commit and its tests, and drops anything that doesn't
verify. *Closest industry term: a merge queue (GitHub's merge queue, Bors, Zuul).* "Landing" a change is Mozilla and
Chromium usage. → `agent-fleet` §6.

**Train.** One landing's worth of finished branches, usually three to five, merged and tested together, with one
commit per branch so a red result bisects cleanly. Most of a landing's cost is fixed (merge, build, test, push), so
batching lowers the cost per fix; that saving is modelled, not measured. *Industry term: GitLab's merge trains.*
→ `agent-fleet` §6.

**Wave, rolling wave.** One batch of implementer work. It is rolling: when an implementer returns, the next group
starts in its slot at once, and a train starts whenever enough branches are ready, so no slot waits for the slowest
agent. *Industry terms: batch, worker pool. Not PMBOK's "rolling-wave planning", which is unrelated.*
→ `references/rolling-wave.js`.

**Refuter.** An adversarial reviewer whose only job is to overturn a verdict. It sees the claim and the evidence, not
the reasoning that produced them, so it isn't anchored by it. *Industry terms: red team, adversarial reviewer,
critic.* → `agent-fleet` §10.

**Registrar.** The agent that files other agents' leads as work items, re-running each lead's repro once before
filing it. *Industry term: triager.* → `agent-fleet` §2.

## The work

**Register.** The single list of open work: one note per defect or decision, with its severity, its code location
and the rule it violates. There is exactly one, because when there were several, a real defect hid in a paragraph
none of them tracked. *Industry term: backlog, or issue tracker.*

**Cluster, group.** Defects grouped by the source file they live in, so one agent fixes everything in that file in
one pass. The groups are computed from each note's code location, never picked by hand. A file with more defects
than one agent should take gets a **same-file successor**: a fresh agent that inherits the first one's branch and
handoff. → `agent-fleet` §7, `references/fix_clusters.py`.

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
formal verification's "discharging a proof obligation".* → `agent-fleet` §2.

## The gates

**Gate.** A check that must pass before work moves forward: an implementer's test run before it reports done, the
lander's whole-suite run before it lands, CI before anything reaches main. *Industry term: quality gate.*
→ `test-gate`.

**Protected main.** The main branch accepts only commits that passed CI. The lander pushes to a staging branch, and
a landing script fast-forwards main only when CI is green on that exact commit. The server enforces it for everyone,
the repository's owner included. → `agent-fleet` §6.

**Other-OS gate.** A local run of CI's legs for an operating system the gates don't run on (for example, CI's Linux
jobs run under WSL on a Windows host), done before every push. → `agent-fleet` §6.

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
a fresh one continues from the checkpoint instead of starting over. → `agent-fleet` §4.

**Handoff.** The short written note a finishing agent leaves for the next agent on the same files: what it did,
what it learned, where to look next. The next agent is a fresh agent. It inherits the note and the branch, never
the transcript. The note is navigation, never evidence. → `agent-fleet` §4 and §7.

**Stamp.** The first line of the status file (`STATUS-AT: <sha>`) names the commit it was written at. A script
compares that with the branch, so the next agent knows whether the note covers everything, or exactly which newer
commits it must read. → `references/status_delta.py`.

**Orientation.** What an agent spends before its first useful edit: reading code and working out where things are.
It was about half of every implementer's tokens. One script now prints a file's outline, its tests, and what earlier
fixes learned about it, in a single call. → `references/orient.py`.

**STOP file.** A file whose presence tells every running agent to checkpoint and return at its next step. Workflow
agents can't be messaged, so this is how a fleet stops gracefully before a usage limit instead of dying mid-step.
→ `agent-fleet` §5.

## When agents fail

**Hung agent.** An agent whose model call simply stops: no error, no more output. It is rare, but it happens.

**Watchdog.** A background script that raises an alarm when an agent has been silent longer than normal, or when
the workflow claims to be running but no agent is actually working. Its thresholds are measured, not guessed: 99.9 %
of an agent's waits on the model finish in under 94 seconds. → `references/stall_watch.py`.

**Ceiling.** A time limit per implementer, so one hung agent can't hold up everyone queued behind it.
→ `references/rolling-wave.js` (`implementerCeilingMin`).

## How the process learns

**Devlog.** A running log of every change, decision and mistake, written by the agents as a standing rule, newest
entry first. It is the project's memory and the raw material for the learnings. → `devlog`.

**Learnings, vetted.** Lessons mined from the devlog. A lesson becomes a rule in a skill only after an independent
check against primary sources and an adversarial refuter. Of 145 candidate lessons, 46 survived. Rules not yet
proven say so where they stand. → [LEARNINGS.md](LEARNINGS.md).

**Skills.** Claude Code's packaged instructions and scripts, this repository. Every vetted lesson lives in one.

---

A term missing here? Open an issue and it will be added.
