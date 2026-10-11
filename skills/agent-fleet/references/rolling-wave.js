export const meta = {
  name: 'rolling-wave',
  description: 'Rolling fix lane: implementer groups run N at a time from one queue (a freed slot refills at once), same-file successors inherit their predecessor\'s branch, each DONE branch is reviewed read-only, and each approved branch is enqueued through the project\'s own enqueue command',
  whenToUse: 'The standard fix-lane dispatch for an agent fleet (agent-fleet references/landing.md and references/grouping-fixes.md).',
  phases: [
    { title: 'Implement', detail: 'one implementer per group, isolated worktrees, rolling pool' },
    { title: 'Review', detail: 'a read-only reviewer per DONE branch; a finisher answers confirmed findings' },
    { title: 'Enqueue', detail: 'the project\'s deterministic enqueue command per approved branch (one pull request each)' },
  ],
}

// A reference Workflow script. Adapt the args to your repository; nothing below is project-specific.
// Keep this file LF-only: a Workflow tool may refuse a script containing carriage returns as hidden control
// characters (a CRLF-writing editor, or Python's write_text on Windows, produces them). The cross-platform skill's
// line-ending rule (`* text=auto eol=lf`) keeps it that way.
//
// The wave PRODUCES DONE BRANCHES. It starts no lander and assembles no train: every approved branch becomes its own
// pull request through the project's enqueue step, and CI's merge-group run is the whole-population gate
// (references/landing.md). A conflict or a queue bounce after the wave is the orchestrator loop's enqueue unit's
// business (it dispatches a finisher).
//
// args: {
//   wave:            label for this queue (used in agent labels),
//   specPattern:     path of each group's pre-rendered dispatch spec, with {letter} substituted
//                    (lower-cased), e.g. "<scratch>/specs/w12-{letter}.txt",
//   stopFile:        graceful-stop flag file checked before every step,
//   implementerAgent, reviewerAgent, finisherAgent: the agent types (judgment roles; the reviewer is read-only),
//   enqueueAgent:    optional agent type that runs the enqueue command and reports its verdict (a cheap tier is enough;
//                    a Workflow script cannot run a shell command itself),
//   model:           optional model alias for the judgment roles (omit to inherit); a group's own `model` overrides it,
//   reviewBrief:     path of the reviewer's brief (the review skill's branch form: <default>...HEAD, correctness first),
//   findingsPattern: where each branch's findings file is written, with {letter} substituted,
//   finisherBrief:   path of the finisher's brief (fix each confirmed finding at the root, regression test, sibling
//                    sweep, the targeted gate again),
//   enqueueCommand:  optional: the project's DETERMINISTIC enqueue step for one branch, with {branch} and {worktree}
//                    substituted (fetch, rebase, the targeted gate under the gate-slot cap, stamp the log entry, the
//                    landing checks, open the pull request, add it to the merge queue). Omit it to return the approved
//                    branches as `ready` for the orchestrator loop's enqueue unit,
//   concurrency (6),
//   implementerCeilingMin (240): an implementer that has not returned after this many minutes is recorded as
//                    STALLED and the wave moves on without it (its model call can hang; see "A stalled agent"),
//   authorization:   the human's direction for THIS fleet, quoted verbatim: who, when, their exact words, and the
//                    scope (e.g. "Repository owner, 2026-01-05 09:45: 'start the next wave' - groups A-F"),
//   statusDelta:     optional command that lists what a predecessor's STATUS.md does not cover, with {worktree}
//                    substituted, e.g. "python <skills>/agent-fleet/references/status_delta.py {worktree}",
//   groups:          [{ letter, lead, notes, after? }]   // after = the letter of a same-file predecessor
// }
const W = args.wave
const CONC = args.concurrency || 6
// A group may carry its own `model` ('sonnet' | 'opus'), which overrides args.model: size the model to the group's work.
const opt = (extra, model) => ((model || args.model) ? { ...extra, model: model || args.model } : extra)
const CEILING_MIN = args.implementerCeilingMin === undefined ? 240 : args.implementerCeilingMin

// A model call can HANG: measured, an implementer that had finished and gated its work never produced another
// token, and the wave's final step waited on it (a workflow cannot stop one of its own agents). The ceiling is the
// backstop that lets the wave move on; stall_watch.py is what notices within minutes. The hung agent keeps running
// in the background, but its commits are on its branch, so the orchestrator can finish or enqueue it from there.
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
const STOP = `Before EACH new step check for ${args.stopFile}; if it exists, checkpoint-commit, write your checkpoint file and report, and return status SPLIT. `
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
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['CLEAN', 'FINDINGS', 'BLOCKED'] },
    confirmed: { type: 'integer' }, findings_file: { type: 'string' },
    summary: { type: 'string', maxLength: 600 },
  },
  required: ['verdict', 'confirmed', 'findings_file', 'summary'],
}
const FINISH_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['DONE', 'SPLIT', 'BLOCKED'] },
    head: { type: 'string' }, gate_verdict: { type: 'string' }, answered: { type: 'integer' },
    summary: { type: 'string', maxLength: 600 },
  },
  required: ['status', 'head', 'gate_verdict', 'summary'],
}
const ENQUEUE_SCHEMA = {
  type: 'object',
  properties: {
    // ENQUEUED: the pull request is in the merge queue. CONFLICT / GATE-RED / CHECK-RED: the step stopped and named why;
    // the branch waits for a finisher (the orchestrator loop's enqueue unit dispatches it).
    verdict: { type: 'string', enum: ['ENQUEUED', 'CONFLICT', 'GATE-RED', 'CHECK-RED', 'ERROR'] },
    pr: { type: 'string' }, output_tail: { type: 'string', maxLength: 1200 },
  },
  required: ['verdict', 'output_tail'],
}

// SAME-FILE SUCCESSORS: a group with `after` runs only once its predecessor has returned. It merges the
// predecessor's branch and orients from its handoff notes instead of re-surveying the file. The predecessor's
// branch is HELD and lands through the successor (which contains it); if the successor yields nothing landable,
// the predecessor is reviewed and enqueued alone.
const queue = [...args.groups]
const results = []
const byLetter = {}
const held = {}
const reviewed = []   // { letter, branch, review, finish?, enqueue? } per branch that went past the implementer
const ready = []      // approved branches not enqueued here (no enqueueCommand, or the enqueue step stopped)
const post = []       // the review → finish → enqueue chains; they run beside the implementers, never in a slot
let running = 0
let wake = () => {}

const hasSuccessorQueued = letter => queue.some(g => g.after === letter)
const landable = r => r.status === 'DONE' || ((r.status === 'DISCHARGED' || r.status === 'SPLIT') && r.head && r.head !== r.base)

function successorNote(g) {
  if (!g.after) return ''
  const p = byLetter[g.after]
  if (!p || !(p.head && p.head !== p.base)) {
    return `Your predecessor group ${g.after} produced no branch (status ${p ? p.status : 'never ran'}); start from the default branch as usual. `
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
    `Your dispatch spec is ${spec} — read it whole and follow it exactly. Your gate is the TARGETED local leg; CI's ` +
    `merge-group run is the whole-population gate. Write your log entry file WITHOUT a number (the enqueue step stamps it). ` +
    STOP +
    `YOUR LAST ACTION MUST BE THE StructuredOutput CALL — never end on a report file or a summary message, or your finished branch is stranded: ` +
    `status, your actual branch, worktree path, base sha, head sha, report path, gate verdict line, items landed, and new leads (text only; do not allocate ids).`,
    opt({ label: `impl-${g.letter}-${g.lead}`, phase: 'Implement', agentType: args.implementerAgent, isolation: 'worktree', schema: IMPL_SCHEMA }, g.model)
  ).then(r => r ? { ...r, letter: g.letter, lead: g.lead, notes: g.notes } : { letter: g.letter, lead: g.lead, notes: g.notes, status: 'NO-RESULT' }),
  CEILING_MIN, () => {
    log(`${g.letter}: no return after ${CEILING_MIN} min; recorded STALLED, the wave moves on`)
    return { letter: g.letter, lead: g.lead, notes: g.notes, status: 'STALLED' }
  })
}

// REVIEW ON THE BRANCH, then ENQUEUE. The review runs when the branch is DONE, beside the other implementers, so it is
// never on a landing's critical path; the enqueue step never reviews and never fixes.
async function reviewAndEnqueue(r) {
  const rec = { letter: r.letter, branch: r.branch, worktree: r.worktree }
  reviewed.push(rec)
  const findings = args.findingsPattern.replace('{letter}', r.letter.toLowerCase())
  rec.review = await agent(
    AUTH + `You are the READ-ONLY reviewer of branch ${r.branch} (worktree ${r.worktree}, group ${r.letter}: ${r.notes}; ` +
    `implementer report ${r.report}). Read ${args.reviewBrief} whole and follow it. Review the branch's diff against the ` +
    `default branch; write every CONFIRMED finding, each with its concrete failure scenario, repro and code site, to ` +
    `${findings}. You never edit the branch. ` + STOP + `Return the verdict, the confirmed count and the findings path.`,
    opt({ label: `review-${r.letter}`, phase: 'Review', agentType: args.reviewerAgent, schema: REVIEW_SCHEMA })
  ).catch(e => ({ verdict: 'BLOCKED', confirmed: 0, findings_file: findings, summary: String(e && e.message || e) }))
  if (!rec.review || rec.review.verdict === 'BLOCKED') {
    log(`${r.letter}: review did not complete; the branch waits for the orchestrator`)
    ready.push({ ...rec, reason: 'review incomplete' })
    return
  }
  if (rec.review.verdict === 'FINDINGS' && rec.review.confirmed > 0) {
    rec.finish = await agent(
      AUTH + `You are the FINISHER of branch ${r.branch} (worktree ${r.worktree}). Read ${args.finisherBrief} whole and ` +
      `follow it. Answer every confirmed finding in ${findings}: fix it at the root with a regression test and a sibling ` +
      `sweep, or refute it with evidence written beside it. Then run the TARGETED gate again. ` + STOP +
      `Return status, the new head sha, the gate verdict line and the number answered.`,
      opt({ label: `finish-${r.letter}`, phase: 'Review', agentType: args.finisherAgent, schema: FINISH_SCHEMA })
    ).catch(e => ({ status: 'BLOCKED', head: '', gate_verdict: '', summary: String(e && e.message || e) }))
    if (!rec.finish || rec.finish.status !== 'DONE') {
      log(`${r.letter}: findings not all answered (${rec.finish ? rec.finish.status : 'NO-RESULT'}); not enqueued`)
      ready.push({ ...rec, reason: 'findings open' })
      return
    }
  }
  if (!args.enqueueCommand) { ready.push(rec); return }
  const cmd = args.enqueueCommand.replace('{branch}', r.branch).replace('{worktree}', r.worktree)
  rec.enqueue = await agent(
    AUTH + `Run EXACTLY this command once, alone (never chained), to a log, and read its verdict line: ${cmd} ` +
    `Change nothing yourself: if it stops on a conflict or a red, report that verdict and the tail of its output.`,
    opt({ label: `enqueue-${r.letter}`, phase: 'Enqueue', agentType: args.enqueueAgent, schema: ENQUEUE_SCHEMA })
  ).catch(e => ({ verdict: 'ERROR', output_tail: String(e && e.message || e) }))
  log(`${r.letter}: enqueue ${rec.enqueue ? rec.enqueue.verdict : 'NO-RESULT'}${rec.enqueue && rec.enqueue.pr ? ' ' + rec.enqueue.pr : ''}`)
  if (!rec.enqueue || rec.enqueue.verdict !== 'ENQUEUED') ready.push({ ...rec, reason: 'enqueue stopped' })
}

const release = r => { post.push(reviewAndEnqueue(r)) }

function onResult(g, r) {
  results.push(r)
  byLetter[r.letter] = r
  if (landable(r)) {
    if (hasSuccessorQueued(r.letter)) { held[r.letter] = r; log(`${r.letter}: ${r.status}; held — lands through its successor`) }
    else release(r)
  }
  if (g.after && held[g.after]) {
    if (!landable(r)) release(held[g.after])
    delete held[g.after]
  }
  log(`${r.letter}: ${r.status}; ${queue.length} group(s) queued`)
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
for (const k of Object.keys(held)) { release(held[k]); delete held[k] }
await Promise.all(post)
return { results, reviewed, ready }
