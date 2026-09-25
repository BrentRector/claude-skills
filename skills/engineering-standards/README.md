# engineering-standards

The quality bar for production code, written down as short rules with the reason each one exists. Code written
by an agent (or a person) under time pressure drifts toward the smallest diff that makes the current test pass:
a fallback here, a second copy of a rule there, a "known limitation" instead of a fix. Each of those is cheap
today and expensive for the next decade of maintenance. This skill states the bar explicitly — commercial-grade,
maintainable by a team for years — so every change is held to it, and so anything that falls short is reported
as debt rather than as "done with caveats".

It is the floor the other skills in this repository build on: each sibling skill has a short *Standards* section
saying how these rules apply in its own context.

## When Claude uses it

The skill's description tells Claude to load it **whenever writing, changing, designing or reviewing production
code**. Skills load automatically when the description matches the task, so in practice it is in play for most
coding work. You can also ask for it directly, e.g. "hold this change to the engineering standards", or invoke
it by name in your request, or pick it from the `/` menu in Claude Code.

The skill itself says how it is used at each stage:

| Stage | What to apply |
|---|---|
| Before writing code | Read the governing spec or design, answer the structural question, decide the complete scope |
| While fixing a bug | Root cause, then sibling sweep, then the other arm of the dispatch, then a drift test |
| Before calling it done | Complete, swept, one mechanism, verified by a check seen to fail, docs current — or reported as debt |
| In review | Every rule is a finding category, even when the tests pass |

## What it does

The rules are grouped into six sections (see [`SKILL.md`](SKILL.md) for the full text):

1. **The quality bar** — production quality always; build what you would ship if you owned it for five years;
   no hacks, shims, fallbacks, dead code or leftover TODOs; latest stable language and runtime; usability,
   understanding, support and maintenance as tie-breakers.
2. **Design and structure** — no god classes; one mechanism per job; one rule in one place; change the dispatch,
   not the callers; model a rule's full shape before fixing a table; one-directional phases; typed models with
   encoding only at the boundary; build output from the model rather than patching input; use the standard tool
   for a solved problem; explicit registries instead of reflection where trimming/AOT applies; check what exists
   before proposing a design. A subsection says **when re-architecture is required, not optional**.
3. **Correctness and root cause** — fix the root cause; never alter valid input to dodge a tool bug; never
   relabel a bug a "quirk"; every bug is a pattern, so sweep for siblings; ask which arm of a two-arm dispatch
   you fixed; diagnose from evidence; keep output reproducible.
4. **Completeness** — implement the whole feature to its spec; tests verify, they do not scope; deferral is debt
   only the owner may choose; never ship a half-feature.
5. **Verification and invariants** — propose invariants and drift tests unprompted; prefer structural guarantees
   to conventions; make every new check fail once; verify values, not exit codes; every measurement carries a
   witness; reachability is measured, not deduced.
6. **Docs and honesty** — docs describe the code as it is now; history goes in commits and the changelog;
   comments carry the *why*; cite the authority in code; forensic commit messages; report calibrated to the
   evidence; say it immediately when you were wrong.

### The bundled script: `references/rule_index.py`

Section 5 asks that drift rules be surfaced *before* an edit, from one home. In this design each structural
("drift") test states its rule in its own doc comment — a C# `/// <summary>`, a Python class or module
docstring, or a JS/TS `/** ... */` block before the first `describe`/`class`. The script derives an index and a
per-file query from those comments, so the rule is never copied anywhere it could drift. It has three modes, as
its docstring states:

```
python rule_index.py --tests "tests/**/*DriftTests.cs"                 # regenerate the index (default RULES.md)
python rule_index.py --tests "tests/**/test_*invariant*.py" --check    # CI: exit 1 if stale or a test states no rule
python rule_index.py --tests "tests/**/*DriftTests.cs" src/foo/Bar.cs  # the rules that govern these files
```

- **Regenerate** — writes a generated Markdown index (default `RULES.md`) with one row per test: the test, its
  rule, and the paths it scans. A test with no doc comment is flagged as having an unwritten rule.
- **Check** (`--check`) — writes nothing; exits 1 when the index is stale, when any test states no rule, or when
  `--tests` matched no files at all (an empty filter is treated as a red, not a pass).
- **Query** (file paths as arguments) — prints the rules that govern each file. A test governs a file
  *specifically* when it names that file, or a directory at least `--depth` segments above it (default 3), as a
  string literal or through a path helper, or when its rule text names the file's basename. Tests that only
  scan a whole top-level tree are listed separately as tree-wide sweeps.

Options: `--tests GLOB` (repeatable, required), `--root DIR` (default: the git top level, else the current
directory), `--out FILE`, `--depth N`, `--path-helper REGEX` (a helper call whose string arguments are path
segments, with a capture group for the base directory, e.g. `'Paths\.(src|tests|docs)\('`), and `--check`.
It needs only Python 3 and the standard library; it calls `git` only to find the repository root.

## Why it works this way

Every rule in the skill carries its own *Why*. The main ones:

- **Production quality always, no fallbacks or shims.** Maintenance cost dwarfs the cost of writing it well once,
  and "good enough for now" is never revisited. A fallback is not robustness; it is a second, wrong answer to a
  question the first path should have answered.
- **One mechanism per job; one rule in one place.** Two coexisting mechanisms double the surface and are
  guaranteed to drift apart. Duplication is what makes a systematic bug look like a one-off — the skill's example
  is a value mapping copied into three evaluators that works in two and throws in the third.
- **Change the dispatch, not the callers.** Type checks smeared across consumers are where the next completeness
  bug hides, and "transitional" wrappers never leave.
- **A stated scope is an estimate, never a ceiling.** Minimizing today's diff maximizes tomorrow's rework. The
  skill prefers the shape that makes the *next* case automatic — its example restructures seven ambient flags
  into one copyable snapshot rather than hand-writing save/restore that every future flag would have to join —
  and accepts a short, deliberate broken build over a half-migrated codebase with two shapes.
- **Every bug is a pattern; ask which arm you fixed.** A repro exercises one arm, the existing tests follow the
  same arm, and the other arm survives a green suite. "Swept" without the search query is an assertion, not
  evidence.
- **Tests verify; they do not scope.** A slice shaped by one test fails the next real input. Parsing something
  and silently doing nothing is worse than an error, because the program runs and produces wrong results.
- **A guard that cannot fail is not a guard.** The skill's example: a test that checked a registry against the
  same reflection scan that populated it could never fail. Every new check is made to fail once, for the right
  reason, before its green is trusted.
- **Surface drift rules from one home.** The skill reports that more than 200 drift tests whose rules lived only
  in the tests were rediscovered one red gate at a time — and that copying the rules into a skill would have
  created a second copy of every rule to drift. Hence the generated index and per-file query instead.
- **Docs describe the present; honesty is calibrated.** A stale design doc tells the next implementer to build
  the rejected approach. The closing summary line is where overreach creeps in, and it is the line others act on.

## Using it in your project

The skill is the generic floor. A repository tightens or extends it in its `CLAUDE.md` (or `AGENTS.md`,
`CONTRIBUTING.md`) under a section such as:

```markdown
## Engineering standards
- Authority: <standard or spec, and the precedence when it leaves latitude>
- Architectural commitments: <settled decisions not to relitigate>
- Language/runtime: <versions, warnings-as-errors, analyzers>
- Docs that must stay current: <design docs, README, changelog, fix log>
- Work register: <the one place new defects and deferrals are filed>
```

**Project rules win on conflict.** A stricter project rule is followed; a deliberate relaxation (for example, an
explicitly throwaway prototype) is followed and noted once. Settled architectural commitments are designed
within, not reopened.

To adopt the rule index, give each structural test a doc comment stating its rule, run the regenerate mode once
to create the index, and add the `--check` mode to CI.

Related skills: [`review`](../review/README.md) treats every rule here as a finding category and uses
`rule_index.py` to list the rules governing each changed file; the other skills in this repository each apply
this bar in their own *Standards* section.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The rules and their reasons, as instructions to Claude |
| [`references/rule_index.py`](references/rule_index.py) | Generates the drift-rule index, checks it in CI, and answers "which rules govern this file?" |
