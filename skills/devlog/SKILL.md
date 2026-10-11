---
name: devlog
description: Use when a project keeps (or should keep) a development log, work history, changelog of findings or fix log that Claude agents write and read, including setting one up, writing, numbering or timestamping an entry, recording a failed, reverted or overturned approach, checking whether something was tried before, enforcing one entry per landing (one file per entry, numbered at enqueue, checked in CI), migrating a single-file log, or consolidating a long log into candidate learnings and validating them before they are published or encoded into a skill.
---

# Development log

A development log is the project's memory: agents lose their context at every session end, and the log is where
what happened, what was tried and why survives. The rules below make it trustworthy. Every rule carries its *why*;
**violating the letter of a rule is violating its spirit.**

## Choose the form by purpose

A project can keep more than one. They differ in audience, not in the core rules.

| Form | Audience | One entry per | Layout |
|---|---|---|---|
| **Working history** | the team and every future agent | every landing (one per pull request, in its branch) | one file per entry (`devlog/NNNN-slug.md`), numbered when the branch is enqueued; the newest-first document is a rendered view, never committed |
| **Defect/fix log** | reviewers, source-license customers | defect fixed in shipped code (not refactors, features or doc changes) | one newest-first file |
| **Published narrative** | outsiders | milestone or finding, reversals included | one post per file with frontmatter |

Templates: `templates/entry-working.md`, `templates/entry-fix-log.md`, `templates/entry-post.md`. The working
history is the source for the other two; they never replace it.

## Core rules (all forms)

| Rule | Why |
|---|---|
| **An entry with every landing.** For the working history, one entry file per pull request, written in the branch by the agent that did the work. A branch's checkpoint commits carry none. | An entry written later loses the reasoning of the moment, and a batch of changes gets one vague entry. |
| **One file per entry, numbered at enqueue, the view rendered.** | Entries inserted at the top of one shared file collide whenever two pull requests are queued together, and each collision bounces one. Numbering at enqueue (after the final rebase) makes number order landing order; an implementer cannot know the landing order. *(Practice — not yet validated: adopted 2026-10-11 with a merge queue.)* |
| **The timestamp comes from the clock**: `devlog.py new` stamps it, or `date "+%Y-%m-%d %H:%M %Z"`. Never a time you estimated or were told approximately ("around 4:30"). | Estimated stamps were caught wrong twice in one day. Readers reconstruct order and duration from them. *(Practice — not yet validated: a prose rule alone did not hold; no enforced check yet.)* |
| **A correction is a NEW entry** that names the entry it overturns. Never edit, delete or renumber an old one, even to "fix" a wrong cause (`devlog.py check --base` refuses a landing that does). | The log records what was believed when. A rewritten entry hides the mistake, and commits and docs that cite it now point at different text. *(Practice — not yet validated: no measured effect.)* |
| **Keep failures, dead ends and overturned verdicts.** | "Tried X, failed because Y" saves the most time later and is the entry most often skipped. *(Practice — not yet validated: no measured effect.)* |
| **Each entry records context, what was tried and why, the result (with numbers), the lesson, and what's next.** | Without the why and the rejected alternatives, the next agent repeats them. |
| **Only the log is historical.** Every other doc describes the current state. | History scattered into design docs rots, and those docs stop saying what is true now. *(Practice — not yet validated: no measured effect.)* |

## Writing an entry

Use the bundled script, `references/devlog.py`; never hand-write a file name, a number or a time.

```
python references/devlog.py new --title "Shared temp dir, not the retry lock" --body-file entry.md   # in the branch
python references/devlog.py stamp --base origin/main     # the enqueue step, after the final rebase
python references/devlog.py check --base origin/main --one   # the enqueue step and CI (pull request and merge group)
python references/devlog.py render --out devlog.rendered.md  # the newest-first view, gitignored
```

- `new` writes `devlog/pending-<slug>.md`, headed `## Entry pending — Title`: no number and no time yet.
- `stamp` (run by the enqueue step, never the implementer) takes the next free number — over the directory AND the
  default branch, or `--number N` from the project's one allocator — renames the file to `NNNN-<slug>.md` and completes
  the header `## Entry N — YYYY-MM-DD HH:MM TZ — Title` with the time from the clock. A bounced pull request keeps its
  number; gaps are fine. Commit the rename on the branch before the pull request opens.
- `check` validates every entry (names, headers, timestamps, unique numbers, no carriage return, no pending file);
  with `--base` it also checks the LANDING: at least one (with `--one`, exactly one) stamped entry added, none pending,
  no existing entry changed or deleted, no number already on the base. `--from N` skips early entries that predate the
  rules (never renumber them: commits cite them).
- `next` prints the next free number; `search -i "<regex>"` searches the entries, newest first.
- Files are LF (the `cross-platform` skill's line-ending rule). The log path comes from `--log` or `.devlog.json`
  (`templates/devlog.json`).

*Why a script: agents splicing by hand once put an entry inside the ordering note, and a text-mode rewrite of a CRLF
single-file log turned a 50-line entry into a 36,000-line whole-file diff. One file per entry removes the splice.*

**Moving from a single newest-first file:** `python references/devlog.py migrate --from history.md` splits it ONCE,
content-faithfully, into entry files written LF (the preamble becomes `devlog/README.md`) and reads every file back to
verify it. Delete the old file and any insert tool in the same landing, and change every brief, rule and script that
says "the top of the log" in that landing too.

## Using the log

1. **Session start: do NOT read the log** (or its rendered view). Read the project's small CURRENT-STATE document instead (live state,
   open work, next steps). That is kept current because every other doc describes the present. *Why: the log is
   written for completeness, not for reading. A 1,750-entry log is about 880,000 words, and even its newest entries
   are an unbounded context cost that restates what the current-state doc already says. Its value is being
   searchable when a question arises.*
2. **Before retrying an approach:** `python references/devlog.py search -i "<regex>"`. If it was tried, cite the
   entry and say what differs this time. *Why: in a long log the same dead end gets rediscovered.*
3. **Consolidate periodically, then validate** (next section). *Why: a 1,750-entry log is unreadable at session
   start, so what it taught has to be distilled; and what is distilled has to be checked before anyone relies on it.*

## From log to learnings: three stages

| Stage | Produces | How |
|---|---|---|
| **1. Record** | the log: everything, hypotheses and wrong turns included | an entry with every landing |
| **2. Consolidate** | `LEARNINGS-CANDIDATES.md`: numbered CANDIDATE learnings (problem / root cause / fix / evidence / when), reversals labeled, closing with **open problems** and **not yet acted on** | one agent, `templates/consolidate-brief.md` |
| **3. Validate** | a verdict per candidate: **VETTED**, **UNPROVEN** or **REFUTED**, with its evidence; then `LEARNINGS.md` holding the vetted ones only | a fresh adversarial agent per batch, `templates/validate-brief.md` |

- **VETTED requires all four:** (1) the root cause is confirmed, not a hypothesis later overturned; (2) the evidence
  is re-checked against primary sources; (3) no later log entry contradicts it; (4) the fix has been used and shown
  useful (a measured effect, or sustained use with no reversal). Otherwise it is **UNPROVEN** (naming the missing
  evidence) or **REFUTED** (citing the contradicting source).
- **Only VETTED learnings enter `LEARNINGS.md`**, each recording its validation: date, sources checked, proof of use.
- **Only vetted learnings are encoded into a skill, a rule, a hook or a `CLAUDE.md` block.** A candidate, however
  plausible, is not.
- **Refuted candidates stay in the record**, marked REFUTED with the contradicting source; UNPROVEN ones stay marked
  with what is missing. Never drop one silently.

*Why: a log records hypotheses as well as conclusions, and some are later refuted: in one project a published
explanation of an observed silence was refuted the same day. A learnings file compiled straight from the log inherits
those errors, and a skill that encodes them spreads them. Consolidation is cheap and finds real problems (one run:
145 candidates and 15 open problems in ~30 min, and a contradiction it surfaced was real and was fixed), but its
output is a list of claims read out of the log, not a list of facts. The first validation of those 145 vetted 46, left 90 unproven and refuted 9, and independent refuters overturned 21 of the 67 that a first validator had vetted.*

## Enforcing it

Paste `templates/CLAUDE-devlog.md` into the project's `CLAUDE.md`, put `.devlog.json` at the repo root, and enforce at
three points:

- **CI, on the pull request and on the merge group:** `devlog.py check --base <the PR's base, or the merge group's
  base sha>` (with `--one` on the pull request). This is the hard gate. Gitignore the rendered view, and have CI
  render it so a broken entry fails there.
- **The enqueue step:** `devlog.py stamp --base <default>`, commit, then `devlog.py check --base <default> --one`
  before it opens the pull request.
- **The agent's side:** `references/devlog_guard.py` as a PreToolUse hook (`templates/settings.json`). It ASKS when an
  agent runs `gh pr create` or `gh pr merge` on a branch that adds no stamped entry (or only a pending one).
- **Register the hook with matcher `Bash|PowerShell` and NO `if` filter.** *Why: an `if` filter such as
  `Bash(git commit*)` or `Bash(gh pr create*)` does not match a chained command (`git add -A && git commit …`,
  `git push … && gh pr create …`), the usual agent form; measured on a sibling hook, the filter silenced it in most
  sessions. The script finds the command anywhere and exits at once on anything else.* *(Practice — not yet validated: the filter's effect was measured in a sandbox, not yet in production.)*
- **It asks; it does not deny.** *Why: a message-only amend or a deliberate exception needs a person to wave it
  through, not a refusal the agent learns to route around.*
- It is silent outside repos with `.devlog.json`, fails open on any error (an unresolvable base included: CI
  decides), and `--self-test` proves each branch. So does `devlog.py --self-test`.

## Red flags

- A header time you typed rather than read from the clock.
- Opening an old entry to fix its conclusion.
- "I'll write the entries at the end of the session."
- An implementer choosing its own entry number, or a pull request carrying a `pending-` entry.
- A committed rendered view, or a generated index, that every pull request rewrites (the queue bounces the second).
- A "history" or "changes" section growing in a design doc.
- A hand-written file name, number or insertion (`text.index("## Entry ")`, `open(p, "w")`) instead of `devlog.py new` / `stamp`.
- A hook registered with an `if` filter (`if: Bash(git commit*)`, `if: Bash(gh pr create*)`).
- A learnings file, a skill rule or a hook built from a consolidation run that no validator has ruled on.
- A refuted candidate deleted instead of marked REFUTED.
