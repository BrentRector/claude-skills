# Brent Rector's Claude Code skills

Engineering-discipline skills for [Claude Code](https://code.claude.com), distilled from long-running production
work — a standards-conformant compiler built largely by Claude agents, a commercial .NET tool, and several smaller
projects. Each skill encodes rules that were learned the expensive way; the *why* travels with every rule.

**[LEARNINGS.md](LEARNINGS.md)** holds the vetted learnings behind these skills: the 46 of 145 candidates from the
project's development log that survived validation against primary sources and an independent refuter. Rules in
the skills that are not yet proven say so where they stand.

## Install

```
/plugin marketplace add BrentRector/claude-skills
/plugin install brent-tools@brentrector-claude-skills
```

To pin the skills to a repository instead, so every clone and every agent session gets the same version, add this
repository as a git submodule (say at `tools/claude-skills`) and declare it in the project's
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "brentrector-claude-skills": { "source": { "source": "directory", "path": "./tools/claude-skills" } }
  },
  "enabledPlugins": { "brent-tools@brentrector-claude-skills": true }
}
```

Project skills that extend one of these can then open by invoking the base (`brent-tools:<skill>`) and keep only
what is specific to the project. Where the plugin isn't loaded (some cloud sessions don't receive project
marketplaces), the base's `SKILL.md` is still readable at its submodule path.

## What's new in 1.12.0

- **The learnings were validated, and the skills now say which rules are proven.** The 145 candidate learnings from
  the development log were each checked against the primary sources (log entries, commits, CI and test records,
  agent transcripts) by a validator, and every VETTED ruling was then re-checked by an independent refuter told to
  overturn it.
  - **46 VETTED, 90 UNPROVEN, 9 REFUTED.** The refuters overturned **21 of the 67** rulings the first validator had
    vetted, 15 to unproven and 6 to refuted.
  - **Refuted claims removed or corrected.** Seven of the nine were never encoded here. Two were, and one more
    was answered:
    - *"One mechanism per implementer, one landing per lander transcript"* rested on a modelled cost, never a
      measurement, and later practice grouped related fixes. `agent-fleet` §6–§7, `spec-compliance-audit` §7 and
      the lander role template no longer give the modelled cost as a reason, and related fixes are grouped.
    - *"A continuation after a kill confirms, it never re-applies"*: continuations confirmed finished steps and
      redid half-done ones. `agent-fleet` §12's restart step now says so, and reads the dead lander's worktree.
    - *"Find-then-verify reviews find real bugs in every phase"* (never stated here): several reviews correctly
      found nothing. `review` Step 6 now says a null result is a valid outcome, labelled unproven.
  - **Unproven rules are labelled.** They stay, marked *"Practice — not yet validated: <the missing evidence>"*, in
    `SKILL.md` and the matching `README.md` row. Vetted rules are marked *"Validated 2026-09-28"*.
  - **Figures corrected** where validation found them wrong: 7 of 10 implementers (not all) declined an
    unauthorized fleet; 5–7 silences over 120 s per agent, the longest ~585 s; 15 compatibility cases, not samples.
  - **Vetted refinements added:** confirm a build succeeded and hash the assemblies when in doubt (`test-gate`);
    check each OR'd filter term's own count (`test-gate`); name input files uniquely and compare returns by id set,
    not count (`agent-fleet` §2); re-measure a work item's premise before fixing it (`engineering-standards` §3);
    the measured 1-hour-cache saving, and dropping the cache for roles that never wait (`automating-agent-guardrails`).
  - A same-run timing ratio is no longer offered as a replacement for a wall-clock ceiling (`review`,
    `pr-test-analyzer`): one went red on unchanged code.
- **[LEARNINGS.md](LEARNINGS.md) is back, with only the 46 vetted learnings**, each with its problem, root cause,
  where the fix lives, the corrected evidence and its validation. The unproven and refuted candidates stay in the
  project's research record, not here.

## What's new in 1.11.0

- **New skill: [`devlog`](skills/devlog/)**, a development log that Claude agents write and use as the project's
  memory.
  - **Three forms, chosen by purpose:** a working history (one entry per change, in the same commit), a defect/fix
    log for reviewers and source-license customers (one entry per defect fixed in shipped code), and published
    narrative posts (one per milestone or finding, reversals included).
  - **Core rules for all three**, each with its reason: an entry with every change; timestamps read from the clock,
    never estimated; a correction is a new entry and old entries are never rewritten; failures and overturned
    verdicts are kept; and only the log is historical, while every other doc describes the current state.
  - **How agents use it:** never loaded at session start (the small current-state document is), and searched before
    retrying an approach.
  - **Learnings come out of it in three stages.** The log records everything. A consolidation run
    (`templates/consolidate-brief.md`) turns it into CANDIDATE learnings. An adversarial validation run
    (`templates/validate-brief.md`) rules each candidate VETTED, UNPROVEN or REFUTED. Only vetted learnings enter
    `LEARNINGS.md`, and only vetted learnings are encoded into skills or rules; refuted candidates stay in the record,
    marked refuted. *Why: a log records hypotheses as well as conclusions, and some are later refuted. A learnings
    file compiled straight from the log inherits those errors, and a skill that encodes them spreads them.*
  - **`references/devlog.py`** (`new` / `check` / `search`) numbers each entry newest + 1 and refuses a collision,
    stamps the time from the clock, and keeps a CRLF file CRLF. It handles both a newest-first file and a directory of
    `NNNN-YYYY-MM-DD-slug.md` entries. **`references/devlog_guard.py`** is a PreToolUse hook that asks before a
    commit that carries no entry. It is registered with no `if` filter, because that filter misses `git add -A &&
    git commit`.
  - **Measured:** the working history this came from reached 1,750+ entries in about six months. One consolidation
    run turned it into 145 CANDIDATE learnings (not yet validated) and 15 open problems in about 30 minutes; the
    contradiction it surfaced was real and was fixed in 1.10.2. Four new evals, all discriminating: WITH 1.00 on
    each, W/OUT 0.00–0.50.
- **Withdrawn, pending validation.** Two things published earlier had not been through the validation above, so they
  are removed rather than left to spread; each comes back only if validation vets it.
  - **`LEARNINGS.md`** (added in 1.10.1). It was compiled from the development log without vetting, so it carried
    the log's refuted hypotheses along with its conclusions. It will be republished containing only vetted learnings (republished in 1.12.0 with only vetted learnings).
  - **`agent-fleet/references/status_guard.py`** and its `agent-fleet` §4 rule (added in 1.9.0). Its sandbox A/B
    was null for staleness, and it has not been proven in production. The stamped handoff it enforced stays:
    `STATUS-AT: <sha>`, read with `status_delta.py` and rewritten after every commit, was proven in an 88-agent
    controlled A/B.

## What's new in 1.10.2

- **Fix: telemetry is enabled in the USER settings** (`automating-agent-guardrails`).
  - Claude Code ignores telemetry-enabling variables in a project's `.claude/settings.json` and
    `.claude/settings.local.json`; a project may only turn telemetry off.
  - `readiness_check.py --enable-telemetry` used to write them to `settings.local.json`, where they did nothing, while
    the check reading that file reported "OK". It now writes `~/.claude/settings.json`, and the check flags a project
    file that sets the switch as dead configuration.
  - The readiness self-test is now hermetic: it no longer inherits the machine's own telemetry variables, which had
    made it RED on any machine with telemetry on.
  - The contradiction was surfaced by compiling LEARNINGS.md (withdrawn in 1.11.0 pending validation: it was compiled
    from the development log without vetting, and will be republished containing only vetted learnings;
    republished in 1.12.0 with only vetted learnings).

## What's new in 1.10.1

- **LEARNINGS.md** (withdrawn in 1.11.0 pending validation: it was compiled from the development log without
  vetting, and will be republished containing only vetted learnings; republished in 1.12.0 with only vetted
  learnings): the consolidated record of agent and fleet
  learnings from the whole project history, grouped by theme. Each entry gives the problem, the root cause, where
  the fix lives in these skills, the measured evidence and the date. It keeps reversals, rejected ideas and null
  results, and closes with the open problems and the lessons the skills do not carry yet, including one the
  guardrails skill currently contradicts: Claude Code ignores telemetry-enabling variables in a project's
  `settings.local.json`.

## What's new in 1.10.0

- **A hung agent can no longer stall a wave unnoticed.** A model call can hang: two implementers in one wave stopped
  producing tokens after a successful tool result, one of them after finishing and gating all its work. Nothing
  noticed for 90 minutes, and the wave's final train waited on it.
  - `agent-fleet/references/stall_watch.py` runs beside every workflow and exits the moment an agent has been silent
    over 10 min waiting on the model, or over 12 min inside one tool call. The thresholds are measured: over 150
    transcripts, model waits were under 94 s at the 99.9th percentile, and tool calls peaked at 585 s.
  - `rolling-wave.js` records an implementer still running after `implementerCeilingMin` (default 240) as `STALLED`
    and moves on, so a hang cannot block a wave forever. Simulated: a never-returning agent hangs the old script,
    and the new one finishes and lands.
  - SKILL §5 gains the procedure: let the others finish, stop the workflow, and dispatch the remainder from the
    stalled agent's branch.

## What's new in 1.9.0

- **`agent-fleet/references/status_guard.py`** (withdrawn in 1.11.0 pending production validation: its sandbox A/B
  was null for staleness). It was a hook that refused a `git commit` while `STATUS.md` did not describe the current
  commit, and refused to let the agent finish in that state. The rule it enforced stays: "rewrite `STATUS.md` after
  EVERY commit".
- **Why, measured.**
  - 3 of 14 finished real branches ended with a stale `STATUS.md` with no crash involved.
  - A stamp test with 88 fresh resumers over 22 scenarios: coverage was misjudged in 11 of 44 resumes without the
    stamp and 0 of 44 with it. Tokens fell about 17 % overall and 31 % when the summary was current.
  - Two sandbox A/Bs of the hook: a per-command reminder was tried and rejected for costing about 20 % more turns
    and dollars. An `if: Bash(git commit*)` filter misses chained and scripted commits, so the hook was registered
    without one.

## What's new in 1.8.2

- **Fix: the rolling wave no longer deadlocks when an agent dies** (`agent-fleet/references/rolling-wave.js`). An
  agent that dies on an API error makes `agent()` reject rather than return null. The rejection escaped the worker
  with its slot still counted and no wake-up sent, so a same-file successor waited forever and the workflow showed
  "running" with nothing left to do; one did so for 16 hours. A rejection is now recorded as `NO-RESULT`, like a null
  return, and the slot and the wake-up are released whatever the outcome. The waiting successor then starts fresh.
  A simulation with a rejecting agent hangs on 1.8.1 and finishes on 1.8.2.

## What's new in 1.8.1

- **Correction: why transcript times are no liveness signal** (`agent-fleet` §5). 1.7.0 said subagent transcripts
  are "written lazily". They aren't. The measured causes are two. A tool call writes nothing to the transcript
  until it returns, so each long gate wait is a ~580-second silence (5–7 of them per agent in one run). And
  clearing or restarting the orchestrating session moves the running agents' transcripts to the new session's
  directory while the workflow journal stays in the old one, which is where the 20+ minutes of "silence" came
  from. The rule is unchanged. §5 now also says how to read a transcript if you must: one ending on an unanswered
  tool call is live for up to that tool's maximum duration, and no longer.

## What's new in 1.8.0

- **One configuration file for the fleet scripts** (`agent-fleet` §2,
  [`fleet_config.py`](skills/agent-fleet/references/fleet_config.py)). `orient.py`, `fix_clusters.py` and
  `status_delta.py` read their settings from a `.agent-fleet.json` at the repository root, so a brief's line is
  just `orient.py <files>`, and a project calls the scripts where they live instead of keeping a wrapper. Flags
  still override it; an unknown key is an error.
- **`orient.py`**: LEARNED is newest-first by the note id's number (a string sort ranked `BUG-62` newer
  than `BUG-1534`), and OPEN is sorted too. C# outlines keep `record struct` and skip statement lines such as
  `return Foo(x)` that looked like declarations. ANTLR `.g4` files get an outline of rules, modes and embedded
  members. A `key` group in `--cite` counts references per clause and lists each clause's rules. New options:
  `--notes-glob`, `--test-ext`, `--max-tests`, `--min-name`; file paths may be given relative to the repository
  root from anywhere inside it.
- **`fix_clusters.py`**: a singleton absorbs another singleton that names its file, so two one-note files that
  name each other are one pass. A path or bare file name counts only if it resolves to a real file, and on a
  directory boundary (`Lexer.cs` no longer matches `MyLexer.cs`; a partial path like `Core/Lexer.cs` now counts).
  `--src` is repeatable and takes globs, `--exclude-dir` leaves generated code out, `--json` adds each note's
  `area` and each cluster's `files`, and a malformed `--harm` is a usage error instead of a traceback.
- **Pinning the plugin as a submodule** (Install, above): project skills become overlays on the published base.

## What's new in 1.7.0

- **The stamped handoff** (`agent-fleet` §4, [`status_delta.py`](skills/agent-fleet/references/status_delta.py)).
  `STATUS.md`'s first line is `STATUS-AT: <sha>`, the commit it describes, written after the checkpoint commit. An
  agent resuming a worktree or merging a predecessor runs `status_delta.py`, which prints CURRENT, STALE by N (read
  only those N commits), or UNSTAMPED / DIVERGED (read every commit since the base), plus the uncommitted changes.
  A stale summary is now detectable without re-reading the branch. The summary stays navigation, never evidence.
- **Workflow agents carry the human's authorization** (`agent-fleet` §2, the `authorization` arg of
  [`rolling-wave.js`](skills/agent-fleet/references/rolling-wave.js), and the brief template's first section). A
  workflow agent takes the session's latest user message as its request, so a fleet launched in a later turn
  quotes the human's direction verbatim in every prompt, or its agents decline the work.
- **Liveness is judged by processes and the journal, not transcript file times** (`agent-fleet` §5). A watchdog
  keyed on transcript modification time called a working fleet dead. (The reason given here at first, that
  transcripts are written lazily, was wrong; 1.8.1 states the two measured causes.)
- Workflow scripts stay LF-only: a Workflow tool refused a CRLF script as containing hidden control characters.

## What's new in 1.6.0

- **The fix lane is a rolling wave** (`agent-fleet` §6, [`rolling-wave.js`](skills/agent-fleet/references/rolling-wave.js)).
  Implementers pull groups from one queue, so a freed slot refills the moment its agent returns, and lander trains
  start as soon as enough branches are ready. There's no "wave, then train" barrier where finished slots wait for the
  slowest group.
- **Same-file successors** (`agent-fleet` §7). When a file has more open defects than one cluster holds, the next
  cluster runs after the first, merges its branch, and orients from its handoff notes instead of re-reading the file.
  The first branch lands through the second. Orientation was about half of every implementer's tokens, so a file's
  context is now paid once. The successor is a fresh agent, because cost grows with the square of a transcript's turns.

## What's new in 1.5.0

- **The model follows the role** (`agent-fleet` §11, `automating-agent-guardrails` §2). Judgment roles run the top
  everyday tier. Mechanical roles run a cheaper one, and there's a new read-only mechanical role template,
  [`locator.md`](skills/automating-agent-guardrails/templates/agents/locator.md), for code-site lookups and
  measurements. Never pass a model per call: it overrides the role's own.
- **A premium model is an exception, not a lane.** On plans where a premium model draws the regular weekly limit
  faster, and its usage-page row is only a ceiling on its share, it is never free capacity.
- `fix_clusters.py` takes several extensions (`--ext .cs,.g4`) and counts bare file names as code sites.

## What's new in 1.4.0

Four changes to how a fleet of agents fixes defects, each measured on a live campaign:

- **Fix groups are computed** (`agent-fleet` §7, [`fix_clusters.py`](skills/agent-fleet/references/fix_clusters.py)).
  Open defects cluster by the source file their code sites name, so one implementer fixes all of one file's
  defects in one pass. 411 open defects became 125 clusters, so a six-agent wave carries ~25–30 fixes instead of ~10.
- **Orientation is one call** (`agent-fleet` §2, [`orient.py`](skills/agent-fleet/references/orient.py)). Before
  reading any source, an implementer gets each file's outline, the tests that cover it and what earlier fixes
  learned about it, all derived fresh from the tree, the notes and git. Reads and searches were 63 % of implementer
  tool calls; the estimate is ~15 % fewer tokens per implementer.
- **No command chained after a build or test** (`agent-fleet` §1, `test-gate`), enforced by a new guard rule,
  `no-chain-after-verdict` (`automating-agent-guardrails`). A chain's exit status is its last command's, so
  `npm test && git push` acts on a verdict nobody read. It's deliberately not a blanket chaining ban: independent
  commands go as parallel tool calls in one turn, because extra turns are the quadratic cost.
- **Two new regression evals** (`agent-fleet-file-clusters`, `agent-fleet-orientation`) prove the skill changes
  what Claude does.

## How skills work

A **skill** is a folder with a `SKILL.md`: YAML frontmatter (a `name` and a `description` of when to use it) followed by
instructions written *to Claude*. Claude Code reads every installed skill's description; when a task matches one, it
loads the full instructions and follows them — you don't have to invoke anything. You can also ask for a skill by name
("run the review skill"), or type `/` in Claude Code to pick it from the list of available skills. Supporting files
live beside it in `references/` — templates, checklists and small scripts the instructions call.

Every skill folder here also has a **`README.md` written for people**: what the skill does, how it runs, and — most
importantly — *why* each rule exists, since every rule traces back to a failure it prevents. Start there; the
`SKILL.md` holds the complete rules.

An **agent** in `agents/` is a subagent definition — a markdown file whose frontmatter names the agent, says when to
use it and which tools it may use. Claude can launch one as a focused, independent reviewer.

## Skills

**The bar**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`engineering-standards`](skills/engineering-standards/) | writing, changing, designing or reviewing production code | Commercial-grade, decades-maintainable code. No god classes; one mechanism per job; one rule in one place; fix the root cause, never paper over; **every bug is a pattern**; implement the complete feature (tests verify, they don't scope); re-architect when the right structure demands it, even if the build breaks on the way. |

**Finding defects**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`review`](skills/review/) | reviewing a diff, branch or PR | Four dimensions (architecture · full code · performance · duplication/efficiency) as parallel reviewers, plus specialist agents; every finding carries a concrete failure scenario; an adversarial skeptic tries to refute each one; confirmed bugs trigger a sibling sweep. |
| [`variant-analysis`](skills/variant-analysis/) | right after any defect is confirmed | Name the mechanism, not the symptom; textual, structural (Roslyn, ANTLR, tree-sitter, Semgrep) and semantic queries; "which arm of the dispatch did you fix?"; a probe per candidate; a sweep report in which zero hits is evidence. |

**Specs and standards**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`spec-oracle`](skills/spec-oracle/) | behavior is governed by a written standard (language standards, RFCs, file formats, ECMA-335 …) | The spec is the only oracle; derive the expected result *before* reading the code; every citation checked mechanically. Includes a small generic citation checker. |
| [`spec-compliance-audit`](skills/spec-compliance-audit/) | auditing a whole implementation against a whole standard | A rule catalog, one agent per rule/subject, a verdict vocabulary, refuters on every closing verdict, a traceability inventory whose GAP count is the progress metric. |

**Testing and .NET**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`test-gate`](skills/test-gate/) | before every commit, merge or push | Tiered gates; read the verdict line, not the exit code; filters that silently match nothing; confirm new tests actually ran; CI for the exact pushed commit is the final word. |
| [`dotnet-engineering`](skills/dotnet-engineering/) | .NET / C# work | Latest .NET and C#, strong types, warnings as errors; `dotnet test` filter traps; test gaps and smells; BenchmarkDotNet with a witness; binlog failure analysis; trimming/Native AOT; NuGet trusted publishing. |
| [`roslyn-analysis`](skills/roslyn-analysis/) | C# duplication review, sibling sweeps, mechanical refactors, verifying built assemblies | Structural clone detection, symbol sweeps (every implementation/override/reference), a safe rewriter harness (dry-run, preserves encoding and line endings, refuses unparseable output), metadata-only assembly and IL inspection. |

**Running agents at scale**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`agent-fleet`](skills/agent-fleet/) | dispatching many parallel subagents on a long campaign | One self-contained input per agent; checkpoint to disk; fresh agents from checkpoints; concurrency and token budgets; land finished work first; adversarial refuters; cost per unit decides the lane. |
| [`claude-cloud-sessions`](skills/claude-cloud-sessions/) | running work in Claude Code cloud sessions | Environment setup scripts and snapshots; multi-repo sessions and hooks; private-repo access; launch surfaces and **billing** (measured, including where it differs from the docs); stopping cleanly before a credit runs out. Includes a setup-script template. |
| [`automating-agent-guardrails`](skills/automating-agent-guardrails/) | agents keep breaking a project's rules, or when setting up guard hooks, role agents, a session-start readiness check, cost telemetry or LSP navigation | Guard hooks on every shell tool that fail open, are scoped to the repo and prove each rule with a self-test in CI; role definitions with model, effort, turn cap, 1-hour cache and read-only hooks in the role itself, proven by a smoke dispatch after restart; a readiness check every session (OK / REPAIRED / N/A / TODO / ASK-OWNER) where anything needing your permission becomes a question; local per-agent cost telemetry. Includes the scripts and templates. |

**Project memory**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`devlog`](skills/devlog/) | keeping a development log, work history or fix log that agents write and read; recording a failed or overturned approach; checking whether something was tried before | Three forms by purpose (working history, defect/fix log, published narrative); an entry with every change; timestamps from the clock; corrections as new entries, never rewrites; failures kept; only the log is historical. Agents search it before retrying instead of reading it at session start; consolidation yields candidate learnings, and only those an adversarial validation vets enter the learnings file or a skill. Includes an entry script (both layouts, line endings kept), a commit hook and the templates. |

`engineering-standards` is the bar every other skill applies in its own context — each has a short *Standards*
section saying how.

## Agents

Specialist reviewers the `review` skill adds when a change calls for them:
[`silent-failure-hunter`](agents/silent-failure-hunter.md) (swallowed errors, fallbacks, silent wrong answers),
[`pr-test-analyzer`](agents/pr-test-analyzer.md) (scope, oracle, discovery and strength of tests),
[`type-design-analyzer`](agents/type-design-analyzer.md) (god classes, stringly-typed state, illegal states),
[`comment-analyzer`](agents/comment-analyzer.md) (comments whose claims or citations don't hold).

## How the skills fit together

- **`engineering-standards` is the bar.** Every other skill applies it in its own domain (each has a short *Standards*
  section saying how).
- **Before building against a standard:** `spec-oracle` derives the expected behavior and checks the citation first;
  `spec-compliance-audit` scales that to a whole implementation against a whole standard, using the same citation
  checker and the refuter pattern from `agent-fleet`.
- **Changing code:** `test-gate` picks and reads the right gate before each commit and push; `dotnet-engineering` adds
  the .NET-specific bar; `engineering-standards`' `rule_index.py` lists the structural rules that govern a file before
  you edit it.
- **Reviewing:** `review` runs the four dimensions with the specialist `agents/`; a confirmed defect hands off to
  `variant-analysis`, which sweeps for its siblings (using `roslyn-analysis` for compiler-accurate C# queries).
- **At scale:** `agent-fleet` runs many agents on a long campaign without losing work to limits, and
  `claude-cloud-sessions` covers running that work in Claude Code cloud sessions. `automating-agent-guardrails` turns
  the rules those agents must follow into hooks and role definitions, and checks at every session start that they
  are in force.
- **Remembering:** `devlog` keeps what every change tried and learned, so the next session starts from it instead of
  repeating it; its consolidation brief turns the log into candidate learnings, and its validation brief admits only
  the vetted ones to a learnings file or a skill.

## Adapting to your project

Most skills end with **Project hooks** (and each skill's README says what a project can supply): your repo's `CLAUDE.md` supplies its commands, tightens or adds rules,
and wins on conflict — no fork needed. For example, a `## Review rules` block can add a spec-conformance reviewer,
and a `## Testing` section records gate commands and baseline counts.

## Regression evals

[`evals/`](evals/README.md) is a `claude plugin eval` suite with one to four cases per skill and one per agent. Each
case runs with the plugin and with no plugin at all, and it is kept only if the plugin arm scores higher. That makes
it a regression test: a skill edit that stops changing Claude's behavior shows up as a shrinking Δ. To run it:
`claude plugin eval . -j 4 --no-publish --threshold 0`. A skill change ships with its eval; see the
[evals README](evals/README.md) for the rule, how to read the delta, and the cases dropped because Claude already
passed them without the plugin.

## Credits and licenses

This repository is MIT-licensed ([LICENSE](LICENSE)) **except** where a directory says otherwise:

| Path | Adapted from | License |
|---|---|---|
| `skills/spec-compliance-audit/`, `skills/variant-analysis/` | [trailofbits/skills](https://github.com/trailofbits/skills) | **CC-BY-SA 4.0** — the `LICENSE` in each directory covers it; adaptations stay share-alike |
| `agents/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) `pr-review-toolkit` | Apache-2.0 — see [NOTICE](NOTICE) and [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| `skills/dotnet-engineering/` | [dotnet/skills](https://github.com/dotnet/skills) | MIT — see its `references/THIRD-PARTY-NOTICES.md` |
| `skills/roslyn-analysis/` | [glennawatson/CSharpAgentSkills](https://github.com/glennawatson/CSharpAgentSkills) (approach; helper code rewritten after vetting) | MIT — see its `references/THIRD-PARTY-NOTICES.md` |

The review skill's triage step and two-axis (scale × consequence) calibration come from
[carlymr/carlys-claude-skills](https://github.com/carlymr/carlys-claude-skills).
