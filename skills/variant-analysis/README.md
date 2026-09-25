# variant-analysis

When you fix a bug, the same mistake usually lives somewhere else too: in a copy-pasted neighbor, at another call
site of the same API, in the other arm of the same dispatch, or in a second copy of the same rule. This skill makes
Claude hunt for those siblings systematically as soon as a defect is confirmed. It states the bug as a searchable
*mechanism*, searches for it at textual, structural and semantic levels, probes every candidate with a minimal
repro, and writes a sweep report in which "no variants found" is backed by evidence rather than asserted.

It is adapted from Trail of Bits' variant-analysis skill (see [Credits / license](#credits--license)) and retargeted
from security bugs to correctness bugs of every kind.

## When Claude uses it

Skills load automatically when the task matches their `description`. This one triggers:

- immediately after a defect is confirmed (reproduced and root-caused): a wrong answer, a crash, a security hole or
  a bad pattern, before or together with the fix;
- when someone asks "are there others like this?", "is this the same bug?" or "did we fix all of them?";
- when a set of look-alike candidates needs triage against one known root cause.

It is **not** for initial discovery with no bug in hand (use a review or audit for that), nor for explaining
unfamiliar code. You can also invoke it explicitly — name it in your request or pick it from the `/` menu — or by asking in words ("sweep for
variants of this bug").

## What it does

| Step | What happens |
|---|---|
| 1. Name the mechanism | Restate the symptom as a mechanism in one of three templates: *data flow* ("value of kind K reaches OPERATION without REQUIRED STEP"), *invariant* ("COMPONENT must PROPERTY; it violates that when CONDITION") or *duplication* ("RULE is written in N places; place P disagrees"). Then list the expansion axes: other call sites, other names for the same role, other dispatch arms, other copies of the rule, edge values the repro skipped, and name/contract mismatches. Every axis must name identifiers that actually exist in the code. |
| 2. Search at three levels | Start with an exact query that hits only the known instance, then generalize one element at a time, reading every new hit. Levels are textual (`rg`, `git grep`), structural (Roslyn syntax walker, ANTLR listener, tree-sitter query, Semgrep) and semantic (Roslyn `SemanticModel`, CodeQL, Semgrep taint). Search the whole repository, including tests, generator sources such as grammars and templates, and docs. |
| 3. Which arm did you fix? | Identify the dispatch and all its arms (exact vs. approximate, read vs. write, encode vs. decode, fast vs. slow path, one grammar edition vs. another ...), record which one was fixed, and probe each of the others. |
| 4. One rule in one place | Search for the rule itself (constant, table, condition, ordering, error message). If it lives in N places, extracting it into one place is the fix, paired with a drift test. |
| 5. Probe every candidate | Argue against each hit first, then run the smallest input that would expose it, asserting the correct value derived from the contract or spec. Classify it as *confirmed*, *cleared* (with the reason) or *latent* (unreachable today but unprotected). |
| 6. Report the sweep | Fill in the sweep template: the mechanism, the dispatch arms, the rule copies, and a table of every query run verbatim with its scope, hit count and classification. Include a calibration line showing the query hit the original instance before the fix, and a regression guard. File each confirmed or latent variant in the project's work register. |

The skill closes with three worked examples (a .NET `Math.Round` midpoint bug, a grammar that fixes the order of
clauses the language allows in any order, and a pagination off-by-one) and a list of the seven reasons hunts fail.

[`references/search-recipes.md`](references/search-recipes.md) holds throwaway starting points for the structural
and semantic levels:

- a single-file Roslyn syntax walker, run with `dotnet run walker.cs -- <repo-root>`;
- Roslyn semantic queries via `MSBuildWorkspace` and `SymbolFinder` (references, overrides and implementations,
  enum switches missing members, field writes);
- ANTLR recipes for grammar rule siblings, rule shapes, corpus coverage of alternatives, and semantic predicates;
- a tree-sitter query, run with `tree-sitter query query.scm <files>`;
- a Semgrep rule, with guidance on generalizing it one element at a time;
- textual reconnaissance with `rg` and `git log -S`.

## Why it works this way

- **Mechanism, not symptom.** You can only search for a mechanism. A query built from the error text finds the
  error text. If you cannot point at the mechanism in the code, the skill says you have a story, not a diagnosis,
  and sends you back to debugging.
- **Start exact, generalize one step at a time.** If the exact query misses the known instance, the bug has been
  misread and every broader query is calibrated wrong. Generalizing several things at once makes the noise
  impossible to attribute. Stop when more than half the hits are noise, and back up.
- **Whole repository, including docs.** Narrow scope is the first listed reason hunts fail, and a wrong rule
  stated in a doc gets re-implemented.
- **Check every dispatch arm.** A repro exercises one arm and the existing tests usually follow the same arm, so the
  other arm survives a green suite. If a second arm has the same defect, the arms don't share their rule, and the
  fix is to make them share it.
- **Extract the rule instead of patching its copies.** When one case fails while its siblings pass, the usual cause
  is a rule written in more than one place. Patching N copies leaves N places to drift again.
- **A candidate is not a finding until something runs.** Arguing against each hit and then probing it separates
  real variants from look-alikes. Expected values come from the contract or spec, not from current output.
  Code with no callers is *latent*, not cleared: the sweep is how you find it before a caller arrives.
- **A zero result must be calibrated.** "No variants" means something only if the query could have found one, so
  the report records that each query hit the original instance before the fix, and records failed queries too.

## Using it in your project

A repository specializes the skill by adding a section to its `CLAUDE.md`:

```markdown
## Variant analysis
- Structural tooling: <Roslyn walker project path / grammar listener harness / semgrep config>
- Probe harness: <how to run a one-file repro>
- File variants to: <work register path or tracker>
```

Prerequisites depend on the level you search at: `rg` and `git` for textual searches; for structural and semantic
searches, whichever of the .NET SDK (Roslyn packages), ANTLR, the tree-sitter CLI, Semgrep or CodeQL fits your
codebase.

How it composes with sibling skills:

- **engineering-standards** is the bar. Its "every bug is a pattern", "two-arm dispatch" and "one rule in one place"
  rules are Steps 1 to 4 here, and its root-cause rule forbids calling a variant "a quirk" or working around it.
- **review** runs this skill in its sibling-sweep step for each confirmed finding.
- **roslyn-analysis** provides symbol sweeps and structural clone detection for C# codebases.

See [SKILL.md](SKILL.md) for the full rules.

## Files

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The skill: the six steps, report template, examples, failure list, standards and project hooks. |
| [`references/search-recipes.md`](references/search-recipes.md) | Ready-to-edit Roslyn, ANTLR, tree-sitter, Semgrep and textual search recipes. |
| [`LICENSE`](LICENSE) | Creative Commons Attribution-ShareAlike 4.0 International, covering this directory only. |
| `README.md` | This file. |

## Credits / license

This skill is adapted from [trailofbits/skills](https://github.com/trailofbits/skills),
`plugins/variant-analysis/skills/variant-analysis/`, and is distributed under
**CC-BY-SA 4.0**; the [`LICENSE`](LICENSE) in this directory covers this skill only. The search recipes file is
adapted from that skill's `references/searching.md`, with new recipes.

Changes from the original, as stated in `SKILL.md`: aimed at all correctness bugs rather than only security bugs;
the root-cause step became "name the mechanism"; the dispatch-arm and one-rule-in-one-place checks were added;
Roslyn, ANTLR and tree-sitter structural recipes were added; every candidate needs a minimal-repro probe; the
report became a sweep record in which a zero result counts as evidence; the CodeQL/Semgrep resource files and the
workflow were dropped.

The rest of the repository is MIT-licensed; this directory is the exception, and adaptations of it stay
share-alike.
