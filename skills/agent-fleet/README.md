# agent-fleet

Running many parallel Claude subagents on a long engineering campaign fails in predictable ways. The session
window closes and kills every live agent at once, so hours of work held only in transcripts disappear. A restart
repeats work that was already decided. And the token budget goes to long, expensive transcripts instead of to the
work that moves the result. This skill is a set of orchestration rules that make a fleet **restart-safe** (a kill
costs at most one step, a restart never repeats work) and **budget-aware** (tokens are spent where they move the
metric you report).

The full rules are in [`SKILL.md`](SKILL.md). This page explains what they are and why they exist.

## When Claude uses it

The skill's description tells Claude to load it **before dispatching more than a couple of parallel subagents or a
multi-agent workflow** on a long-running campaign. Skills load automatically when the description matches the
task, so asking Claude to "fan this out across agents", "run a fleet over these items" or "dispatch implementers
for these fixes" is usually enough. You can also name it explicitly ("use the agent-fleet skill").

## What it does

The skill splits the work into roles. The **orchestrator** (your own session) plans, dispatches, reconciles,
gates and commits. Every other job (probe, implement, validate, adversarial review, land) is a subagent. The
orchestrator keeps its own transcript short: briefs and reports are files, and the conversation carries only
their paths.

A campaign run under the skill looks like this:

1. **Write one brief per agent** from [`references/brief-template.md`](references/brief-template.md), rendered by
   a script into `{SCRATCH}/briefs/<wave>-<slug>.md`. Each brief holds only that agent's slice, an apply-ready
   contract (code sites, repro, governing rule, gate command), the "worthless even if well-formed" bar, and the
   ids allocated to it. The agent's prompt is a single line: *"Read and follow `{SCRATCH}/briefs/<file>`."*
   The brief's first instruction is to orient with [`references/orient.py`](references/orient.py) on the files
   its items name, before reading any source. Then the implementer re-runs each item's repro on its own build;
   an item that no longer reproduces is discharged with the evidence instead of fixed.
2. **Dispatch within the concurrency budget**: by default 1 lander, a handful of implementers (~3–6) and one
   read-only chunk about 4 wide. Each implementer gets a *group* of related items (same files or rule family),
   and parallel slots get one group per subsystem. The groups are computed, not hand-picked:
   [`references/fix_clusters.py`](references/fix_clusters.py) clusters open defects by the source file their
   code sites name, so every defect in one file is fixed in one pass.
3. **Agents checkpoint after every unit**: after staging and before every commit they assert, on the output of
   `git grep --cached` and `git diff --cached --check`, that no conflict marker is staged; implementers make a WIP
   commit and then rewrite `STATUS.md` (`DONE` / `NEXT` / `BLOCKED` / `GATE` / ids used), whose first line `STATUS-AT: <sha>` names the commit it
   describes; workflow stages append one JSON line per decided item and skip items already on disk when they start.
   An agent that resumes a worktree or merges a predecessor runs
   [`references/status_delta.py`](references/status_delta.py) first, which prints exactly the commits the summary
   does not cover.
4. **Agents obey the stop rules**: a hard turn cap per role (e.g. ~160 read-only, ~220 implementer), a graceful
   `{SCRATCH}/STOP` file checked before every step, and never ending a turn while their own background gate runs.
5. **Reconcile the returns** against the expected worklist (missing, duplicated, extra) and re-run only the gaps.
6. **Send closing verdicts to adversarial refuters**, small independent agents told to overturn the claim.
7. **Land finished work first**: one lander on main at a time, 4–6 finished clusters per landing with one commit
   each, gated on the whole unfiltered test suite, then watch CI for the pushed head. The comprehensive battery
   runs in its own detached worktree at the batch head, so landings go on while it runs.
8. **After the fleet**, run `git status --short` and account for every unexpected path before staging.

On restart after a cutoff, the skill's recovery procedure is: read the reset time from the limit message, check
the dead lander's worktree (confirm the steps it finished, redo a half-done one, never re-apply a finished one), run
`status_delta.py` on each worktree,
and dispatch **fresh** agents from the checkpoints in landing order. Before calling a background workflow dead,
check its run status and journal and its agents' processes and worktrees. Transcript file times are not a signal:
a tool call writes nothing to a transcript until it returns, and restarting the orchestrating session moves live
agents' transcripts to the new session's directory.

A fleet launched in a later turn than your request carries that request, quoted verbatim, at the top of every
agent prompt (the `authorization` arg of [`rolling-wave.js`](references/rolling-wave.js), or the brief's first
section).

### The brief template

[`references/brief-template.md`](references/brief-template.md) is a copy-and-fill dispatch brief. Its sections are:

| Section | What you fill in |
|---|---|
| Authorization | who directed this work, when, their exact words and the scope, so an agent never declines it for lack of a visible request |
| Role | implementer, analyst, refuter, registrar or lander, plus the slug and wave |
| Your input | the items for this agent only, embedded or as a path to a file holding only this slice |
| Contract | code sites (`file:line`), exact repro, verified governing rule, narrow gate command; the implementer re-runs each repro first and DISCHARGES, with evidence, an item that no longer reproduces; a registrar runs each lead's repro once before filing it; the comprehensive battery runs in a detached worktree |
| The bar | what would make the output worthless even though it is well-formed |
| Allocated to you | id ranges, code ranges, the report path — agents never mint their own |
| Checkpoint protocol | a staged-output conflict-marker assertion before every commit; WIP commits + a stamped `STATUS.md` (`STATUS-AT: <sha>`) for worktree agents, and `status_delta.py` first when resuming or merging a predecessor; JSONL-per-item for workflow stages |
| Stop rules | the STOP file, the turn cap, and blocking on background jobs with `timeout 580 bash -c 'tail -n +1 -f <log> \| grep -m1 "<verdict>"'` |
| Ground rules | write only in your worktree or scratch; every reported lead carries repro and code site |
| Report | 60 lines or fewer: status, one section per item, leads, NEXT if split |

Render copies with a script rather than by hand, and point each agent at its rendered copy instead of pasting it.

## Why it works this way

Every rule in the skill carries its own *Why*. The main ones:

| Rule | The failure it prevents |
|---|---|
| Hard turn caps; split a job, never extend it | An agent re-reads its whole context every turn, so cost grows roughly quadratically with turns. In one measured campaign, the ~8 % of agents that ran 250+ turns burned ~39 % of all tokens. A fresh agent from a checkpoint pays the cheap early-turn cost. *(Practice — not yet validated: the curve was refit on a newer model with different coefficients, and the saving from splitting, net of the successor's orientation, was never measured.)* |
| One self-contained input file per agent | Agents miscount indices into a shared list: one fan-out double-processed four items and skipped five. *(Validated 2026-09-28.)* |
| Point agents at a brief file, not a pasted prompt | A file can be re-read after a restart; a prompt dies with its transcript. *(Practice — not yet validated: the rule lapsed for about two months until a checker enforced it.)* |
| Apply-ready contracts for implementers | Search and read turns are the largest share of implementer tokens; rediscovering a subsystem costs more than fixing it. *(Practice — not yet validated: no like-for-like cost per item before and after.)* |
| Re-run each item's repro before fixing it; discharge what no longer reproduces | A backlog item's word is not evidence. Re-probing 331 known-bad items judged before several fix waves landed found 114 already fixed, and refuters overturned 20 of the probers' own claims. *(Validated 2026-09-28.)* |
| A registrar runs each lead's given repro once before filing it | A registrar that copies a report's measurement forward is a second place for its mistakes to live. Across six registrar passes, forwarded leads repeatedly failed the re-run (three of 52 in one pass), and a quoted citation proved to be a paraphrase. Running the given repro once, and probing fresh only without one, replaced re-probing every lead three times over. *(Validated 2026-09-28.)* |
| Only verified facts in a brief | Agents inherit a confident wrong citation and carry it into code. *(Validated 2026-09-28.)* |
| State the bar, not just the format | Agents optimize the criterion you wrote down; a shape validator passes worthless-but-valid work. *(Validated 2026-09-28.)* |
| Checkpoint to disk after every unit | Un-checkpointed refuters lost 100 % of their decisions to a single session kill. *(Practice — not yet validated: a reliable checkpoint is not yet shown: 3 of 14 finished branches still ended with a stale `STATUS.md`.)* |
| Stamp the handoff (`STATUS-AT: <sha>`, read with `status_delta.py`) | An agent killed between its commit and its summary leaves a summary that silently omits the last commits. Without a stamp, a successor can't tell stale from current and must re-read the whole branch every time. Measured (88 resumers, 22 scenarios): coverage misjudged in 11 of 44 resumes without the stamp, 0 of 44 with it; tokens −17 % overall, −31 % when the summary was current. *(Practice — not yet validated: a controlled A/B on 11 branches; resume accuracy in production is not yet measured.)* |
| A workflow's prompts carry the human's authorization verbatim | A workflow agent takes the session's latest user message as its request. A fleet launched in a turn whose latest message was about something else had 7 of its 10 implementers decline and return BLOCKED. *(Practice — not yet validated: one exercise under an unrelated message since, and the first before/after run was confounded.)* |
| Judge a workflow's liveness by its processes and journal | A tool call writes nothing to the transcript until it returns, so every long gate wait is a ~580-second silence (measured: 5–7 silences over 120 s per agent in one run, the longest ~585 s). And clearing or restarting the orchestrating session moves live agents' transcripts to the new session's directory while the journal stays in the old one; a watchdog reading the old directory saw 20+ minutes of silence for that reason and called a healthy fleet dead. A transcript ending on an unanswered tool call is live for up to that tool's maximum duration. *(Practice — not yet validated: not yet exercised across several waves.)* |
| Assert on conflict markers between `git add` and `git commit`, by output | Four unresolved hunks in a script no test imports passed three green gates. `--check` flags every line of a CRLF file, so the rule reads the output, not the exit code. Since the repo-wide marker test was adopted, no marker has reached main. *(Validated 2026-09-28.)* |
| Never `git stash` (including `--autostash`) | The stash stack is shared by every linked worktree, so one agent's `stash pop` can take another's work. *(Practice — not yet validated: one near-miss recorded; no loss yet traced to the shared stack.)* |
| Concurrency budget and a token tally | ~28 concurrent agents burned ~20 % of a window in 11 minutes; ~50 exhausted a window in ~2.5 h. The limit kills landers mid-landing. *(Practice — not yet validated: no evidence the tally, rather than the real usage meter and the STOP file, prevented a kill.)* |
| Graceful STOP file | Workflow agents can't be messaged, and a hard kill lands mid-step. *(Validated 2026-09-28.)* |
| Land finished work first; batch 4–6 clusters | Ready work once sat behind a serialized lander when the limit hit. A landing is mostly fixed cost, so per-cluster cost roughly halves from 1 to 5 clusters. *(Practice — not yet validated: the saving is modelled, not measured.)* |
| The lander gates the whole suite | The tests no implementer's filter names are exactly the ones that go red in CI. *(Validated 2026-09-28.)* |
| The comprehensive battery runs in its own detached worktree | It rebuilds mid-run: on the shared checkout one measured a half-finished edit and nothing could land for its ~45 min (the blocked work was modelled at about seven clusters, not measured). From the first worktree battery on, landings continued in parallel, though slower while it shares the cores. *(Validated 2026-09-28.)* |
| Group related fixes per implementer | Separate implementers on the same files produced merge conflicts and composition defects neither could see. *(Practice — not yet validated: no before/after measure of conflicts per train.)* |
| Compute the groups by file (`fix_clusters.py`) | Hand-picked groups carried 1–3 items and split one file's defects across implementers; computed per-file clusters turned 411 open defects into 125 groups, so a six-slot wave carries ~25–30 fixes instead of ~10. *(Practice — not yet validated: no before/after measure of fixes landed per wave.)* |
| A rolling wave (`rolling-wave.js`), not "N implementers, then one train" | Under a wave barrier every finished slot waits for the slowest group; a queue refills a slot the moment its agent returns, and trains start as branches finish. *(Filling a freed slot at once: validated 2026-09-28. The rolling-wave script: practice, not yet validated: no A/B against the barrier.)* |
| Same-file successors for a file with more defects than one cluster holds | Orientation was about half of every implementer's tokens. Two independent groups on one file pay it twice; a successor merges the first branch and starts from its handoff notes. It is a fresh agent because cost grows with the square of a transcript's turns. *(Practice — not yet validated: no A/B against independent groups.)* |
| One-call orientation (`orient.py`) before reading source | Across 7 implementer transcripts, 63 % of tool calls were reads/searches and 15 % of turns came before the first edit, re-deriving what earlier fixes had learned. Cutting ~25 of ~200 turns saves ~15 % of an implementer's tokens. *(Practice — not yet validated: the ~15 % is an estimate, not yet measured.)* |
| Never chain after a build/test verdict; parallel calls instead of a chaining ban | A chain's exit status is its last command's, so `test && git commit` commits on an unread verdict. A blanket ban adds turns, which are the quadratic cost. *(The verdict rule: validated 2026-09-28. The targeted form: practice, not yet validated.)* |
| The model follows the role, never a per-call model | A per-call model overrides the role's frontmatter: "top model on every agent" ran the cheap chore role on the top tier, and a 30-lookup code-site pass ran on the top-tier analyst. *(Practice — not yet validated: the cost of the override was never measured.)* |
| A premium model is a per-item escalation, not a lane | Where it draws the same weekly pool faster, and its usage row is only a ceiling on its share, a premium lane buys similar results for more quota. *(Practice — not yet validated: the premium model's draw per unit was never measured.)* |
| Central id allocation | Five id collisions in one day each cost a renumbering pass; parallel landers overwrote each other's reports. *(Practice — not yet validated: collisions recurred whenever a second allocator existed.)* |
| Pinned read-only worktree; frozen tree during a fleet | A landing that rebuilds the main tree swaps binaries under running probes. *(Practice — not yet validated: its effect on contaminated results was never measured.)* |
| Never poll a fleet's output directory | An adversarial stage 2 only removes confidence, so an early read is biased upward. One early merge moved 10 of 55 results. *(Validated 2026-09-28.)* |
| Adversarial refuters on closing verdicts | The first agent's framing is contagious; only an agent hunting a counter-example finds the well-formed-but-wrong result. *(Validated 2026-09-28.)* |
| Verdicts keyed on (claim, evidence) | Pooling overturns by claim dropped valid evidence and recorded evidence nobody judged. *(Practice — not yet validated: not yet exercised on later batches.)* |
| Measure cost per unit per lane | Cost per unit can differ by ~10× across lanes; a large review fleet can burn billions of tokens for single-digit movement. *(Practice — not yet validated: tokens per closed item are not yet measured the same way for each lane.)* |
| `git status` before `git add -A` | Agents drop files into the repo root despite scratch-only rules; the prompt constrains intent, not effects. *(Practice — not yet validated: no recorded catch.)* |

## Using it in your project

- **Your project's rules.** The skill tells every implementer brief to name the project's own rules alongside the
  quality bar, and the brief template leaves the gate commands, id ranges and paths as placeholders for you to
  fill. The repo-wide convention (see the [top-level README](../../README.md#adapting-to-your-project)) is that your
  `CLAUDE.md` supplies commands and tightens rules, and wins on conflict.
- **The two dispatch tools.** Both read a directory of issue notes, one Markdown file per item with front matter
  (`id`, `status`, harm flags such as `wrong_answer: true`), and both write nothing into your tree:
  ```
  python references/fix_clusters.py --notes docs/issues --src src --ext .cs --json clusters.json
  python references/orient.py src/Parser/Lexer.cs --notes docs/issues --tests tests --cite "RFC\s?\d+"
  ```
  `fix_clusters.py` picks what each implementer gets: one cluster of co-located defects per slot, the
  highest-harm cluster first. `orient.py` is the first line of each implementer's brief. Its LEARNED section is
  only as good as your closed notes, so have every fix record its code site and mechanism in the note.
- **Configure once, not at every call site.** Put your settings in a `.agent-fleet.json` at the repository root
  and every brief can say just `python <path>/orient.py <files>`. The three scripts find it by walking up from the
  current directory; explicit flags override it, and a key no script accepts is an error. The keys are the long
  flag names with underscores; path keys are relative to the file:
  ```json
  {
    "notes": "docs/issues", "notes_glob": "*.md", "tests": "tests", "test_ext": ".cs",
    "cite": "(?P<key>RFC\\s?\\d+)(?:\\s+section\\s+\\d+)?", "closed_status": "done,fixed", "min_name": 7,
    "src": ["src/App.*"], "ext": ".cs,.g4", "exclude_dir": ["Generated"],
    "harm": "wrong_answer=8,crashes=4", "kind": "defect", "skip_flag": ["blocked"],
    "base": "origin/main", "exclude": [".local-settings.json"]
  }
  ```
  A named group `key` in `cite` counts references per key and lists each key's refinements
  (`RFC9110×12 (section 8×5, …)`); without one, each distinct match counts separately.
  [`fleet_config.py`](references/fleet_config.py) documents every key.
- **Consume the plugin rather than copying it.** A repository can pin this repository as a git submodule, enable
  the plugin from the submodule in its project settings, and call the scripts at their submodule paths, so
  improvements arrive by moving the pin and the project keeps only its configuration and its overlays.
- **Prerequisites.** Git with worktree support (implementers and pinned analysis probes each use a worktree),
  a subagent or workflow tool, and a shell that can run `timeout`, `tail` and `grep` for the blocking-gate pattern.
- **Composes with:**
  - [`engineering-standards`](../engineering-standards/SKILL.md) — the quality bar every implementer brief must
    carry. Briefs also tell implementers to run that skill's rule query for the files they will touch
    (`engineering-standards/references/rule_index.py --tests "<glob>" <files>`, or the repo's own) before editing.
  - [`test-gate`](../test-gate/SKILL.md) — how implementers and the lander choose and read their gates.
  - [`review`](../review/SKILL.md) and [`spec-compliance-audit`](../spec-compliance-audit/SKILL.md) — fleets whose
    closing verdicts go through the refuter step described here.
  - [`claude-cloud-sessions`](../claude-cloud-sessions/SKILL.md) — the same restart-safety rules applied to fleets
    running on cloud VMs.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The rules Claude follows, each with its reason |
| [`references/brief-template.md`](references/brief-template.md) | Copy-and-fill dispatch brief carrying the checkpoint, STOP, turn-cap, blocking-gate and report rules |
| [`references/fix_clusters.py`](references/fix_clusters.py) | Groups open defect notes by the source files their code sites name, ranked by summed harm, so each implementer fixes one file's defects in one pass |
| [`references/rolling-wave.js`](references/rolling-wave.js) | Reference Workflow script for the fix lane: a rolling pool of implementers over a queue of groups, same-file successors (`after`) that inherit their predecessor's branch and handoff notes, and serialized lander trains started as branches finish. Agent types, spec paths, stop file, landing command and the human's verbatim `authorization` are args |
| [`references/status_delta.py`](references/status_delta.py) | Reads a worktree's stamped `STATUS.md` against its branch and prints CURRENT, STALE by N (with only those commits), or UNSTAMPED / DIVERGED (with every commit since the base), plus the uncommitted changes |
| [`references/stall_watch.py`](references/stall_watch.py) | Background watchdog for a running workflow: exits the moment a pending agent has been silent more than 10 min waiting on the model or 12 min inside one tool call (thresholds measured over 150 transcripts), naming the agent and its last action |
| [`references/orient.py`](references/orient.py) | One-call orientation for the files an implementer will change: outline with line numbers, cited spec references, covering tests, what closed notes learned about each file, open notes naming it, recent commits |
| [`references/fleet_config.py`](references/fleet_config.py) | Finds and validates the repository's optional `.agent-fleet.json`, the one place the three scripts' settings live |
| `README.md` | This page |
