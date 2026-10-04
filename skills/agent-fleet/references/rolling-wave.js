export const meta = {
  name: 'rolling-wave',
  description: 'Rolling fix lane: implementer groups run N at a time from one queue (a freed slot refills at once), same-file successors inherit their predecessor\'s branch, and lander trains start as branches finish',
  whenToUse: 'The standard fix-lane dispatch for an agent fleet (agent-fleet references/landing.md and references/grouping-fixes.md).',
  phases: [
    { title: 'Implement', detail: 'one implementer per group, isolated worktrees, rolling pool' },
    { title: 'Land', detail: 'serialized lander trains over ready branches' },
  ],
}

// A reference Workflow script. Adapt the args to your repository; nothing below is project-specific.
// Keep this file LF-only: a Workflow tool may refuse a script containing carriage returns as hidden control
// characters (a CRLF-writing editor, or Python's write_text on Windows, produces them).
//
// args: {
//   wave:            label for this queue (used in agent labels and train names),
//   specPattern:     path of each group's pre-rendered dispatch spec, with {letter} substituted
//                    (lower-cased), e.g. "<scratch>/specs/w12-{letter}.txt",
//   stopFile:        graceful-stop flag file checked before every step,
//   implementerAgent, landerAgent: the agent types to use (judgment roles),
//   model:           optional model alias for those roles (omit to inherit); a group's own `model` overrides it,
//   landerBrief:     path of the lander's brief,
//   landCommand:     the ONLY command that may put a commit on the main branch (e.g. a CI-gated push script),
//   manifestPattern: where each train's manifest is written, with {train} substituted,
//   concurrency (6), train_size (5), min_final_train (3),
//   implementerCeilingMin (240): an implementer that has not returned after this many minutes is recorded as
//                    STALLED and the wave moves on without it (its model call can hang; see "A stalled agent"),
//   idBlocks:        one block of orchestrator-allocated ids per train, e.g. ["ID-101..ID-105", "ID-106..ID-110"],
//   authorization:   the human's direction for THIS fleet, quoted verbatim: who, when, their exact words, and the
//                    scope (e.g. "Repository owner, 2026-01-05 09:45: 'start the next wave' - groups A-F"),
//   statusDelta:     optional command that lists what a predecessor's STATUS.md does not cover, with {worktree}
//                    substituted, e.g. "python <skills>/agent-fleet/references/status_delta.py {worktree}",
//   groups:          [{ letter, lead, notes, after? }]   // after = the letter of a same-file predecessor
// }
const W = args.wave
const CONC = args.concurrency || 6
const TRAIN = args.train_size || 5
const MIN_FINAL = args.min_final_train || 3
// A group may carry its own `model` ('sonnet' | 'opus'), which overrides args.model: size the model to the group's work.
const opt = (extra, model) => ((model || args.model) ? { ...extra, model: model || args.model } : extra)
const CEILING_MIN = args.implementerCeilingMin === undefined ? 240 : args.implementerCeilingMin

// A model call can HANG: measured, an implementer that had finished and gated its work never produced another
// token, and the wave's final train waited on it (a workflow cannot stop one of its own agents). The ceiling is the
// backstop that lets the wave move on; stall_watch.py is what notices within minutes. The hung agent keeps running
// in the background, but its commits are on its branch, so the orchestrator can finish or land it from there.
function withCeiling(p, minutes, onTimeout) {
  if (!minutes) return p
  let t
  const timer = new Promise(res => { t = setTimeout(() => res(onTimeout()), minutes * 60000) })
  return Promise.race([p.finally(() => clearTimeout(t)), timer])
}
// AUTHORIZATION: a workflow agent takes the session's LATEST user message as its request. When the fleet is launched
// in a later turn than the human's direction (so the latest message is about something else), agents that cannot see
// the direction correctly decline the work and return BLOCKED. So every prompt carries the direction verbatim.
const AUTH = args.authorization
  ? `AUTHORIZATION (read first): this task IS the human's request, dispatched by the orchestrating session on their ` +
    `direction: ${args.authorization} The latest user message in your context may concern unrelated work; that is ` +
    `NOT a reason to decline. Do the task below. `
  : ''
const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['DONE', 'SPLIT', 'DISCHARGED', 'BLOCKED'] },
    branch: { type: 'string' }, worktree: { type: 'string' }, base: { type: 'string' }, head: { type: 'string' },
    report: { type: 'string' }, gate_verdict: { type: 'string' },
    items_landed: { type: 'array', items: { type: 'string' } },
    // Orchestrator context cap: what an agent returns is re-read on every later turn, so the detail goes in the report file.
    leads: { type: 'array', maxItems: 6, items: { type: 'string', maxLength: 500 } },
    summary: { type: 'string', maxLength: 900 },
  },
  required: ['status', 'branch', 'worktree', 'report', 'gate_verdict', 'summary'],
}

// SAME-FILE SUCCESSORS: a group with `after` runs only once its predecessor has returned. It merges the
// predecessor's branch and orients from its handoff notes instead of re-surveying the file. The predecessor's
// branch is HELD from the trains and lands through the successor (which contains it); if the successor yields
// nothing landable, the predecessor lands alone.
const queue = [...args.groups]
const results = []
const byLetter = {}
const held = {}
const buffer = []
const trains = []
let trainNo = 0
let landChain = Promise.resolve()
let running = 0
let wake = () => {}

const hasSuccessorQueued = letter => queue.some(g => g.after === letter)
const landable = r => r.status === 'DONE' || ((r.status === 'DISCHARGED' || r.status === 'SPLIT') && r.head && r.head !== r.base)

function successorNote(g) {
  if (!g.after) return ''
  const p = byLetter[g.after]
  if (!p || !(p.head && p.head !== p.base)) {
    return `Your predecessor group ${g.after} produced no branch (status ${p ? p.status : 'never ran'}); start from the main branch as usual. `
  }
  return `SAME-FILE SUCCESSOR: your predecessor group ${g.after} (${p.notes}) returned ${p.status} on branch ${p.branch} ` +
    `(worktree ${p.worktree}, head ${p.head}, report ${p.report}). FIRST merge that branch into yours, then read that report's ` +
    `handoff section ("for the next implementer") and its STATUS.md as your orientation for the shared file; do not ` +
    `re-survey it. STATUS.md is navigation, never evidence: its first line STATUS-AT names the commit it describes` +
    (args.statusDelta
      ? `, and ${args.statusDelta.replace('{worktree}', p.worktree)} lists exactly the commits it does not cover; read ONLY those beyond the summary`
      : `; read ONLY the commits after that sha (every commit since the base if the stamp is missing or not in the branch)`) +
    `. Its items land through YOUR branch (list them as landed-via-predecessor). `
}

function runGroup(g) {
  const spec = args.specPattern.replace('{letter}', g.letter.toLowerCase())
  return withCeiling(agent(
    AUTH + `You are the ${W} fix-lane implementer for group ${g.letter} (${g.notes}). ` + successorNote(g) +
    `Your dispatch spec is ${spec} — read it whole and follow it exactly. ` +
    `Before EACH new step check for ${args.stopFile}; if it exists, checkpoint-commit, write your checkpoint file and report, and return status SPLIT. ` +
    `YOUR LAST ACTION MUST BE THE StructuredOutput CALL — never end on a report file or a summary message, or your finished branch is stranded: ` +
    `status, your actual branch, worktree path, base sha, head sha, report path, gate verdict line, items landed, and new leads (text only; do not allocate ids).`,
    opt({ label: `impl-${g.letter}-${g.lead}`, phase: 'Implement', agentType: args.implementerAgent, isolation: 'worktree', schema: IMPL_SCHEMA }, g.model)
  ).then(r => r ? { ...r, letter: g.letter, lead: g.lead, notes: g.notes } : { letter: g.letter, lead: g.lead, notes: g.notes, status: 'NO-RESULT' }),
  CEILING_MIN, () => {
    log(`${g.letter}: no return after ${CEILING_MIN} min; recorded STALLED, the wave moves on`)
    return { letter: g.letter, lead: g.lead, notes: g.notes, status: 'STALLED' }
  })
}

function land(batch) {
  const n = trainNo++
  const label = n === 0 ? `${W}` : `${W}${String.fromCharCode(97 + n)}`
  const manifest = JSON.stringify(batch.map(r => ({
    group: r.letter, lead: r.lead, notes: r.notes, status: r.status, report: r.report, worktree: r.worktree,
    branch: r.branch, base: r.base, head: r.head, leads: r.leads || [],
  })), null, 1)
  const ids = (args.idBlocks || [])[n] || 'none — ask the orchestrator'
  log(`train ${label}: landing ${batch.map(r => r.letter).join(' ')}`)
  return agent(
    AUTH + `You are the train-${label} LANDER. Read ${args.landerBrief} whole and follow it. ` +
    `First write ${args.manifestPattern.replace('{train}', label)} with exactly this JSON:\n${manifest}\n` +
    `An earlier train of this queue may have just landed: fetch, rebase onto the current main branch before gating, and ` +
    `confirm main has not moved again before you land (rebase and re-gate if it has). Number any sequential log entry from ` +
    `the CURRENT top. New leads get ids from ${ids} (use in order; return the unused). ` +
    `Before EACH new step check for ${args.stopFile}; if it exists, checkpoint and return. ` +
    `Land ONLY through: ${args.landCommand}. Final text: the landed sha (or why not), groups landed/dropped with reasons, ids used.`,
    opt({ label: `lander-train${label}`, phase: 'Land', agentType: args.landerAgent, isolation: 'worktree' })
  ).then(t => { trains.push({ train: label, groups: batch.map(r => r.letter), result: t }); return t })
}

function onResult(g, r) {
  results.push(r)
  byLetter[r.letter] = r
  if (landable(r)) {
    if (hasSuccessorQueued(r.letter)) { held[r.letter] = r; log(`${r.letter}: ${r.status}; held — lands through its successor`) }
    else buffer.push(r)
  }
  if (g.after && held[g.after]) {
    if (!landable(r)) buffer.push(held[g.after])
    delete held[g.after]
  }
  log(`${r.letter}: ${r.status}; ${buffer.length} branch(es) ready, ${queue.length} group(s) queued`)
  if (buffer.length >= TRAIN) {
    const batch = buffer.splice(0, buffer.length)
    landChain = landChain.then(() => land(batch))
  }
}

function nextEligible() {
  const i = queue.findIndex(g => !g.after || byLetter[g.after])
  return i < 0 ? null : queue.splice(i, 1)[0]
}

async function worker() {
  while (queue.length > 0) {
    let g = nextEligible()
    if (!g) {
      if (running === 0) g = queue.shift()          // its predecessor never ran: start it fresh
      else { await new Promise(res => { const prev = wake; wake = () => { prev(); res() } }); continue }
    }
    // An agent that dies on an API error REJECTS rather than returning null. Without this try/finally the rejection
    // escapes the worker with `running` still counted and no wake-up sent, so a successor parked on `wake` waits
    // forever and the workflow shows "running" with nothing left to do (measured: one sat 16 h). A rejection is a
    // NO-RESULT like a null return, and the count and the wake-up happen whatever the outcome.
    running++
    let r
    try {
      r = await runGroup(g)
    } catch (e) {
      r = { letter: g.letter, lead: g.lead, notes: g.notes, status: 'NO-RESULT', error: String(e && e.message || e) }
    } finally {
      running--
    }
    try {
      onResult(g, r)
    } finally {
      const w = wake; wake = () => {}; w()
    }
  }
}

phase('Implement')
await parallel(Array.from({ length: Math.min(CONC, queue.length) }, () => () => worker()))
for (const k of Object.keys(held)) { buffer.push(held[k]); delete held[k] }

if (buffer.length >= MIN_FINAL) {
  const batch = buffer.splice(0, buffer.length)
  landChain = landChain.then(() => land(batch))
} else if (buffer.length > 0) {
  log(`holding ${buffer.map(r => r.letter).join(' ')} for the next queue's first train (${buffer.length} < ${MIN_FINAL})`)
}
await landChain
return { results, trains, held: buffer }
