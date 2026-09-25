# Brent Rector's Claude Code skills

Engineering-discipline skills for [Claude Code](https://code.claude.com), distilled from long-running production
work — a standards-conformant compiler built largely by Claude agents, a commercial .NET tool, and several smaller
projects. Each skill encodes rules that were learned the expensive way; the *why* travels with every rule.

## Install

```
/plugin marketplace add BrentRector/claude-skills
/plugin install brent-tools@brentrector-claude-skills
```

## Skills

| Skill | Use it when | What it enforces |
|---|---|---|
| [`engineering-standards`](skills/engineering-standards/SKILL.md) | writing, changing, designing or reviewing production code | The bar: commercial-grade, decades-maintainable code. No god classes; one mechanism per job; one rule in one place; fix the root cause, never paper over; **every bug is a pattern** — sweep its siblings; implement the complete feature (tests verify, they don't scope); re-architect when the right structure demands it, even if the build breaks on the way. |
| [`review`](skills/review/SKILL.md) | reviewing a diff, branch or PR | Four dimensions (architecture · full code · performance · duplication/efficiency) as parallel reviewers; every finding carries a concrete failure scenario; an adversarial skeptic tries to refute each one; confirmed bugs trigger a sibling sweep. |
| [`spec-oracle`](skills/spec-oracle/SKILL.md) | behavior is governed by a written standard (language standards, RFCs, file formats, ECMA-335 …) | The spec is the only oracle; derive the expected result *before* reading the code; every citation checked mechanically; the failure modes of plausible-but-wrong citations. Includes a small generic citation checker. |
| [`test-gate`](skills/test-gate/SKILL.md) | before every commit, merge or push | Tiered gates; read the verdict line, not the exit code; filters that silently match nothing (`dotnet test --filter`, `pytest -k`, `jest -t`); confirm new tests actually ran; CI for the exact pushed commit is the final word. |
| [`agent-fleet`](skills/agent-fleet/SKILL.md) | dispatching many parallel subagents on a long campaign | One self-contained input per agent; checkpoint to disk; fresh agents from checkpoints; concurrency and token budgets; land finished work first; adversarial refuters; cost per unit decides the lane. |
| [`claude-cloud-sessions`](skills/claude-cloud-sessions/SKILL.md) | running work in Claude Code cloud sessions | Environment setup scripts and snapshot semantics; multi-repo sessions and hooks; private-repo access; launch surfaces and **billing** (measured, including where it differs from the docs); stopping cleanly before a credit runs out. Includes a setup-script template. |

`engineering-standards` is the bar the other five apply in their own context — each has a short *Standards*
section saying how.

## Adapting to your project

Every skill ends with **Project hooks**: your repo's `CLAUDE.md` supplies its commands, tightens or adds rules,
and wins on conflict — no fork needed. For example, a `## Review rules` block can add a spec-conformance reviewer,
and a `## Testing` section records gate commands and baseline counts.

## Credits

The review skill's triage step and two-axis (scale × consequence) calibration come from
[carlymr/carlys-claude-skills](https://github.com/carlymr/carlys-claude-skills).

## License

MIT — see [LICENSE](LICENSE).
