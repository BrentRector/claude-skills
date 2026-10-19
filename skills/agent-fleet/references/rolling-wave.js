export const meta = {
  name: 'rolling-wave',
  description: 'Rolling fix lane: implementer groups run N at a time from one queue (a freed slot refills at once), each DONE branch is reviewed read-only the moment it returns and enqueued at once when CLEAN, same-file successors merge their predecessor\'s REVIEWED head, and each approved branch is enqueued through the project\'s own enqueue command',
  whenToUse: 'The standard fix-lane dispatch for an agent fleet (agent-fleet references/landing.md and references/grouping-fixes.md).',
  phases: [
    { title: 'Implement', detail: 'one implementer per group, isolated worktrees, rolling pool' },
    { title: 'Review', detail: 'a read-only reviewer per DONE branch; a finisher per blocking round; a re-review reads only the diff' },
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
//   readerAgent:     optional agent type that runs lastVerdictCommand (a cheap read-only tier; default enqueueAgent),
//   model:           optional model alias for the judgment roles (omit to inherit); a group's own `model` overrides it,
//   reviewBrief:     path of the reviewer's brief (the review skill's branch form, correctness first). It names the
//                    project's ONE writer of the findings file, which records each finding with its severity and
//                    computes the round's verdict from the file,
//   findingsPattern: where each branch's findings file is written, with {letter} substituted,
//   lastVerdictCommand: optional: the project's ONE reader of a findings file, with {file} substituted. It prints the
//                    file's newest verdict as one JSON line ({round, head, verdict: CLEAN | FINDINGS | TORN,
//                    blocking}) and never fails: a torn or unreadable file reads TORN. The landing survey must call
//                    the same reader (references/landing.md). Without it, every FINDINGS end reads `unanswered`,
//   finisherBrief:   path of the finisher's brief (fix each blocking finding at the root, regression test, sibling
//                    sweep, the targeted gate again),
//   reviewFixRounds (2): finisher rounds per branch; the review round after the last finisher is the CAPPED round,
//   blocking ('critical,high,medium'): the severities that block a round a finisher can still answer,
//   blockingAtCap ('critical,high'): the severities that block the capped round,
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
// returns { results, reviewed, ready, leads }: `ready` holds every branch the wave did not enqueue, with its reason;
// `leads` holds every review's non-blocking findings, for the loop to file as work items.
const W = args.wave
const CONC = args.concurrency || 6
// A group may carry its own `model` ('sonnet' | 'opus'), which overrides args.model: size the model to the group's work.
const opt = (extra, model) => ((model || args.model) ? { ...extra, model: model || args.model } : extra)
const CEILING_MIN = args.implementerCeilingMin === undefined ? 240 : args.implementerCeilingMin
const REVIEW_FIX_ROUNDS = args.reviewFixRounds === undefined ? 2 : args.reviewFixRounds
const BLOCKING = args.blocking || 'critical,high,medium'
const BLOCKING_AT_CAP = args.blockingAtCap || 'critical,high'
const READER = args.readerAgent || args.enqueueAgent

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
    // CLEAN: this round recorded no finding of a blocking severity. FINDINGS: `blocking` of them. BLOCKED: the review
    // did not finish (the writer refused a torn findings file, the STOP file appeared, the branch would not read).
    verdict: { type: 'string', enum: ['CLEAN', 'FINDINGS', 'BLOCKED'] },
    blocking: { type: 'integer' }, head: { type: 'string' }, findings_file: { type: 'string' },
    leads: { type: 'array', maxItems: 6, items: { type: 'string', maxLength: 500 } },
    summary: { type: 'string', maxLength: 600 },
  },
  required: ['verdict', 'blocking', 'head', 'findings_file', 'summary'],
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
const LAST_VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    // NONE: the command printed no verdict line (read as unanswered, never as clean).
    verdict: { type: 'string', enum: ['CLEAN', 'FINDINGS', 'TORN', 'NONE'] },
    round: { type: 'integer' }, head: { type: 'string' }, blocking: { type: 'integer' },
    output_tail: { type: 'string', maxLength: 800 },
  },
  required: ['verdict', 'output_tail'],
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

// FINISHED WORK IS NEVER HELD. Every finished branch is reviewed the moment its implementer returns, beside the other
// implementers, and is enqueued the moment its review ends CLEAN, whether or not a same-file successor follows it.
// There is no predecessor hold: with one pull request per branch through a merge queue, holding a predecessor to land
// "through" its successor saves nothing and postpones the whole chain until its last link is clean.
//
// SAME-FILE SUCCESSORS: a group with `after` starts once its predecessor is SETTLED: its review loop has ended (CLEAN,
// FINDINGS n, STALE, BLOCKED or NO-RESULT), or it returned with nothing to review. It merges the predecessor's FINAL,
// REVIEWED head (the finisher's, when one ran) and orients from its handoff notes instead of re-surveying the file. The
// landing order is COMMUNICATED (the successor is told the predecessor lands on its own and its own pull request merges
// on top), never enforced by holding. The one thing that keeps a CLEAN successor off the queue is a predecessor's
// UNANSWERED BLOCKING FINDINGS, which the successor's branch carries; whether they stand is read from ONE source, the
// predecessor's findings file, through the project's ONE reader (lastVerdictCommand), never from a report stamp.
const queue = [...args.groups]
const results = []
const byLetter = {}   // letter -> the group's SETTLED result (the reviewed one): a successor starts only once it is set
const reviewed = []   // { letter, branch, rounds, leads, enqueue? } per branch that went past the implementer
const ready = []      // branches not enqueued here, each with its reason (no enqueueCommand, findings open, enqueue stopped)
const post = []       // the review -> finish -> enqueue chains; they run beside the implementers, never in a slot
let running = 0
let settling = 0      // review chains still running: a successor parked on one must not be started fresh
let wake = () => {}

const hasSuccessorQueued = letter => queue.some(g => g.after === letter)
const landable = r => r.status === 'DONE' || ((r.status === 'DISCHARGED' || r.status === 'SPLIT') && r.head && r.head !== r.base)
const sameHead = (a, b) => !!a && !!b && (a.startsWith(b) || b.startsWith(a))
const findingsFile = letter => args.findingsPattern.replace('{letter}', letter.toLowerCase())
function wakeAll() { const w = wake; wake = () => {}; w() }

// HOW A PREDECESSOR'S REVIEW ENDED, as its successor and the successor's reviewer read it. ONE reading, so the
// implementer's note and the reviewer's scope never disagree.
//   'clean'       reviewed CLEAN at its head: it is enqueued on its own.
//   'capped'      FINDINGS, and the findings file's last verdict is the capped round at the predecessor's head: no
//                 finisher followed it, so the findings belong to the predecessor's own next finisher. The successor
//                 neither answers them nor records them again, and it is not enqueued while they stand.
//   'unanswered'  any other FINDINGS end: a finisher was sent and came back without answering (SPLIT, BLOCKED, killed;
//                 a commit of its own or none), or the last verdict could not be read, or the file is TORN. Whatever
//                 the finisher left half done is on the successor's branch, so the successor's review covers the
//                 predecessor's commits as its own and records again each finding that still holds; and it is not
//                 enqueued while they stand. A torn file is never read as capped.
//   'unreviewed'  the review did not finish (STALE, BLOCKED, NO-RESULT): its commits are reviewed with the successor's.
function predecessorEnd(p) {
  if (p.review === 'CLEAN') return 'clean'
  if (!/^FINDINGS/.test(p.review || '')) return 'unreviewed'
  const v = p.last_verdict
  return v && v.verdict === 'FINDINGS' && v.blocking > 0 && v.round > REVIEW_FIX_ROUNDS && sameHead(v.head, p.head)
    ? 'capped' : 'unanswered'
}

// THE ONE READER of a findings file, run by one cheap read-only agent (a workflow script cannot run a command itself).
// null (read as unanswered) when the project names no reader or the reader gave no verdict line.
async function lastVerdict(letter) {
  if (!args.lastVerdictCommand) return null
  const cmd = args.lastVerdictCommand.replace('{file}', findingsFile(letter))
  const v = await agent(
    AUTH + `Run EXACTLY this command once, alone (never chained), and read the one verdict line it prints: ${cmd} ` +
    `Read no other file and judge nothing: report the verdict, round, head and blocking count exactly as printed, and the tail of its output.`,
    { label: `last-verdict-${letter}`, phase: 'Review', agentType: READER, schema: LAST_VERDICT_SCHEMA }
  ).catch(() => null)
  if (!v || v.verdict === 'NONE') { log(`${letter}: the findings reader gave no verdict; its successor reads it unanswered`); return null }
  return v
}

function successorNote(g) {
  if (!g.after) return ''
  const p = byLetter[g.after]
  if (!p || !(p.head && p.head !== p.base)) {
    return `Your predecessor group ${g.after} produced no branch (status ${p ? p.status : 'never ran'}); start from the default branch as usual. `
  }
  const file = findingsFile(g.after)
  return `SAME-FILE SUCCESSOR: your predecessor group ${g.after} (${p.notes}) ended ${p.status}, review ${p.review || 'none'}, ` +
    `on its FINAL branch ${p.branch} (worktree ${p.worktree}, head ${p.head}, report ${p.report}). FIRST merge that branch ` +
    `at head ${p.head} into yours (it is the reviewed head), then read that report's handoff section ("for the next ` +
    `implementer") and its STATUS.md as your orientation for the shared file; do not re-survey it. STATUS.md is ` +
    `navigation, never evidence: its first line STATUS-AT names the commit it describes` +
    (args.statusDelta
      ? `, and ${args.statusDelta.replace('{worktree}', p.worktree)} lists exactly the commits it does not cover; read ONLY those beyond the summary`
      : `; read ONLY the commits after that sha (every commit since the base if the stamp is missing or not in the branch)`) +
    `. Its items are its own: never claim them as yours. ` +
    {
      clean: `It was reviewed CLEAN and is enqueued ON ITS OWN, now; your pull request merges on top of it. `,
      capped: `Its review ended ${p.review} at the round cap: those findings (${file}) belong to its own next finisher, ` +
        `not to you; do not fix or answer them. Your branch carries them, so it is enqueued only after they are answered. `,
      unanswered: `Its review ended ${p.review} and its finisher came back ${p.finisher || 'without a verdict'} without ` +
        `answering them: those findings (${file}) are UNANSWERED and your branch carries them, with whatever that finisher ` +
        `left half done. Read them and fix the ones your change reaches; your reviewer covers the predecessor's commits as ` +
        `yours, and your branch is enqueued only after they are answered. `,
      unreviewed: `Its review did not finish (${p.review || 'none'}), so its commits on your branch are reviewed with yours and land with yours. `,
    }[predecessorEnd(p)]
}

// What round 1 of a SUCCESSOR's review leaves alone, by predecessorEnd: content reviewed CLEAN is not re-opened (a
// successor's reviewer that re-reviews it restates the predecessor's findings); a capped predecessor's findings stay in
// its own file. An unanswered predecessor is reviewed with this branch and its findings recorded again; an unreviewed
// one is reviewed as this branch.
function predecessorScope(g) {
  const p = g.after ? byLetter[g.after] : null
  if (!p || !p.review || !(p.head && p.head !== p.base)) return ''
  const file = findingsFile(g.after)
  return {
    clean: `This branch merged its same-file predecessor ${p.branch} at ${p.head}, reviewed CLEAN (${file}): that content is reviewed and is not re-opened unless this branch's own commits touch it. `,
    capped: `This branch merged its same-file predecessor ${p.branch} at ${p.head}, whose review ended ${p.review} at the round cap: those findings are recorded in ${file} and belong to its own finisher; do not record them again here. `,
    unanswered: `This branch merged its same-file predecessor ${p.branch} at ${p.head}, whose findings (${file}) are UNANSWERED: review the predecessor's commits as part of this branch and record again here each of those findings that still holds on this head. `,
    unreviewed: '',
  }[predecessorEnd(p)]
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

// THE REVIEW LOOP. Round 1 reviews the whole branch. On FINDINGS a finisher answers the blocking ones and the branch is
// reviewed again, at most REVIEW_FIX_ROUNDS times; a re-review reads ONLY the finisher's diff from the head the last
// round reviewed, plus its answers, because the earlier content is reviewed (whole-branch re-reviews each find something
// new and never converge). The verdict is a SEVERITY THRESHOLD: BLOCKING while a finisher can still answer, then
// BLOCKING_AT_CAP, so a medium finding blocks until the cap and is a lead there, a low or info one never blocks, and
// critical and high always block. Every non-blocking finding is a LEAD, recorded and returned, never dropped.
function reviewPrompt(g, r, round, head, reviewedHead, blocking, file) {
  return AUTH + `You are the READ-ONLY reviewer of branch ${r.branch} (worktree ${r.worktree}, group ${r.letter}: ${r.notes}; ` +
    `implementer report ${r.report}), review round ${round}, at head ${head}. Read ${args.reviewBrief} whole and follow it. ` +
    (round === 1
      ? `Review the whole branch: its diff against the default branch. ` + predecessorScope(g)
      : `This is a RE-REVIEW after the finisher's round: review ONLY \`git diff ${reviewedHead}..${head}\` (when the finisher ` +
        `merged a newer default branch, only its own commits: \`git log --no-merges ${reviewedHead}..${head} --not <default>\`) ` +
        `and its answers to round ${round - 1}'s findings in ${file}. The earlier content is reviewed and is not re-opened ` +
        `unless the diff touches it. Raise again only a blocking finding neither fixed nor answered with a reason you accept, ` +
        `and any new defect the diff introduced. `) +
    `Record every CONFIRMED finding in ${file} through the project's writer, each with its concrete failure scenario, repro, ` +
    `code site and SEVERITY (critical, high, medium, low or info: what it does, calibrated, never raised to make it block). ` +
    `This round's blocking severities are ${blocking}: the verdict is computed from the file, CLEAN when this round recorded ` +
    `no finding of a blocking severity, else FINDINGS with that count; a finding with no severity, or an unknown one, blocks. ` +
    `Every other finding is a LEAD: recorded, not blocking; return each as a one-line lead. If the writer refuses the ` +
    `findings file as torn, stop: never edit or repair it; return BLOCKED. You never edit the branch. ` + STOP +
    `Return the verdict, the blocking count, the head you reviewed, the findings path and the leads.`
}

async function reviewLoop(g, r) {
  const rec = { letter: r.letter, branch: r.branch, worktree: r.worktree, rounds: [], leads: [] }
  reviewed.push(rec)
  const file = findingsFile(r.letter)
  let head = r.head
  let reviewedHead = null
  for (let round = 1; ; round++) {
    const capped = round > REVIEW_FIX_ROUNDS
    const v = await agent(reviewPrompt(g, r, round, head, reviewedHead, capped ? BLOCKING_AT_CAP : BLOCKING, file),
      opt({ label: `review-${r.letter}-r${round}`, phase: 'Review', agentType: args.reviewerAgent, schema: REVIEW_SCHEMA })
    ).catch(() => null)
    const verdict = !v ? 'NO-RESULT' : (v.verdict === 'CLEAN' && !sameHead(v.head, head)) ? 'STALE' : v.verdict
    if (v && Array.isArray(v.leads)) rec.leads.push(...v.leads)
    rec.rounds.push({ round, head, verdict, blocking: v ? v.blocking : null })
    log(`${r.letter}: review round ${round} at ${head}: ${verdict}${verdict === 'FINDINGS' ? ' ' + v.blocking : ''}`)
    const end = { ...r, head, review_rounds: round, review_leads: rec.leads, rec }
    if (verdict === 'CLEAN') return { ...end, review: 'CLEAN' }
    if (verdict !== 'FINDINGS') return { ...end, review: verdict }
    if (capped) {
      log(`${r.letter}: still FINDINGS after ${REVIEW_FIX_ROUNDS} finisher round(s); its own next finisher answers them`)
      return { ...end, review: `FINDINGS ${v.blocking}` }
    }
    const f = await agent(
      AUTH + `You are the FINISHER of branch ${r.branch} (worktree ${r.worktree}) after review round ${round}. Read ` +
      `${args.finisherBrief} whole and follow it. Answer EVERY BLOCKING finding of round ${round} in ${file} by its id: fix ` +
      `it at the root with a regression test and a sibling sweep, or refute it with evidence written beside it. A LEAD is ` +
      `not yours unless it sits in a file you change anyway. Then run the TARGETED gate again and commit. ` + STOP +
      `Return status, the new head sha, the gate verdict line and the number answered.`,
      opt({ label: `finish-${r.letter}-r${round}`, phase: 'Review', agentType: args.finisherAgent, schema: FINISH_SCHEMA })
    ).catch(() => null)
    if (!f || f.status !== 'DONE' || !f.head || sameHead(f.head, head)) {
      log(`${r.letter}: finisher round ${round} returned ${f ? f.status : 'NO-RESULT'}; its findings stay unanswered`)
      return { ...end, head: f && f.head ? f.head : head, review: `FINDINGS ${v.blocking}`, finisher: f ? f.status : 'NO-RESULT' }
    }
    reviewedHead = head
    head = f.head
  }
}

async function enqueue(s) {
  if (!args.enqueueCommand) { ready.push({ letter: s.letter, branch: s.branch, worktree: s.worktree, reason: 'reviewed CLEAN' }); return }
  const cmd = args.enqueueCommand.replace('{branch}', s.branch).replace('{worktree}', s.worktree)
  s.rec.enqueue = await agent(
    AUTH + `Run EXACTLY this command once, alone (never chained), to a log, and read its verdict line: ${cmd} ` +
    `Change nothing yourself: if it stops on a conflict or a red, report that verdict and the tail of its output.`,
    opt({ label: `enqueue-${s.letter}`, phase: 'Enqueue', agentType: args.enqueueAgent, schema: ENQUEUE_SCHEMA })
  ).catch(e => ({ verdict: 'ERROR', output_tail: String(e && e.message || e) }))
  log(`${s.letter}: enqueue ${s.rec.enqueue.verdict}${s.rec.enqueue.pr ? ' ' + s.rec.enqueue.pr : ''}`)
  if (s.rec.enqueue.verdict !== 'ENQUEUED') ready.push({ letter: s.letter, branch: s.branch, worktree: s.worktree, reason: 'enqueue stopped' })
}

// Review a finished branch, settle it for its successor, and enqueue it at once when CLEAN, predecessor or not. A
// successor reviewed CLEAN is held back only by its predecessor's unanswered blocking findings, which it carries.
async function settle(g, r) {
  try {
    let s = await reviewLoop(g, r)
    if (/^FINDINGS/.test(s.review) && hasSuccessorQueued(r.letter)) s = { ...s, last_verdict: await lastVerdict(r.letter) }
    const { rec, ...out } = s          // the record is returned once, under `reviewed`
    results.push(out)
    byLetter[r.letter] = s
    wakeAll()                          // its successor may start now, while this one is enqueued
    const p = g.after ? byLetter[g.after] : null
    const carries = s.review === 'CLEAN' && p && ['capped', 'unanswered'].includes(predecessorEnd(p))
    if (s.review === 'CLEAN' && !carries) await enqueue(s)
    else ready.push({ letter: s.letter, branch: s.branch, worktree: s.worktree,
      reason: carries ? `carries group ${g.after}'s unanswered findings (${findingsFile(g.after)})` : `review ${s.review}` })
  } finally {
    settling--
    wakeAll()
  }
}

function onResult(g, r) {
  if (landable(r)) {
    settling++
    post.push(settle(g, r))
  } else {
    results.push(r)
    byLetter[r.letter] = r             // nothing to review: settled now
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
      if (running === 0 && settling === 0) g = queue.shift()   // its predecessor never ran: start it fresh
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
      wakeAll()
    }
  }
}

phase('Implement')
await parallel(Array.from({ length: Math.min(CONC, queue.length) }, () => () => worker()))
await Promise.all(post)
const leads = results.flatMap(r => (r.review_leads || []).map(l => `${r.letter} (${r.branch}): ${l}`))
return { results, reviewed: reviewed.map(({ letter, branch, rounds, enqueue }) => ({ letter, branch, rounds, enqueue })), ready, leads }
