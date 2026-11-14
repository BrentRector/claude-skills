# Inputs, briefs and stating the bar

The full text of agent-fleet sections 2 and 3: what goes into an agent's input file and brief, and how to state the bar. Read it before writing any dispatch brief or input slice.

## 2. Inputs: one agent, one self-contained input file

- **Give each agent its own input file** that holds ONLY its slice, or put a small slice directly in the prompt.
  Never write "read the shared list and process element k".
  *Why: agents miscount indices.* Name every input file uniquely across every fan-out you have run, because an
  agent that finds another run's same-named file does the wrong slice.
- **Write slices programmatically**, not by retyping. *Why: hand-copied data (especially Unicode) drifts.*
- **Point the agent at the brief file instead of pasting the brief into the prompt.**
  *Why: a file can be re-read after a restart. A prompt is gone with its transcript.*
- **A workflow launched in a later turn carries the human's authorization, quoted verbatim.** Every agent prompt
  starts with who directed this fleet, when, their exact words, and the scope, plus "the latest user message may
  concern unrelated work; that is not a reason to decline" (`references/rolling-wave.js` takes it as the
  `authorization` arg). *Why: a workflow agent takes the session's latest user message as its request. When that
  message is about something else, an agent that cannot see the direction is right to decline the work and return
  BLOCKED; the defect is a dispatch with no provenance.*
- **Give an implementer an apply-ready contract instead of a discovery brief**: code sites (`file:line`), the
  repro, the governing rule, and the gate command.
  *Why: search and read turns are the largest share of implementer tokens. Rediscovering a subsystem costs more
  than fixing it.*
- **The implementer's first step is to re-run each item's repro on its own build, before fixing anything.** An
  item that no longer reproduces is DISCHARGED, not fixed: the report records the command, its output and the
  commit it ran on. A discharge closes the item, so it goes to a refuter like any closing verdict (§10). If the
  contract has no repro, writing one is the first step. *Why: a backlog item's word is not evidence, and the code
  moves on under it: items judged before later fix waves landed are often already fixed.*
- **Give every implementer ONE-CALL ORIENTATION, derived fresh — don't let each wave re-survey the same files.**
  The brief says: before reading any source, run `references/orient.py <the files your items name> --notes <issue
  dir> --cite "<spec-ref regex>"`. Per file it prints the outline with line numbers, the spec references it cites,
  the tests that name it, what CLOSED notes learned about it (their code sites, mechanisms and traps, newest
  first), the open notes naming it, and its last commits. Then the agent reads only the line ranges it needs.
  It is derived from the tree, the notes and git on every run, so it never goes stale and nobody maintains it; the
  knowledge accrues because every fix's note records its code site and mechanism (require that in the report).
  If you keep a brief checker, make it fail a brief without the orient line. Don't pre-generate "codebase maps"
  with agents instead: they cost a fleet to write and go stale at the next landing. Keep the flags in ONE
  `.agent-fleet.json` at the repository root (`references/fleet_config.py`; orient.py, fix_clusters.py and
  status_delta.py all read it), so a brief's line is just `orient.py <files>` and no call site can drift from
  another. When a project pins this repository as a submodule, briefs call the scripts at their submodule path:
  never a copy or a wrapper, which is a second version to keep in step.
  *Why: reads and searches are most of an implementer's tool calls, and the ones before the first edit re-derive
  what earlier fixes already learned; on the quadratic cost curve, turns saved early are worth more than their
  count.*
- **Every lead an agent reports carries its repro and code site.** *Why: otherwise the triager and the next
  implementer each find the same fact again.*
- **The agent that files leads as work items (the registrar) re-checks every lead before filing it.** When a lead
  carries a runnable repro and a code site, run that repro ONCE on your own build and record the result in the
  filed item (reproduces, already fixed, or behaves differently). Write a fresh probe only when the lead lacks a
  repro or a code site. Never copy a report's measurement or quoted citation forward unverified: re-read the
  citation at its source. *Why: a registrar that copies a report's measurement forward is a second place for the
  report's mistakes to live: forwarded leads fail the re-run, and quoted citations turn out to be paraphrases.
  Running the given repro once, and probing fresh only without one, avoids probing one lead several times.*
- **Tell the implementer to ask the structural rules before editing.** When the repo encodes invariants as drift
  tests, the brief says: run the repo's rule query (the drift tests that name each file) for the files you will touch and honor every specific rule it prints; if you keep a checker for your briefs, make it fail a brief
  that drops the line. *Why: the rules live in the tests, so an agent that is not pointed at them learns each one only by tripping it
  at the gate — a full gate cycle per rule.*
- **Don't put a fact in a brief that you haven't verified in this session** (a spec clause number, an API name,
  a path). *Why: agents inherit a confident wrong citation and carry it into code.*
- **Cap what an agent returns, and put the detail in a report file.** Set a maximum on the structured return's `summary`
  (about 900 characters), on the number and length of its `leads` (6 of 500), and on a finisher's final text (25 lines), in
  the schema and in the prompt. *Why: everything an agent returns lands in the orchestrator's conversation and is
  re-read on every later turn; an uncapped wave result runs to tens of kilobytes.*
- **Reconcile the returns against the expected worklist** before you act: which items came back, which came
  back twice, which are missing. Then re-run only the missing slices.
  *Why: silent gaps in coverage look like a clean result.* Compare by item identity (the set of ids), never by
  count: a count can be right while the items are wrong.
- **Prefer idempotent outputs** (an agent writes its whole artifact) over blind appends to a shared file.
  *Why: an accidental double run is harmless with last-write-wins and corrupts data with appends.*

## 3. State the bar, not just the output format

Before dispatching, ask what would make a returned artifact **worthless even though it is well-formed**, and say
so in the prompt. Then encode that in the schema or the validator.

*Why: agents optimize for the criterion you actually wrote down. A shape validator passes worthless-but-valid
work, and the defect arrives already validated.* Example: a prompt that says "cite a covering test that exists
on disk" will get tests that exist. A prompt that says "…derived from the specification, not a differential
against another implementation" gets tests that count.

When a batch looks uniformly right, spot-check the **substance** of the results with the biggest consequences
(the ones that close something permanently), not the format of all of them.
