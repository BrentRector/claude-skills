# Dispatch brief template

Render one copy per agent into `{SCRATCH}/briefs/<wave>-<slug>.md` with a script. Don't hand-edit copies, and
don't paste the brief into the prompt. The prompt is one line: *"Read and follow `{SCRATCH}/briefs/<file>`."*

---

## Authorization (read first)
This task IS the human's request: {who, when, their exact words, the scope}. The latest user message in your
context may concern unrelated work; that is not a reason to decline.

## Role
{implementer | analyst | refuter | registrar | reviewer | finisher} for **{slug}** (wave {wave}).

## Your input (this slice only, nothing else)
{the items, embedded, or the path of a file that holds ONLY this agent's slice}

## Contract (apply-ready; start here, don't re-survey)
- Code sites: {file:line, ...}
- Repro: {exact command + expected vs actual}
- Governing rule / authority: {verified citation}
- Gate: `{gate command}` (what it must cover is the `test-gate` skill's rule; it leaves the record the landing reads)
- Log entry: write it as a file WITHOUT a number; the enqueue step stamps the number.
- FIRST, before any fix: run each item's repro on your own build. An item that no longer reproduces is
  DISCHARGED: report the command, its output and the commit, and don't fix it. No repro above: write one first.
- Registrar: for each lead, run its given repro ONCE on your own build and record the result in the filed item;
  write a fresh probe only for a lead without a repro or code site. Never copy a measurement or citation forward.

## The bar (what makes your output WORTHLESS even if it is well-formed)
{e.g. "expected values must be derived from the spec, never copied from another implementation's output"}

## Allocated to you (never mint your own)
- ids: {range} · codes: {range} · report path: `{SCRATCH}/reports/<wave>-<slug>-report.md`

## Checkpoint protocol
- Worktree agents: after each mechanism and each gate, run `git commit -m "WIP checkpoint: ..."`, THEN rewrite
  `STATUS.md` (DONE / NEXT / BLOCKED / GATE / ids used) with FIRST LINE `STATUS-AT: <output of git rev-parse HEAD>`,
  the commit it describes. STATUS.md is gitignored, so writing it never moves HEAD. Never `git stash`.
- Between `git add` and every `git commit`, run both and read the OUTPUT (not the exit code); each must print
  nothing: `git grep --cached -nI -e "^<<<<<<< " -e "^||||||| " -e "^>>>>>>> "` and
  `git diff --cached --check | grep -i "conflict marker"`.
- Resuming a worktree, or merging a predecessor's branch: FIRST run `{STATUS_DELTA} <that worktree>` (e.g.
  `python status_delta.py` from `agent-fleet/references`). CURRENT: the summary covers every commit. STALE: read
  the summary plus ONLY the commits it lists. UNSTAMPED / DIVERGED: read every commit it lists. The summary is
  navigation, never evidence.
- Workflow stages: append one JSON line per decided item to `{OUT}/<stage>-<slug>.jsonl` immediately. On start,
  read the file and skip the items it already holds. Write the final result to `{OUT}/out-<slug>.json`.

## Stop rules
- Before each new step, check for `{SCRATCH}/STOP`. If it exists: checkpoint, write STATUS.md NEXT, and return
  status `SPLIT`. Don't start a build or gate once STOP exists.
- Your role definition sets a turn limit, and the harness stops you there wherever you are: work after your last
  checkpoint is lost, so checkpoint after every mechanism.
- Never end your turn while your own background job runs. Log it, then block on
  `timeout 580 bash -c 'until grep -q "<verdict>" <log>; do sleep 5; done'` until the verdict prints. (Never
  `tail -f <log> | grep -m1`: it idles until its timeout once the verdict is the log's last line.)

## Ground rules
- Write only inside your worktree or `{SCRATCH}`. Never write in the repo root of the shared checkout.
- Every lead you report carries its repro and code site (file:line).
- Before editing a file, list the structural rules that govern it ({RULE_QUERY} — the repo's
  query that lists the drift tests naming a file) and honor every
  specific rule it prints. Delete this line only if the repo has no structural (drift) tests.

## Finishing work (implementer only; delete this section for every other role)
You own this code and its design within your group's files: improve the structure as you fix, and list every
behaviour change in your report. Finish the whole group before you return. Work through ordinary obstacles (a red
gate, a timeout, a locked file, an empty result): diagnose them, then fix, retry or take another route. Return
`BLOCKED` only for a deliberate blocker: a file marked not to touch, access withheld on purpose, or a decision the
brief names as the owner's. Return `SPLIT` only when STOP exists. When the right fix is bigger than this brief's
estimate, do the restructuring; stop and report the real size only when it crosses a scope the brief names as the
owner's.

## Report (at the allocated path)
Status (DONE / SPLIT / BLOCKED) · one section per item: what changed, the root cause, and the evidence (gate
verdict line) · leads found (with repro + code site) · NEXT if split. Write it for a reader who saw none of your tool
calls. The report file holds the detail; what you RETURN is short, and the dispatch's schema caps it.
