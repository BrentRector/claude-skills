# devlog

Claude agents forget everything at the end of a session. A development log is how a project remembers: what
changed, what was tried, why, and what went wrong. This skill has Claude keep that log as a standing rule, write
each entry the same way every time, and use the log before repeating work.

The full rules are in [`SKILL.md`](SKILL.md). This page explains what the skill does and why each rule exists.

## When Claude uses it

The skill's description tells Claude to load it when a project keeps, or should keep, a development log, a work
history or a fix log. That covers setting one up, writing or correcting an entry, recording an approach that failed
or was overturned, checking whether something was tried before, enforcing one entry per landing, and
consolidating a long log into candidate learnings and validating them. Asking "add the devlog entry for this",
"set up a devlog for this repo" or "have we tried this before?" is usually enough. You can also name the skill.

## Three forms, chosen by purpose

The skill grew out of three logs kept across several projects. Each one serves a different reader.

| Form | Who reads it | What gets an entry | Template |
|---|---|---|---|
| **Working history** | the team and every future agent | every landing (one pull request), as its own file in the branch | [`entry-working.md`](templates/entry-working.md) |
| **Defect/fix log** | reviewers and source-license customers | each defect fixed in shipped code: what a user saw, the cause, the fix, why that shape and not an easier one, and how the guard was proven able to fail. Refactors, features and doc changes are left out. | [`entry-fix-log.md`](templates/entry-fix-log.md) |
| **Published narrative** | outsiders, as posts on a site | each milestone or finding, including reversals (one series has a post whose title says the earlier mechanism was overturned) | [`entry-post.md`](templates/entry-post.md) |

The working history is the record, and the other two are written from it. It is a directory with one file per entry
(`devlog/NNNN-slug.md`). The implementer writes `pending-<slug>.md` in its branch; the enqueue step stamps the number
and the time after the final rebase, so number order is landing order; the newest-first document is RENDERED on
demand and never committed. Two pull requests in a merge queue therefore never touch the same log file. A project with
a single newest-first file migrates it once (`devlog.py migrate`).

## The core rules, and why

| Rule | Why |
|---|---|
| An entry with every landing, as its own file in the branch | Written later, an entry loses the reasoning of the moment, and a batch of changes ends up with one vague entry. |
| One file per entry, numbered at enqueue, the view rendered | Entries inserted at the top of one shared file collide when pull requests queue together, and the queue bounces the second. *(Practice — not yet validated: adopted 2026-10-11.)* |
| The timestamp comes from the clock (`date`, or the script) | Estimated timestamps were caught wrong twice in one day. Readers use the stamps to work out order and duration. *(Practice — not yet validated: a prose rule alone did not hold.)* |
| A correction is a new entry; old entries are never rewritten | The log records what was believed and when. A rewritten entry hides the mistake, and every commit or doc citing it now points at different text. |
| Failures, dead ends and overturned verdicts stay in | "We tried X; it failed because Y" is the entry that saves the most time later, and the one most often left out. |
| Each entry gives the context, what was tried and why, the result, the lesson, and what's next | Without the why and the rejected alternatives, the next agent tries them again. |
| Only the log is historical; every other doc describes the current state | History spread across design docs rots, and those docs stop saying what is true now. |

## How agents use it

- **At session start** they do NOT read the log; they read the small current-state document. The log is searched
  on demand, never loaded whole: it is written to be complete, and a large one (1,750+ entries, ~880,000 words)
  would swamp the context.
- **Before retrying an approach** they search the log (`devlog.py search`), and if it was tried before, they cite
  that entry and say what is different this time.
- **Periodically** the log is turned into learnings in three stages, described below.

## From log to learnings: record, consolidate, validate

1. **Record.** The log records everything, including hypotheses that later turn out wrong.
2. **Consolidate.** One agent turns the log into `LEARNINGS-CANDIDATES.md` using
   [`consolidate-brief.md`](templates/consolidate-brief.md). Each CANDIDATE learning gives the problem, the root
   cause, the fix and where it lives, the evidence and the date. Candidates are grouped by theme, oldest first.
   Reversals stay in with the correction labeled, and the file ends with an open-problems list and a list of lessons
   not yet acted on.
3. **Validate.** A fresh agent per batch, using [`validate-brief.md`](templates/validate-brief.md), tries to
   overturn each candidate and rules it **VETTED**, **UNPROVEN** or **REFUTED**. VETTED requires all four: the root
   cause is confirmed rather than a hypothesis later overturned; the evidence is re-checked against primary sources;
   no later log entry contradicts it; and the fix has been used and shown useful (a measured effect, or sustained
   use with no reversal). UNPROVEN names the missing evidence, and REFUTED cites the contradicting source.

Only VETTED learnings enter `LEARNINGS.md`, each recording its validation (date, sources, proof of use), and only
vetted learnings are encoded into skills or rules. Refuted candidates are kept in the record, marked refuted, and are
never silently dropped.

**Why a separate validation stage:** a log records hypotheses as well as conclusions, and some are later refuted:
in one project a published explanation of an observed silence was refuted the same day. A learnings file compiled
straight from the log inherits those errors, and a skill that encodes them spreads them. Consolidation alone
produces claims, not facts. The first validation of those 145 vetted 46, left 90 unproven and refuted 9, and independent refuters overturned 21 of the 67 that a first validator had vetted.

## What's included

| File | What it does |
|---|---|
| [`references/devlog.py`](references/devlog.py) | `new` writes the branch's `pending-<slug>.md`. `stamp` (the enqueue step) gives it the next free number, counting the default branch too, and the time from the clock, and renames it `NNNN-<slug>.md`. `check` validates every entry; with `--base` it checks the landing (one stamped entry added, none pending, no old entry changed, no number reused). `render` prints the newest-first view, `next` the next number, `search` the matching entries. `migrate` splits a single-file log once, LF, verified by reading every file back. Files are written LF. Standard library only (`git` for `--base`), with a `--self-test`. |
| [`references/devlog_guard.py`](references/devlog_guard.py) | A PreToolUse hook. When a shell command runs `gh pr create` or `gh pr merge` and the branch adds no stamped entry over its base (or only a pending one), it asks you to confirm. It is silent in repositories without `.devlog.json`, fails open on any error (an unresolvable base included: CI's check decides), and has a `--self-test`. |
| [`templates/CLAUDE-devlog.md`](templates/CLAUDE-devlog.md) | The standing rule block for your `CLAUDE.md`, with the reason for each rule. |
| [`templates/settings.json`](templates/settings.json), [`templates/devlog.json`](templates/devlog.json) | The hook registration, and the config file that names the log for both scripts. |
| `templates/entry-*.md` | The three entry forms. |
| [`templates/consolidate-brief.md`](templates/consolidate-brief.md) | The consolidation brief: one agent turns the log into numbered CANDIDATE learnings in `LEARNINGS-CANDIDATES.md`. |
| [`templates/validate-brief.md`](templates/validate-brief.md) | The validation brief: one adversarial agent per batch rules each candidate VETTED, UNPROVEN or REFUTED with its evidence; then `LEARNINGS.md` is written from the vetted ones only. |

## Setting it up

1. Copy `references/devlog.py` and `references/devlog_guard.py` into the project (for example `.claude/hooks/`),
   and `templates/devlog.json` to `.devlog.json` at the repository root. Set `log` to your entry directory and
   `base` to your default branch's remote ref. With an existing single-file log, run `devlog.py migrate --from
   <file>` once and delete the file in the same landing.
2. Paste `templates/CLAUDE-devlog.md` into `CLAUDE.md`, with the script path filled in.
3. Merge `templates/settings.json` into `.claude/settings.json`. **Register the hook without an `if` filter.** An
   `if` filter does not match a chained command (`git push … && gh pr create …`), which is how agents usually run it.
   On a sibling hook, the filter was measured silencing it in most sessions. The script finds the command anywhere
   and returns at once for every other command. *(Practice — not yet validated: the filter's effect was measured in a sandbox, not yet in production.)*
4. Run `python devlog.py --self-test` and `python devlog_guard.py --self-test`, then `python devlog.py check`
   (with `--from N` if the early entries predate the header format).
5. Add `devlog.py check --base <base> --one` to CI's pull-request job and `devlog.py check --base <merge group base
   sha>` to its merge-group job, gitignore the rendered view, and have the enqueue step run `stamp` and `check`.

## Measured

| Fact | Where it comes from |
|---|---|
| The working history reached **1,750+ entries in about six months**, one per change, written by agents under this rule and enforced by the hook (as one newest-first CRLF file, until it moved to one file per entry with a merge queue in 2026-10) | the largest project the skill came from |
| One consolidation run produced **145 CANDIDATE learnings (not yet validated) and 15 open problems in about 30 minutes** | the brief in `consolidate-brief.md` |
| The contradiction that run surfaced **was real**: a skill documented a setting the tool silently ignores. It was fixed in this repository's 1.10.2 | the root README's "What's new in 1.10.2" |
| The first validation run over those 145 candidates vetted **46**, left **90** unproven and refuted **9**; independent refuters overturned **21 of the 67** that a first validator had vetted | [`LEARNINGS.md`](../../LEARNINGS.md) |
| Estimated timestamps were caught wrong **twice in one day**; a hand-written splice put an entry **inside the ordering note**; a text-mode write turned a 50-line entry into a **36,000-line diff** | the traps `devlog.py new` closes |

In this repository's eval (3 runs per arm), Claude without the skill usually registered the hook with an `if`
filter and always made it deny instead of ask. It stamped the header "16:30" from "around 4:30", wrote its own
insertion code, and left the not-yet-acted-on list out of every consolidation brief. With the skill it did none of
these. See [`evals/README.md`](../../evals/README.md).
