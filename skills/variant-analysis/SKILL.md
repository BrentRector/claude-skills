---
name: variant-analysis
description: Use immediately after any defect is confirmed - a wrong answer, crash, security hole, or bad pattern - and whenever someone asks "are there others like this?" or "is this the same bug?". Names the mechanism rather than the symptom, derives textual, structural (Roslyn, ANTLR, tree-sitter, Semgrep) and semantic queries, checks the other arms of the dispatch and every place the same rule is written, probes each candidate with a minimal repro, and reports the sweep so a zero result is evidence. Not for initial discovery with no bug in hand.
---

> **Attribution.** Adapted from [trailofbits/skills](https://github.com/trailofbits/skills)
> `plugins/variant-analysis/skills/variant-analysis/` (CC-BY-SA 4.0; see `LICENSE` in this directory, which
> covers this skill only). Changes: aimed at all correctness bugs rather than only security bugs; the
> root-cause step became "name the mechanism"; added the dispatch-arm and one-rule-in-one-place checks;
> added Roslyn, ANTLR and tree-sitter structural recipes; every candidate needs a minimal-repro probe; the
> report became a sweep record in which a zero result counts as evidence; the CodeQL/Semgrep resource files
> and the workflow were dropped. This adapted skill is distributed under CC-BY-SA 4.0.

# Variant analysis

**Every bug is a pattern.** Once a defect is confirmed, it is one instance of a mechanism, and the same mistake
usually lives elsewhere: in a copy-pasted neighbor, at another call site of the same API, in the other arm of the
same dispatch, or in a second copy of the same rule. The fix is not done until the sweep is done, and the sweep is
not done until you can show the queries you ran and what each one found.

## When to use

- Right after a defect is confirmed (reproduced, root-caused), before or with the fix. Sweep in the same change.
- When someone asks "are there others like this?", "is this the same bug?", "did we fix all of them?"
- When a look-alike set of candidates needs triage against one known root cause.

**Not for:** initial discovery with no bug in hand (use a review or audit), or explaining unfamiliar code.

## Step 1: Name the mechanism, not the symptom

The symptom is what the user saw ("a negative amount prints without its sign"). The mechanism is why the code
is wrong ("the sign-handling rule is applied in the value-producing path but not in the validating path"). You can
only search for a mechanism. Fill in one of these:

> **Data flow:** "[VALUE of kind K] reaches [OPERATION] without [REQUIRED STEP]."
> **Invariant:** "[COMPONENT] must [PROPERTY]; it violates that when [CONDITION]."
> **Duplication:** "[RULE] is written in N places; place P disagrees with the others."

If you cannot point at the mechanism in this code, you have a story, not a diagnosis. Go back to debugging.

Then list the **expansion axes**: the independent directions in which a variant could hide. Each must name
concrete identifiers or constructs that exist in the code (grep for them before you claim them):

1. **Same operation, other call sites.** Every caller of the API or helper that was misused.
2. **Same role, other names.** `IsSigned` also means `HasSign` and `SignSeparate`; `Read` also means `Peek`.
3. **Other arms of the same dispatch** (Step 3).
4. **Other copies of the same rule** (Step 4).
5. **Edge values the repro skipped.** Null on both sides, empty versus null, zero, the maximum and minimum of the
   type, negative zero, a collection with one element, the first and last iteration.
6. **Name/contract mismatch.** Functions whose return value contradicts their name or doc comment. Every caller
   of such a function is a candidate.

## Step 2: Search at three levels, one abstraction at a time

Start from an **exact match** that hits only the known instance. If it misses, you have misread the bug, and
everything built on it is calibrated wrong. Then generalize **one element per step**, run the query, and read
every new hit before the next step. Stop climbing when more than half the hits are noise, and back up.

| Level | Tool | Finds | Misses |
|---|---|---|---|
| Textual | `rg`, `git grep` | copy-paste, same identifiers, comments and docs repeating the rule | renamed variables, different formatting, semantics |
| Structural | Roslyn syntax walker, ANTLR listener, tree-sitter query, Semgrep | same shape under any names; every `switch` over the enum; every rule alternative | type-driven and cross-procedure flow |
| Semantic | Roslyn `SemanticModel`, CodeQL, Semgrep taint | every call resolving to the symbol, every read of a field, value flow | code that does not build |

Search the **whole repository root**, never only the module where the bug was found. Include tests, generated
code sources (templates, grammars), and docs, because a wrong rule stated in a doc gets re-implemented. See
[references/search-recipes.md](references/search-recipes.md) for ready-to-edit Roslyn, ANTLR, tree-sitter and
Semgrep recipes.

## Step 3: Which arm did you fix?

Most dispatches have two or more arms: exact versus approximate, validating versus value-producing, read versus
write, encode versus decode, fast path versus slow path, debug versus release, signed versus unsigned, the grammar
alternative for one edition versus another. A repro exercises one arm. The existing tests usually follow the same
arm. The other arm survives a green suite.

For every fix, write down: *the dispatch is at ___; its arms are ___; I fixed ___; the others are ___, and here is
the probe that shows each one is correct.* If a second arm has the same defect, the arms do not share their rule,
so restructure them to share it rather than patching both (Step 4).

## Step 4: One rule in one place

When a single case fails while its siblings pass, the usual cause is **one rule written down in more than one
place**, with one copy that disagrees. Search for the rule, not the construct: the constant, the table, the
condition, the ordering, the error message. Look in code, tests, generated sources and docs alike.

If the rule lives in N places, extracting it into one place *is* the fix. Patching each copy leaves N places to
drift again. Pair the extraction with a drift test that fails if a second copy reappears or if two consumers
disagree.

## Step 5: Probe every candidate with a minimal repro

A candidate is not a finding until something runs. For each hit:

1. **Argue against it.** Read the surrounding function, its callers and the types involved, and look for what
   makes it safe: an earlier guard, a type that makes the bad value unreachable, a normalizing step upstream.
2. **Write the smallest input that would expose it** (a unit test, a five-line source file, a one-record fixture)
   and run it. Assert the correct value, not merely that it ran. Derive the expected value from the contract or
   spec, not from the current output.
3. **Classify it:** *confirmed* (the probe fails), *cleared* (the probe passes, with the reason recorded), or
   *latent* (unreachable today but unprotected; report at lower severity and say what would make it reachable).

Code with no callers today is not cleared. It is latent, and the sweep is exactly how you find it before a caller
arrives. Keep every probe as a regression test once it is fixed.

## Step 6: Report the sweep

The report is what turns "I swept it" from an assertion into evidence. A zero result is only meaningful if the
queries could have found something. Prove that each query hits the original instance before the fix.

```markdown
## Variant sweep: <mechanism statement>
Origin: <file:line>, fixed by <change>. Dispatch arms: <list, each marked fixed / probed OK / defect>.
Rule copies: <locations, or "one place: <location>">.

| # | Level | Query (verbatim) | Scope | Hits | Confirmed | Cleared | Latent |
|---|-------|------------------|-------|------|-----------|---------|--------|
| 1 | text  | rg -n 'IsSigned\b' --type cs | repo root | 14 | 2 | 12 | 0 |
| 2 | struct| SwitchOverEnum(NumericKind) walker | src/ | 6 | 1 | 5 | 0 |

Confirmed: <file:line, quoted code, probe, fix>.
Cleared, grouped by reason: <reason, count, e.g. "normalized upstream by X: 9">.
Calibration: query 1 hit the origin before the fix: yes.
Regression guard: <test or analyzer or CI rule derived from the best query>.
```

File every confirmed and latent variant in the project's work register, one item each, before it turns into a
paragraph of prose. Record the queries that failed alongside those that worked.

## Examples

**.NET / C#.** A `decimal` rounding bug: `Math.Round(x, 2)` used banker's rounding where the contract says
half-away-from-zero. Mechanism: "a monetary value reaches `Math.Round` without an explicit `MidpointRounding`."
Textual: `rg -n 'Math\.Round\(' --type cs`. Structural: a Roslyn walker listing every `Math.Round` invocation
with fewer than three arguments, resolved through `SemanticModel` so `using static System.Math` calls are caught
too. Arms: the formatting path (`ToString("F2")`) and the parsing path round too, so probe both. Rule copies:
three helpers each defined their own rounding. Fold them into one `Money.Round`, and add an analyzer test that
bans bare `Math.Round` on `decimal`.

**Compiler / grammar.** A statement is rejected when an optional phrase comes before a required one. Mechanism:
"the grammar rule fixes the order of clauses that the language says may appear in any order." Textual: grep the
`.g4` files for the phrase keyword. Structural: an ANTLR listener, or a pass over the grammar's own parse tree,
listing every rule whose alternatives are fixed sequences of optional clauses. The sibling statements usually
share the defect. Arms: the parser accepted it for one dialect or edition but not for another, and the semantic
checker had a second copy of the ordering rule. Probe each candidate statement with a three-line source file in
both orders.

**Generic.** An off-by-one in a pagination helper drops the last item when the count is an exact multiple of the
page size. Mechanism: "an exclusive upper bound is computed as `count / size` instead of `ceil`." Textual:
`rg -n '/ *(pageSize|size|batch)'`. Structural: a Semgrep or tree-sitter pattern for `$N / $SIZE` used as a loop
bound. Arms: forward versus reverse paging, and the server's copy of the calculation. Probe with count = 0, 1,
size, size + 1.

## Why hunts fail

1. **Narrow scope.** Only the original module was searched.
2. **Symptom search.** The query matched the error text, not the mechanism.
3. **One arm.** The sibling arm of the dispatch was never probed.
4. **Patching copies.** N copies of a rule were fixed N times instead of once.
5. **Generalizing too fast.** Several abstractions at once, so the noise cannot be attributed to any of them.
6. **Uncalibrated zero.** A query that could not have hit the original was reported as "no variants."
7. **Happy-path probes.** Null, empty, boundary and both-sides-null cases were never tried.

## Standards

The bar is the **engineering-standards** skill. Its "every bug is a pattern", "two-arm dispatch" and "one rule in
one place" rules are Steps 1 to 4 here, and its root-cause rule forbids calling a variant "a quirk" or working
around it. A sweep shaped to the smallest diff, where the defect class calls for extracting the rule, falls
short of that bar. The **review** skill's sibling-sweep step runs this skill for each confirmed finding.

## Project hooks

A repository specializes this skill by adding a section to its CLAUDE.md:

```markdown
## Variant analysis
- Structural tooling: <Roslyn walker project path / grammar listener harness / semgrep config>
- Probe harness: <how to run a one-file repro>
- File variants to: <work register path or tracker>
```
