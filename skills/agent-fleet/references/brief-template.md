# Dispatch brief template

Render one copy per agent into `{SCRATCH}/briefs/<wave>-<slug>.md` with a script. Don't hand-edit copies, and
don't paste the brief into the prompt. The prompt is one line: *"Read and follow `{SCRATCH}/briefs/<file>`."*

---

## Role
{implementer | analyst | refuter | lander} for **{slug}** (wave {wave}).

## Your input (this slice only, nothing else)
{the items, embedded, or the path of a file that holds ONLY this agent's slice}

## Contract (apply-ready; start here, don't re-survey)
- Code sites: {file:line, ...}
- Repro: {exact command + expected vs actual}
- Governing rule / authority: {verified citation}
- Gate: `{narrow gate command}` (low priority; never the whole suite unless you are the lander)

## The bar (what makes your output WORTHLESS even if it is well-formed)
{e.g. "expected values must be derived from the spec, never copied from another implementation's output"}

## Allocated to you (never mint your own)
- ids: {range} · codes: {range} · report path: `{SCRATCH}/reports/<wave>-<slug>-report.md`

## Checkpoint protocol
- Worktree agents: after each mechanism and each gate, run `git commit -m "WIP checkpoint: ..."` and update
  `STATUS.md` (DONE / NEXT / BLOCKED / GATE / ids used). Never `git stash`.
- Workflow stages: append one JSON line per decided item to `{OUT}/<stage>-<slug>.jsonl` immediately. On start,
  read the file and skip the items it already holds. Write the final result to `{OUT}/out-<slug>.json`.

## Stop rules
- Before each new step, check for `{SCRATCH}/STOP`. If it exists: checkpoint, write STATUS.md NEXT, and return
  status `SPLIT`. Don't start a build or gate once STOP exists.
- Turn cap: {160 read-only | 220 implementer}. At the cap: checkpoint and return `SPLIT` with NEXT filled in.
  Never extend.
- Never end your turn while your own background job runs. Log it, then block on
  `timeout 580 bash -c 'tail -n +1 -f <log> | grep -m1 "<verdict>"'` until the verdict prints.

## Ground rules
- Write only inside your worktree or `{SCRATCH}`. Never write in the repo root of the shared checkout.
- Every lead you report carries its repro and code site (file:line).

## Report (60 lines or fewer, at the allocated path)
Status (DONE / SPLIT / BLOCKED) · one section per item: what changed, the root cause, and the evidence (gate
verdict line) · leads found (with repro + code site) · NEXT if split.
