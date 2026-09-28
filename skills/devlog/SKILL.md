---
name: devlog
description: Use when a project keeps (or should keep) a development log, work history, changelog of findings or fix log that Claude agents write and read, including setting one up, writing, numbering or timestamping an entry, recording a failed, reverted or overturned approach, checking whether something was tried before, enforcing an entry with every commit, or consolidating a long log into candidate learnings and validating them before they are published or encoded into a skill.
---

# Development log

A development log is the project's memory: agents lose their context at every session end, and the log is where
what happened, what was tried and why survives. The rules below make it trustworthy. Every rule carries its *why*;
**violating the letter of a rule is violating its spirit.**

## Choose the form by purpose

A project can keep more than one. They differ in audience, not in the core rules.

| Form | Audience | One entry per | Layout |
|---|---|---|---|
| **Working history** | the team and every future agent | every change (in the same commit) | one newest-first file, or one numbered file per entry (`NNNN-YYYY-MM-DD-slug.md`) |
| **Defect/fix log** | reviewers, source-license customers | defect fixed in shipped code (not refactors, features or doc changes) | one newest-first file |
| **Published narrative** | outsiders | milestone or finding, reversals included | one post per file with frontmatter |

Templates: `templates/entry-working.md`, `templates/entry-fix-log.md`, `templates/entry-post.md`. The working
history is the source for the other two; they never replace it.

## Core rules (all forms)

| Rule | Why |
|---|---|
| **An entry with every change.** For the working history, in the same commit as the change. | An entry written later loses the reasoning of the moment, and a batch of changes gets one vague entry. |
| **The timestamp comes from the clock**: `devlog.py new` stamps it, or `date "+%Y-%m-%d %H:%M %Z"`. Never a time you estimated or were told approximately ("around 4:30"). | Estimated stamps were caught wrong twice in one day. Readers reconstruct order and duration from them. *(Practice — not yet validated: a prose rule alone did not hold; no enforced check yet.)* |
| **A correction is a NEW entry** that names the entry it overturns. Never edit, delete or renumber an old one, even to "fix" a wrong cause. | The log records what was believed when. A rewritten entry hides the mistake, and commits and docs that cite it now point at different text. *(Practice — not yet validated: no measured effect.)* |
| **Keep failures, dead ends and overturned verdicts.** | "Tried X, failed because Y" saves the most time later and is the entry most often skipped. *(Practice — not yet validated: no measured effect.)* |
| **Each entry records context, what was tried and why, the result (with numbers), the lesson, and what's next.** | Without the why and the rejected alternatives, the next agent repeats them. |
| **Only the log is historical.** Every other doc describes the current state. | History scattered into design docs rots, and those docs stop saying what is true now. *(Practice — not yet validated: no measured effect.)* |

## Writing an entry

Use the bundled script; do not hand-write a splice.

```
python references/devlog.py new --title "Shared temp dir, not the retry lock" --body-file entry.md
python references/devlog.py new --body-file entry.md      # first line of entry.md is the title
```

It numbers the entry newest + 1 and refuses a collision (`--number N` asserts the number you expect), stamps the
time from the clock, inserts at the first LINE-START `## Entry <digits>` (never inside an ordering note that
quotes the header format), and reads and writes bytes so a CRLF file stays CRLF. For a directory log it writes
`NNNN-YYYY-MM-DD-slug.md`. The log path comes from `--log` or `.devlog.json` (`templates/devlog.json`).
*Why a script: agents splicing by hand put an entry inside the ordering note, and a text-mode rewrite turned a
50-line entry into a 36,000-line whole-file diff. Read the diffstat after writing: additions only.*

`python references/devlog.py check [--from N]` validates numbering (unique, descending), headers and timestamps;
`--from` skips early entries that predate the rules (never renumber them: commits cite them).

## Using the log

1. **Session start: do NOT read the log.** Read the project's small CURRENT-STATE document instead (live state,
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
| **1. Record** | the log: everything, hypotheses and wrong turns included | an entry with every change |
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

Paste `templates/CLAUDE-devlog.md` into the project's `CLAUDE.md`, and install `references/devlog_guard.py` as a
PreToolUse hook (`templates/settings.json`), with `.devlog.json` at the repo root.

- **Register it with matcher `Bash|PowerShell` and NO `if` filter.** *Why: `if: Bash(git commit*)` does not match
  `git add -A && git commit …`, the usual agent form; measured on a sibling hook, the filter silenced it in most
  sessions. The script finds `git commit` anywhere in the command and exits at once on anything else.* *(Practice — not yet validated: the filter's effect was measured in a sandbox, not yet in production.)*
- **It asks; it does not deny.** *Why: a message-only amend or a deliberate exception needs a person to wave it
  through, not a refusal the agent learns to route around.*
- It is silent outside repos with `.devlog.json`, fails open on any error, and `--self-test` proves each branch.

## Red flags

- A header time you typed rather than read from the clock.
- Opening an old entry to fix its conclusion.
- "I'll write the entries at the end of the session."
- A "history" or "changes" section growing in a design doc.
- A hand-written insertion (`text.index("## Entry ")`, `open(p, "w")`) instead of `devlog.py new`.
- A hook registered with `if: Bash(git commit*)`.
- A learnings file, a skill rule or a hook built from a consolidation run that no validator has ruled on.
- A refuted candidate deleted instead of marked REFUTED.
