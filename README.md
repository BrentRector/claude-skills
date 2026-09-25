# Brent Rector's Claude Code skills

Engineering-discipline skills for [Claude Code](https://code.claude.com), distilled from long-running production
work — a standards-conformant compiler built largely by Claude agents, a commercial .NET tool, and several smaller
projects. Each skill encodes rules that were learned the expensive way; the *why* travels with every rule.

## Install

```
/plugin marketplace add BrentRector/claude-skills
/plugin install brent-tools@brentrector-claude-skills
```

## How skills work

A **skill** is a folder with a `SKILL.md`: YAML frontmatter (a `name` and a `description` of when to use it) followed by
instructions written *to Claude*. Claude Code reads every installed skill's description; when a task matches one, it
loads the full instructions and follows them — you don't have to invoke anything. You can also ask for a skill by name
("run the review skill"), or type `/` in Claude Code to pick it from the list of available skills. Supporting files
live beside it in `references/` — templates, checklists and small scripts the instructions call.

Every skill folder here also has a **`README.md` written for people**: what the skill does, how it runs, and — most
importantly — *why* each rule exists, since every rule traces back to a failure it prevents. Start there; the
`SKILL.md` holds the complete rules.

An **agent** in `agents/` is a subagent definition — a markdown file whose frontmatter names the agent, says when to
use it and which tools it may use. Claude can launch one as a focused, independent reviewer.

## Skills

**The bar**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`engineering-standards`](skills/engineering-standards/) | writing, changing, designing or reviewing production code | Commercial-grade, decades-maintainable code. No god classes; one mechanism per job; one rule in one place; fix the root cause, never paper over; **every bug is a pattern**; implement the complete feature (tests verify, they don't scope); re-architect when the right structure demands it, even if the build breaks on the way. |

**Finding defects**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`review`](skills/review/) | reviewing a diff, branch or PR | Four dimensions (architecture · full code · performance · duplication/efficiency) as parallel reviewers, plus specialist agents; every finding carries a concrete failure scenario; an adversarial skeptic tries to refute each one; confirmed bugs trigger a sibling sweep. |
| [`variant-analysis`](skills/variant-analysis/) | right after any defect is confirmed | Name the mechanism, not the symptom; textual, structural (Roslyn, ANTLR, tree-sitter, Semgrep) and semantic queries; "which arm of the dispatch did you fix?"; a probe per candidate; a sweep report in which zero hits is evidence. |

**Specs and standards**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`spec-oracle`](skills/spec-oracle/) | behavior is governed by a written standard (language standards, RFCs, file formats, ECMA-335 …) | The spec is the only oracle; derive the expected result *before* reading the code; every citation checked mechanically. Includes a small generic citation checker. |
| [`spec-compliance-audit`](skills/spec-compliance-audit/) | auditing a whole implementation against a whole standard | A rule catalog, one agent per rule/subject, a verdict vocabulary, refuters on every closing verdict, a traceability inventory whose GAP count is the progress metric. |

**Testing and .NET**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`test-gate`](skills/test-gate/) | before every commit, merge or push | Tiered gates; read the verdict line, not the exit code; filters that silently match nothing; confirm new tests actually ran; CI for the exact pushed commit is the final word. |
| [`dotnet-engineering`](skills/dotnet-engineering/) | .NET / C# work | Latest .NET and C#, strong types, warnings as errors; `dotnet test` filter traps; test gaps and smells; BenchmarkDotNet with a witness; binlog failure analysis; trimming/Native AOT; NuGet trusted publishing. |
| [`roslyn-analysis`](skills/roslyn-analysis/) | C# duplication review, sibling sweeps, mechanical refactors, verifying built assemblies | Structural clone detection, symbol sweeps (every implementation/override/reference), a safe rewriter harness (dry-run, preserves encoding and line endings, refuses unparseable output), metadata-only assembly and IL inspection. |

**Running agents at scale**

| Skill | Use it when | What it enforces |
|---|---|---|
| [`agent-fleet`](skills/agent-fleet/) | dispatching many parallel subagents on a long campaign | One self-contained input per agent; checkpoint to disk; fresh agents from checkpoints; concurrency and token budgets; land finished work first; adversarial refuters; cost per unit decides the lane. |
| [`claude-cloud-sessions`](skills/claude-cloud-sessions/) | running work in Claude Code cloud sessions | Environment setup scripts and snapshots; multi-repo sessions and hooks; private-repo access; launch surfaces and **billing** (measured, including where it differs from the docs); stopping cleanly before a credit runs out. Includes a setup-script template. |

`engineering-standards` is the bar every other skill applies in its own context — each has a short *Standards*
section saying how.

## Agents

Specialist reviewers the `review` skill adds when a change calls for them:
[`silent-failure-hunter`](agents/silent-failure-hunter.md) (swallowed errors, fallbacks, silent wrong answers),
[`pr-test-analyzer`](agents/pr-test-analyzer.md) (scope, oracle, discovery and strength of tests),
[`type-design-analyzer`](agents/type-design-analyzer.md) (god classes, stringly-typed state, illegal states),
[`comment-analyzer`](agents/comment-analyzer.md) (comments whose claims or citations don't hold).

## How the skills fit together

- **`engineering-standards` is the bar.** Every other skill applies it in its own domain (each has a short *Standards*
  section saying how).
- **Before building against a standard:** `spec-oracle` derives the expected behavior and checks the citation first;
  `spec-compliance-audit` scales that to a whole implementation against a whole standard, using the same citation
  checker and the refuter pattern from `agent-fleet`.
- **Changing code:** `test-gate` picks and reads the right gate before each commit and push; `dotnet-engineering` adds
  the .NET-specific bar; `engineering-standards`' `rule_index.py` lists the structural rules that govern a file before
  you edit it.
- **Reviewing:** `review` runs the four dimensions with the specialist `agents/`; a confirmed defect hands off to
  `variant-analysis`, which sweeps for its siblings (using `roslyn-analysis` for compiler-accurate C# queries).
- **At scale:** `agent-fleet` runs many agents on a long campaign without losing work to limits, and
  `claude-cloud-sessions` covers running that work in Claude Code cloud sessions.

## Adapting to your project

Most skills end with **Project hooks** (and each skill's README says what a project can supply): your repo's `CLAUDE.md` supplies its commands, tightens or adds rules,
and wins on conflict — no fork needed. For example, a `## Review rules` block can add a spec-conformance reviewer,
and a `## Testing` section records gate commands and baseline counts.

## Regression evals

[`evals/`](evals/README.md) is a `claude plugin eval` suite with one or two cases per skill and one per agent. Each
case runs with the plugin and with no plugin at all, and it is kept only if the plugin arm scores higher. That makes
it a regression test: a skill edit that stops changing Claude's behavior shows up as a shrinking Δ. To run it:
`claude plugin eval . -j 4 --no-publish --threshold 0`. A skill change ships with its eval; see the
[evals README](evals/README.md) for the rule, how to read the delta, and the cases dropped because Claude already
passed them without the plugin.

## Credits and licenses

This repository is MIT-licensed ([LICENSE](LICENSE)) **except** where a directory says otherwise:

| Path | Adapted from | License |
|---|---|---|
| `skills/spec-compliance-audit/`, `skills/variant-analysis/` | [trailofbits/skills](https://github.com/trailofbits/skills) | **CC-BY-SA 4.0** — the `LICENSE` in each directory covers it; adaptations stay share-alike |
| `agents/` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) `pr-review-toolkit` | Apache-2.0 — see [NOTICE](NOTICE) and [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt) |
| `skills/dotnet-engineering/` | [dotnet/skills](https://github.com/dotnet/skills) | MIT — see its `references/THIRD-PARTY-NOTICES.md` |
| `skills/roslyn-analysis/` | [glennawatson/CSharpAgentSkills](https://github.com/glennawatson/CSharpAgentSkills) (approach; helper code rewritten after vetting) | MIT — see its `references/THIRD-PARTY-NOTICES.md` |

The review skill's triage step and two-axis (scale × consequence) calibration come from
[carlymr/carlys-claude-skills](https://github.com/carlymr/carlys-claude-skills).
