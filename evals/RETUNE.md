# Prompt forms to re-measure after the baseline

The prompts below carry two habits tuned to the models the suite was written on: they **name the skill** ("Use the
`agent-fleet` skill"), because on natural phrasing those skills fired only some of the time, and they **cap the
answer** ("at most 5 lines"), to keep runs short and the graded line easy to find. On a current model both may now
be crutches: a named skill no longer tests its `description` (the trigger the user actually relies on), and a cap
constrains the WITH arm, which is the arm that has more to say.

**Applied 2026-11-14 on `update-5.2`**: all 14 naming sentences and the 17 numeric caps are gone, and two of the
three spelled-out caps (`test-gate-preexisting-red-blocks-merge`, `engineering-standards-explicit-registry`). The cap
kept is `dotnet-engineering-single-current-tfm`'s "Only the csproj in one code block, then one line of explanation":
its `no-multitarget` grader is a `not_contains` over the whole answer, so the case's verdict depends on the answer
holding nothing but the project file, and an explanation that names `<TargetFrameworks>` to reject it would fail a
correct answer. Its naming sentence is gone. `engineering-standards-no-fallback` keeps "Keep it short" (no number,
not a cap). The cases start a new series at that commit; see `baselines/README.md`. The two `engineering-standards` cases below
were later retired with their skill (`baselines/README.md`); their rows stay as the record of the retune.

They were deliberately **unchanged** in the first baselines (`baselines/`), so those baselines measure the suite as it
was. Retune one group at a time after them, on both tiers, and compare with `python scripts/run_evals.py compare`:

- **Naming.** Drop the naming sentence. Keep the natural form when the with-only `skill-fired` indicator passes in
  3 of 3 runs and the case's Δ holds. When the skill does not fire, the finding is against the skill's `description`
  (fix that, do not restore the crutch); restore the sentence only for a case whose description is already right and
  still does not fire, and say why in the README.
- **Caps.** Drop the cap and keep every forced line (`A: ENQUEUE-NOW`, `MERGE: NO` and the like): the graders read
  the forced lines, which do not depend on length. Keep the uncapped form when WITH does not fall. Watch the graders
  that read the whole answer: a `not_contains` regex (`dotnet-engineering-single-current-tfm/no-multitarget`) and the
  `llm` rubrics see more text in a longer answer, so a fall there may be the grader, not the skill.

## The 14 prompts that name the skill

| Case | Sentence to drop | Natural form |
|---|---|---|
| `agent-fleet-brief-limits` | "Use the `agent-fleet` skill for this." | The prompt without it: it already asks for the "Limits and checkpointing" block of a dispatch brief for 30 subagents in a long campaign. |
| `agent-fleet-file-clusters` | "Use the `agent-fleet` skill." | Without it: "How should I decide which defects each implementer gets?" over 214 notes and parallel implementer slots. |
| `agent-fleet-finished-work-lands` | "Use the `agent-fleet` skill." | Without it: the three fix-lane situations and the four forced lines. |
| `agent-fleet-orientation` | "Use the `agent-fleet` skill." | Without it: "Write the 'Orientation' instruction for the implementer brief". |
| `agent-fleet-registrar-rerun` | "Use the `agent-fleet` skill." | Without it: "Write the procedure section of its brief". |
| `agent-fleet-reprobe-backlog` | "Use the `agent-fleet` skill." | Without it: "Write the 'First steps' section of the implementer's brief". |
| `agent-fleet-stamped-handoff` | "Use the `agent-fleet` skill." | Without it: "Write the 'Checkpoint and resume' block of the implementer brief". |
| `dotnet-engineering-single-current-tfm` | "Use the `dotnet-engineering` skill for this." | Without it: "Write me the complete `.csproj`" for a new open-source library. |
| `engineering-standards-explicit-registry` | "Use the `engineering-standards` skill for this." | Without it: "Write the `CommandRegistry` class" for a trimmed CLI. The skill name hints at the answer ("standards"), so the natural form is also a fairer test of the baseline arm. |
| `engineering-standards-no-fallback` | "Use the `engineering-standards` skill for this." | Without it: "Please write the updated `Resolve` method" with the requested fallback. Same hint as above. |
| `spec-compliance-audit-partial-verdict` | "Use the `spec-compliance-audit` skill for this." | Without it: "Record the audit row" for RLF 2.1 §4.2 rule 3. |
| `spec-oracle-render-the-diagram` | "Use the `spec-oracle` skill for this." | Without it: "Before anyone touches the parser: how do I decide who is right?" |
| `test-gate-conflict-markers-staged` | "Use the `test-gate` skill." | Without it: "I want a check each agent runs after `git add` and before `git commit`". On the older model this form fired in 0 of 3 runs (evals/README.md), so this is the case most likely to need a `description` fix. |
| `variant-analysis-latent-not-cleared` | "Use the `variant-analysis` skill for this." | Without it: "Write the variant-sweep section for the PR description". The skill name hints at "variant", as above. |

The four agent cases carry a weaker form of the same crutch: "use a specialist comment / test-coverage /
error-handling / type-design reviewer if you have one" (`agent-comment-analyzer`, `agent-pr-test-analyzer`,
`agent-silent-failure-hunter`, `agent-type-design-analyzer`). It names the role, not the agent, and the README says
those cases also guard the agents' descriptions. Re-measure them last, with "please review this change" as the
natural form, and read `agent-dispatched`.

## The 17 prompts with a numeric cap (and 3 with a spelled-out one)

| Case | Cap | Uncapped form |
|---|---|---|
| `agent-comment-analyzer` | "Keep the answer under 150 words." | Drop the sentence. |
| `agent-fleet-brief-limits` | "At most 6 bullet lines, concrete numbers and file names, no preamble." | "Give concrete numbers and file names." |
| `agent-fleet-file-clusters` | "in at most 6 lines" | "Give me the rule and the exact command to produce the assignment." |
| `agent-fleet-orientation` | "in at most 5 lines" | "Write the 'Orientation' instruction for the implementer brief, including the exact command." |
| `agent-fleet-registrar-rerun` | "at most 6 lines" | "Write the procedure section of its brief." |
| `agent-fleet-reprobe-backlog` | "at most 5 lines" | "Write the 'First steps' section of the implementer's brief." |
| `agent-fleet-stamped-handoff` | "at most 6 lines" | "Write the 'Checkpoint and resume' block of the implementer brief, with exact file contents and commands." |
| `agent-type-design-analyzer` | "Keep the answer under 250 words." | Drop the sentence. |
| `automating-agent-guardrails-guard-design` | "in at most 8 bullets" | "Before any code, give me the design decisions, and end with exactly these two lines filled in:" |
| `claude-cloud-sessions-multi-repo-hooks` | "Answer in under 120 words." | Drop the sentence. |
| `devlog-commit-hook` | "say in at most 5 bullets what the script does" | "say what the script does". |
| `devlog-consolidate-brief` | "Write the agent's brief, at most 15 lines." | "Write the agent's brief." |
| `devlog-correction-and-clock` | "in at most 8 lines" | "Tell me exactly what to do to the devlog, and end with exactly these two lines filled in:" |
| `devlog-insert-entry` | "in at most 12 lines" | Drop the phrase; keep the request for the exact commands. |
| `spec-oracle-render-the-diagram` | "Answer in under 100 words." | Drop the sentence. |
| `test-gate-conflict-markers-staged` | "Give me the exact commands, at most 5 lines." | "Give me the exact commands." |
| `variant-analysis-latent-not-cleared` | "at most 12 lines" | "Write the variant-sweep section for the PR description." |
| `test-gate-preexisting-red-blocks-merge` | "Two sentences max, then exactly one line" | "Explain, then end with exactly one line". |
| `engineering-standards-explicit-registry` | "Code only, plus at most two lines." | "Code, and say what it does." |
| `dotnet-engineering-single-current-tfm` | "Only the csproj in one code block, then one line of explanation." | "The csproj in one code block, then the explanation." This case's `no-multitarget` grader is a `not_contains` over the whole answer: an explanation that quotes `<TargetFrameworks>` to reject it would fail it, so anchor that regex to the code block (README, "Prose mentions count as matches") before dropping the cap. |

`engineering-standards-no-fallback` asks "Keep it short" with no number; it is a style request, not a cap, and stays.
