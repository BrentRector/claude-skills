# devlog

Claude agents forget everything at the end of a session. A development log is how a project remembers: what
changed, what was tried, why, and what went wrong. This skill has Claude keep that log as a standing rule, write
each entry the same way every time, and use the log before repeating work.

The full rules are in [`SKILL.md`](SKILL.md). This page explains what the skill does and why each rule exists.

## When Claude uses it

The skill's description tells Claude to load it when a project keeps, or should keep, a development log, a work
history or a fix log. That covers setting one up, writing or correcting an entry, recording an approach that failed
or was overturned, checking whether something was tried before, enforcing an entry with every commit, and
consolidating a long log into candidate learnings and validating them. Asking "add the devlog entry for this",
"set up a devlog for this repo" or "have we tried this before?" is usually enough. You can also name the skill.

## Three forms, chosen by purpose

The skill grew out of three logs kept across several projects. Each one serves a different reader.

| Form | Who reads it | What gets an entry | Template |
|---|---|---|---|
| **Working history** | the team and every future agent | every change, in the same commit | [`entry-working.md`](templates/entry-working.md) |
| **Defect/fix log** | reviewers and source-license customers | each defect fixed in shipped code: what a user saw, the cause, the fix, why that shape and not an easier one, and how the guard was proven able to fail. Refactors, features and doc changes are left out. | [`entry-fix-log.md`](templates/entry-fix-log.md) |
| **Published narrative** | outsiders, as posts on a site | each milestone or finding, including reversals (one series has a post whose title says the earlier mechanism was overturned) | [`entry-post.md`](templates/entry-post.md) |

The working history is the record, and the other two are written from it. It can be one newest-first file, or a
directory of numbered files named `NNNN-YYYY-MM-DD-slug.md`. The script handles both layouts.

## The core rules, and why

| Rule | Why |
|---|---|
| An entry with every change, in the same commit | Written later, an entry loses the reasoning of the moment, and a batch of changes ends up with one vague entry. |
| The timestamp comes from the clock (`date`, or the script) | Estimated timestamps were caught wrong twice in one day. Readers use the stamps to work out order and duration. |
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
produces claims, not facts.

## What's included

| File | What it does |
|---|---|
| [`references/devlog.py`](references/devlog.py) | `new` adds the next entry. The number is the newest plus one, and a collision is refused. The time comes from the clock. The entry goes above the newest one, never inside a note that quotes the header format. The file's line endings are kept (CRLF stays CRLF). `check` validates numbering, headers and timestamps; `--from N` skips early entries that predate the rules. `search` prints matching entries with their headers. It works on either layout, uses only the standard library, and has a `--self-test`. |
| [`references/devlog_guard.py`](references/devlog_guard.py) | A PreToolUse hook. When a shell command runs `git commit` and the commit won't include a devlog change, it asks you to confirm. It counts a devlog change that the same command stages (`git add -A && git commit`, `commit -a`), and one already in HEAD for `--amend`. It is silent in repositories without `.devlog.json`, fails open on any error, and has a `--self-test`. |
| [`templates/CLAUDE-devlog.md`](templates/CLAUDE-devlog.md) | The standing rule block for your `CLAUDE.md`, with the reason for each rule. |
| [`templates/settings.json`](templates/settings.json), [`templates/devlog.json`](templates/devlog.json) | The hook registration, and the config file that names the log for both scripts. |
| `templates/entry-*.md` | The three entry forms. |
| [`templates/consolidate-brief.md`](templates/consolidate-brief.md) | The consolidation brief: one agent turns the log into numbered CANDIDATE learnings in `LEARNINGS-CANDIDATES.md`. |
| [`templates/validate-brief.md`](templates/validate-brief.md) | The validation brief: one adversarial agent per batch rules each candidate VETTED, UNPROVEN or REFUTED with its evidence; then `LEARNINGS.md` is written from the vetted ones only. |

## Setting it up

1. Copy `references/devlog.py` and `references/devlog_guard.py` into the project (for example `.claude/hooks/`),
   and `templates/devlog.json` to `.devlog.json` at the repository root. Set `log` to your file or directory.
2. Paste `templates/CLAUDE-devlog.md` into `CLAUDE.md`, with the script path filled in.
3. Merge `templates/settings.json` into `.claude/settings.json`. **Register the hook without an `if` filter.** An
   `if: Bash(git commit*)` filter does not match `git add -A && git commit …`, which is how agents usually commit.
   On a sibling hook, the filter was measured silencing it in most sessions. The script finds `git commit` anywhere
   in the command and returns at once for every other command.
4. Run `python devlog.py --self-test` and `python devlog_guard.py --self-test`, then `python devlog.py check`
   (with `--from N` if the early entries predate the header format).

## Measured

| Fact | Where it comes from |
|---|---|
| The working history reached **1,750+ entries in about six months**, one per change, written by agents under this rule and enforced by the hook | the largest project the skill came from |
| One consolidation run produced **145 CANDIDATE learnings (not yet validated) and 15 open problems in about 30 minutes** | the brief in `consolidate-brief.md` |
| The contradiction that run surfaced **was real**: a skill documented a setting the tool silently ignores. It was fixed in this repository's 1.10.2 | the root README's "What's new in 1.10.2" |
| Estimated timestamps were caught wrong **twice in one day**; a hand-written splice put an entry **inside the ordering note**; a text-mode write turned a 50-line entry into a **36,000-line diff** | the traps `devlog.py new` closes |

In this repository's eval (3 runs per arm), Claude without the skill usually registered the hook with an `if`
filter and always made it deny instead of ask. It stamped the header "16:30" from "around 4:30", wrote its own
insertion code, and left the not-yet-acted-on list out of every consolidation brief. With the skill it did none of
these. See [`evals/README.md`](../../evals/README.md).
