# Learnings: running Claude agents on a long engineering campaign

This file holds **only vetted learnings**: the lessons behind these skills that survived an adversarial validation.
From March to September 2026 a large, standards-conformant compiler was built mostly by Claude agents, first by one
agent session and later by fleets of parallel subagents run by an orchestrating session. Its development log (1,750+
entries) was consolidated into **145 candidate learnings**. On 2026-09-28 each candidate was validated against the
primary sources:

- **46 VETTED**, listed below;
- **90 UNPROVEN**, kept in the project's research record with the missing evidence named (where one is encoded in a
  skill, the skill labels it *"Practice — not yet validated"*);
- **9 REFUTED**, kept in the project's research record and removed or corrected in the skills.

A first validator ruled on every candidate, and an independent refuter re-checked every VETTED ruling; the refuters
overturned 21 of the 67 that the first validator had vetted. The candidate ids (C1–C145) are the project's ledger
ids, kept so a later run can re-check a learning without re-validating it.

Each entry gives the **problem**, the **root cause**, the **fix** and where it lives in these skills (or "not yet in
the skills"), the **evidence** (the validator's corrected figures), and its **validation**. "Entry N" is an entry in
the project's development log.

**Contents:**
[Adversarial review and refuters](#adversarial-review-and-refuters) ·
[Checkpointing and limits](#checkpointing-and-limits) ·
[Concurrency and landing](#concurrency-and-landing) ·
[Gates and verification](#gates-and-verification) ·
[Guardrails](#guardrails) ·
[Measurement discipline](#measurement-discipline) ·
[Model per role](#model-per-role) ·
[Orchestration mechanics](#orchestration-mechanics) ·
[Orientation and handoffs](#orientation-and-handoffs) ·
[Spec as oracle and citation discipline](#spec-as-oracle-and-citation-discipline) ·
[Work register](#work-register) ·
[Validation](#validation)

[af]: skills/agent-fleet/SKILL.md
[ag]: skills/automating-agent-guardrails/SKILL.md
[tg]: skills/test-gate/SKILL.md
[so]: skills/spec-oracle/SKILL.md
[sca]: skills/spec-compliance-audit/SKILL.md
[rv]: skills/review/SKILL.md
[es]: skills/engineering-standards/SKILL.md
[va]: skills/variant-analysis/SKILL.md

---

## Adversarial review and refuters

### C1. An audit scoped to five items reported "no divergences"
- **Problem:** a comprehensive audit was requested; the agent checked 5 items and reported no divergences.
- **Root cause:** under-scoping gave false confidence. Nothing counted what had not been examined.
- **Fix in the skills:** [spec-compliance-audit §1–§2](skills/spec-compliance-audit/SKILL.md#1-decompose-the-standard-into-a-rule-catalog)
  (a rule catalog as the denominator, GAP as the progress metric); [review, Scale](skills/review/SKILL.md#scale)
  (a completeness critic).
- **Evidence:** the full audit found 80 issues (7 critical); one missed bug affected 32 programs of an external
  conformance suite, and "a full day was wasted". Later, the denominator showed 3,361 of 3,636 open rows (92 %) had
  never been adjudicated while review fleets polished 27, and redirected the campaign. The completeness critic
  found same-class siblings and 15 unseen rule blocks. Qualifier: the catalog itself was once 60 rules short,
  because its critics asked only whether a block yielded something; a per-clause count check fixed that.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 020, 988, 989, 1026, 1424, 1529.

### C3. A verifier that agrees must agree with the reasoning
- **Problem:** a verification pass agreed with a verdict held for the wrong reason; acting on that reason would
  have shipped a defect that rejects legal input.
- **Root cause:** the verifier checked the conclusion, not the reasoning.
- **Fix in the skills:** [review Step 6](skills/review/SKILL.md#step-6---adversarial-verification) "Right answer,
  wrong reason"; [spec-oracle, Failure modes](skills/spec-oracle/SKILL.md#failure-modes-each-one-has-shipped-real-bugs);
  [spec-compliance-audit §6](skills/spec-compliance-audit/SKILL.md#6-the-adversarial-refuter-on-every-closing-verdict).
- **Evidence:** of five forks the verifier agreed with, three rested on wrong rationales and one was
  behavior-changing. Later, refuters that agreed a finding was real corrected its root cause; a fix at the reported
  site would have left a live sibling broken. The same pass caught a fabricated corroborating citation.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 925, 1253, 1406, and the
  adjudication record for entry 925.

### C4. Refuters overturn a large share, and almost always downward
- **Problem:** adjudicators closed rules as conforming after sampling outputs or reading one of two code paths.
- **Root cause:** the author of a verdict is biased toward it, and sampled outputs miss the branch that matters.
- **Fix in the skills:** [agent-fleet §10](skills/agent-fleet/references/refuters-and-routing.md#10-adversarial-refuters-on-closing-verdicts);
  [spec-compliance-audit §6](skills/spec-compliance-audit/SKILL.md#6-the-adversarial-refuter-on-every-closing-verdict).
- **Evidence:** 26 agents, 16 overturns, all downgrades; 19 of 70; 44 of 120 ("not one overturn went upward"); 3 of
  10; 21 of 51; later batches 39/74, 67/158, 41/115, 36/112, 39/135. One batch (2026-08-29) overturned in both
  directions, downgrades dominating. Caveat: later refuters re-derived only closing verdicts, so "never upward" in
  those batches is structural.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1115, 1145, 1343, 1363, 1437,
  1451, 1681, 1707.

### C5. Review fleets on a green wave find the wave's own defects
- **Problem:** waves gated green still carried defects their implementers had introduced, widened or certified.
- **Root cause:** only the implementer had read the change.
- **Fix in the skills:** [agent-fleet §11](skills/agent-fleet/references/refuters-and-routing.md#11-measure-cost-per-unit-and-route-to-the-cheapest-lane)
  "Self-review before a large review fleet": each implementer reviews its own diff, and the lander reviews the
  merged batch.
- **Evidence:** a 106-agent fleet confirmed 26 findings; 5 of the 11 resulting items were defects the wave itself
  introduced, widened or certified. A 25-agent pass found three blockers the author had just introduced. Qualifier:
  thirteen large fleets (~1,000 agents, ~4 B cache-read tokens) moved the open count only 27 rows, so the lasting
  form is self-review plus the lander's review, not routine large fleets; self-review has kept catching the
  implementer's own defects since.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1104, 1390–1397, 1421, 1424.

### C6. Re-probe a stale backlog before fixing it
- **Problem:** 331 known-bad rules had been judged before several fix waves landed.
- **Root cause:** a note's word is not evidence, and the code had moved on.
- **Fix in the skills:** [agent-fleet §2](skills/agent-fleet/references/inputs-and-briefs.md#2-inputs-one-agent-one-self-contained-input-file)
  "The implementer's first step is to re-run each item's repro on its own build"; the brief template's Contract.
- **Evidence:** a 24-agent probe-and-refute pass found 114 already FIXED, 170 still live and 47 not implemented, with
  20 prober claims overturned. A later 17-agent pass had refuters break 14 FIXED claims. Re-probing on the
  implementer's own build is standing practice and keeps discharging stale items.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1255, 1285, 1331, 1722, 1743, 1756.

### C9. A registrar re-measures every lead before filing it
- **Problem:** leads forwarded from implementer reports were often wrong, and a second agent repeated them verbatim:
  "a registrar that copies a report's measurement forward is a second place for the report's mistakes to live".
- **Root cause:** unverified self-reports.
- **Fix in the skills:** [agent-fleet §2](skills/agent-fleet/references/inputs-and-briefs.md#2-inputs-one-agent-one-self-contained-input-file)
  "The agent that files leads as work items (the registrar) re-checks every lead", in the current form: run the
  lead's given repro once on your own build; write a fresh probe only when the lead has no runnable repro and code
  site. Also the brief template's Contract.
- **Evidence:** one pass of 52 leads: three died on re-measurement, one already fixed. Another of 48: three did not
  survive the re-run, and a quoted citation was a paraphrase. Another: two real defects each carried a wrong claim.
  Sustained across six registrar passes.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1616, 1623, 1633, 1636, 1664, 1672.

## Checkpointing and limits

### C19. A graceful STOP file works where messaging cannot
- **Problem:** workflow agents cannot be messaged, and a hard kill lands mid-step; landers had been killed
  mid-landing.
- **Root cause:** no channel into a running workflow agent.
- **Fix in the skills:** [agent-fleet §5](skills/agent-fleet/references/concurrency-and-watchdog.md#5-the-concurrency-budget-and-stopping-before-the-limit)
  "Use a graceful STOP file"; the brief template's stop rules.
- **Evidence:** a lander stopped cleanly before its push for a session reset, with all seven clusters gated green;
  two registrars stopped with their work in checkpoint commits, and finishers completed it. Graceful stops were used
  repeatedly from 2026-09-22, and no limit kill of a working agent is recorded after adoption.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1542, 1556, 1559, 1637, 1650,
  1664, 1669, 1672.

## Concurrency and landing

### C23. Idle slots, not work, were the bottleneck: fill a slot the turn it frees
- **Problem:** the defect register filled much faster than it drained.
- **Root cause:** implementers were dispatched one cluster at a time, behind landings.
- **Fix in the skills:** [agent-fleet §6](skills/agent-fleet/references/landing.md#6-land-finished-work-before-starting-new-work)
  "Fill a freed implementer slot in the same turn it frees". (The rolling-wave script that mechanizes it is not
  itself validated.)
- **Evidence:** ~16 mechanisms in six days (~2.7/day) against a modelled capacity of ~24/day, about 11 %
  utilization, while two adjudication batches opened 169 notes. The next working day, with every slot refilled the
  turn it freed: twelve clusters in three hours across three trains.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1454, 1520, 1521, 1523, 1744, and
  the 2026-09-04 process review.

### C25. Run the comprehensive battery in its own worktree
- **Problem:** the batch test battery rebuilds the tree, so a battery on the shared tree froze the lander.
- **Root cause:** a shared build tree; one battery measured a half-edited change and had to be redone.
- **Fix in the skills:** [test-gate](skills/test-gate/SKILL.md#the-three-tiers) "Run the comprehensive gate in its
  own detached worktree"; [agent-fleet §6](skills/agent-fleet/references/landing.md#6-land-finished-work-before-starting-new-work)
  "Run the comprehensive battery in its own detached worktree".
- **Evidence:** the battery took ~45 min of machine time. From the next battery on, every battery ran in a detached
  worktree without freezing the lander. The saving is a slowdown rather than a full freeze: the lander's gate ran
  about twice as slow during one battery.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1175, 1455, 1465, 1502, 1645, 1733.

### C26. Composition defects appear only on the merged tree
- **Problem:** two clusters, each green, composed wrongly: one renamed a method, and the other's later batch wrote
  the old name back.
- **Root cause:** each cluster's own gate cannot see its siblings.
- **Fix in the skills:** [agent-fleet §6](skills/agent-fleet/references/landing.md#6-land-finished-work-before-starting-new-work)
  "The lander gates the WHOLE test suite, unfiltered", on the merged tree.
- **Evidence:** 1 red of 27,772 tests on the merged tree; the same shape recurred the next train; a set missed a
  member a sibling had added. The merged-tree gate kept catching composition defects through later trains.
  (Merging one cluster at a time with a build between each is not validated.)
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1587, 1617, 1618, 1650, 1651, 1758.

## Gates and verification

### C39. "It ran" is not success
- **Problem:** ~70 functions and 30 green unit tests, and a demo ran cleanly while every intrinsic result was zero.
  Later a program's own "all tests successful" line was trusted without a diff.
- **Root cause:** the tests exercised the runtime directly, never the code generator; surface signals were taken
  as proof.
- **Fix in the skills:** [engineering-standards §5](skills/engineering-standards/SKILL.md#5-verification-and-invariants)
  "Verify the values, not 'it ran'".
- **Evidence:** every intrinsic result in the demo was zero; the recurrence left four output mismatches. Byte-exact
  comparison against expected output became the standing harness.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 011, 075, 575.

### C40. A regression guard that compares against recorded output can lock bugs in
- **Problem:** wrong results had been recorded as "expected".
- **Root cause:** the baselines were captured from the implementation, not derived from the authority.
- **Fix in the skills:** [test-gate, Standards](skills/test-gate/SKILL.md#standards);
  [engineering-standards §5](skills/engineering-standards/SKILL.md#5-verification-and-invariants).
- **Evidence:** 232 wrong results locked in across 19 tests; a purge fixed 147. The failure recurred later and was
  resolved each time by re-deriving the expected value from the spec, never by re-baselining.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 169, 170, and later re-derivations.

### C42. Build the whole solution before a no-build test run
- **Problem:** CI was red while every local run was green, because the tests exercised an old compiler.
- **Root cause:** building one project does not re-copy its output into the test projects.
- **Fix in the skills:** [test-gate, Always first: build fresh](skills/test-gate/SKILL.md#always-first-build-fresh),
  including: confirm the build succeeded, and hash the assemblies when in doubt.
- **Evidence:** CI showed 2 failures of 3,112 on a clean build; a fresh-build battery caught 22 + 2 reds at once.
  The stale-binary family recurred from June to July before the rule. The rule is necessary, not sufficient: a
  failed build and an incremental build each later left a stale assembly.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 550, 619, 621, 704, 724, 725, 1007,
  1168, 1305, 1445.

### C43. Local green is evidence about one host
- **Problem:** eleven clusters in a row went red on CI while the local guard was green; three pushes went red from a
  check compiled only into Debug builds.
- **Root cause:** the local battery ran on one OS, in Debug, and was not a superset of CI.
- **Fix in the skills:** [test-gate, After the push](skills/test-gate/SKILL.md#after-the-push-ci-is-the-final-authority).
- **Evidence:** 11 red pushes; 3 consecutive red pushes. After CI was read on every landing, it held main untouched
  on reds the local gates missed, several times.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 515, 691, 774, 1617.

### C44. Gate on the verdict line, never on a chain's exit code
- **Problem:** `test | tail -2 && git commit` committed with the verdict line reading `Failed: 1`; a battery exited 0
  while its verdict line reported 31 regressions.
- **Root cause:** a chain's exit status is its last command's. "Only the FORM prevents it."
- **Fix in the skills:** [test-gate, Read the verdict line](skills/test-gate/SKILL.md#read-the-verdict-line-not-the-exit-code);
  [agent-fleet §1](skills/agent-fleet/SKILL.md#1-the-cost-law-which-drives-the-other-rules) rule (a).
- **Evidence:** reading the verdict line caught 31 regressions that the exit code hid, with every other gate
  green. The written rule was broken three times after it existed; the hook that now enforces it is not yet proven
  in production.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 783, 792, 1140, 1189, 1739.

### C45. A check that has never failed may not be checking anything
- **Problem:** a static-analysis scan printed "Scan completed successfully" while 4 of its 6 rules were dead; drift
  guards were drafted that could not have caught the defect they commemorated.
- **Root cause:** guards were never watched failing. "A guard nobody has watched fail is a guess about a guess."
- **Fix in the skills:** [test-gate, A gate that has never failed proves nothing](skills/test-gate/SKILL.md#a-gate-that-has-never-failed-proves-nothing);
  [engineering-standards §5](skills/engineering-standards/SKILL.md#5-verification-and-invariants).
- **Evidence:** 4 of 6 rules dead; once fixed, one found 423 hits. Seen-to-fail checks later caught several guards
  and goldens that could not fail.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1023, 1172, 1226, 1391, 1393.

### C46. A filter that matches nothing is a silent green, and so is one dead term among live ones
- **Problem:** a filter reported 354 passed and ran neither new test; after a test split, four CI filters matched
  nothing; one dead term OR'd among live ones printed a clean pass on every run.
- **Root cause:** `dotnet test --filter` answers "no test matches" with exit 0, and a whole-filter check cannot see a
  single dead term.
- **Fix in the skills:** [test-gate, A filter that matches nothing](skills/test-gate/SKILL.md#a-filter-that-matches-nothing-is-a-silent-green),
  including checking each OR'd term's own count.
- **Evidence:** 354 green over 0 of 2 targets; four dead CI filters, one of which would have printed a
  "byte-exact" verdict over zero of 349 cases. A per-term population check then refused dead terms in live gates
  three times.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1080, 1426, 1556.

### C47. A missing observation is not a negative one
- **Problem:** a guard printed ALL GREEN at 352 of 353 because one program vanished; five runs on one tree gave five
  outcomes; a killed process was scored as a rejection.
- **Root cause:** harnesses counted only failures and inferred verdicts from absent data; the launcher logic was
  copied seven times.
- **Fix in the skills:** [test-gate, A missing observation](skills/test-gate/SKILL.md#a-missing-observation-is-not-a-negative-one).
- **Evidence:** 352/353; seven copies merged into one. A later population audit caught a program with no verdict
  line, and a CI read that came back empty now reports UNVERIFIED instead of red.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1150, 1151, 1309, 1735.

### C48. Compare differentials case by case, never by totals
- **Problem:** for weeks, "0 per-case flips" rested on four matching totals; no per-case record had been kept.
- **Root cause:** identical totals are consistent with offsetting flips.
- **Fix in the skills:** [test-gate, A missing observation](skills/test-gate/SKILL.md#a-missing-observation-is-not-a-negative-one)
  "Compare ... case by case, never by totals".
- **Evidence:** 1,323 cases; two planted offsetting flips left all four totals unchanged and were caught by name.
  Later batteries found 12 flips (one a real regression) and a flip that produced a blocking fix.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1176, 1610, 1611.

### C49. A selector is no evidence about what it dropped
- **Problem:** the work ranker hid about half the harmful work; a regex counting a construct reported the subject
  itself as the whole population.
- **Root cause:** the ranking predicate omitted two harm classes; the regex required an optional keyword that the
  author's own example happened to contain.
- **Fix in the skills:** [test-gate](skills/test-gate/SKILL.md#a-missing-observation-is-not-a-negative-one) "A filter,
  ranker or selector tells you ... nothing about what it dropped";
  [engineering-standards §5](skills/engineering-standards/SKILL.md#5-verification-and-invariants) "Vary the axis".
- **Evidence:** actionable items went from 10 to 19 on one predicate change (4 + 5 items in the two missing
  classes); the widened regex found 3 where 1 was reported (2 of them real). Measuring the complement later found a
  gate that skipped a 2,218-case set where all eight reds lived.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1188, 1632, 1634.

### C51. The landing protocol never read CI: main was red for 29 hours
- **Problem:** 16 consecutive CI runs failed over ~29 h while about ten landings each reported a green local gate.
- **Root cause:** every written landing procedure stopped at the push; the reds were host-dependent behaviors of the
  CI runners (Windows and Linux) that no gate on the owner's desktop could see.
- **Fix in the skills:** [test-gate, After the push](skills/test-gate/SKILL.md#after-the-push-ci-is-the-final-authority);
  [agent-fleet §6](skills/agent-fleet/references/landing.md#6-land-finished-work-before-starting-new-work) "Watch CI for every
  pushed head".
- **Evidence:** 16 failed runs plus 6 cancelled, 28 h 50 min. After landings pushed a verified sha and waited for
  CI, CI caught reds with main untouched on at least six later trains.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1567, 1568, 1571, 1594, 1617–1619,
  1656, 1667, 1710, 1735.

### C52. Conflict markers passed three green gates
- **Problem:** an implementer committed four unresolved conflict hunks into a script no test imports.
- **Root cause:** a blanket `git add -A` checkpoint, a lander that resolved conflicts by judgement with no re-check,
  and no test touching the file.
- **Fix in the skills:** [test-gate](skills/test-gate/SKILL.md#between-staging-and-committing-no-conflict-markers)
  "Between staging and committing: no conflict markers";
  [agent-fleet §4](skills/agent-fleet/references/checkpointing.md#4-checkpoint-to-disk-after-every-unit-of-work) "Assert on conflict
  markers between staging and committing"; the brief template's checkpoint protocol. Both assert on the OUTPUT of
  `git grep --cached` and `git diff --cached --check` (not their exit codes: a CRLF file makes every line "trailing
  whitespace"), backed by a repo-wide conflict-marker test.
- **Evidence:** 4 hunks, 3 green gates. The marker test was fired end to end (370 ms over 7,304 files) and has run in
  every unfiltered leg since; the per-cluster check is recorded train after train.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1547, 1559, 1594.

### C53. A union of filter terms never converges; the landing gate is the whole suite
- **Problem:** trains passed a green union-of-filters gate and each drew a red first CI run on tests no term named.
- **Root cause:** the leftover set is by construction the population no term names, so one more term per failure
  never converges.
- **Fix in the skills:** [test-gate, The three tiers](skills/test-gate/SKILL.md#the-three-tiers) "A landing gate
  covers the whole affected assembly"; [agent-fleet §6](skills/agent-fleet/references/landing.md#6-land-finished-work-before-starting-new-work).
- **Evidence:** a new missing term on each of five landings; a 25-term union green while five external programs were
  red. The whole-assembly gate measured 7,632 cases in 11 min 30 s (9,317 cases later) and ran on every train after,
  with "not one red on any leg" on the next.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1594, 1617, 1618, 1619, 1622, 1625,
  1656, 1758.

### C56. A registered test is not an executed test
- **Problem:** a new negative test shipped without its expected-error file, because the implementer's gate ran only
  the "every program is registered" test.
- **Root cause:** registration proves presence, not execution.
- **Fix in the skills:** [test-gate, Confirm the new tests actually ran](skills/test-gate/SKILL.md#confirm-the-new-tests-actually-ran-by-name).
- **Evidence:** one incident, caught by the lander's whole-suite gate (2026-09-24). By-name execution of new cases is
  recorded on every later train.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1697, 1699, 1700, 1702, 1715, 1758.

## Guardrails

### C60. Agents change valid input to dodge a bug in the tool
- **Problem:** the agent edited a demo program and test inputs until they passed, instead of fixing the tool.
- **Root cause:** working around bugs, as when using software, while building it.
- **Fix in the skills:** [engineering-standards §3](skills/engineering-standards/SKILL.md#3-correctness-and-root-cause)
  "Never change valid input to dodge a bug in the tool".
- **Evidence:** 4 occurrences in March 2026. The rule then kept deciding landings for six months. A July recurrence
  stayed hidden until September: the written rule reduces the behavior but has not stopped it.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 008, 011, 1559, 1562, 1657.

### C61. Every bug is a pattern
- **Problem:** fixes went to one of several sibling sites (two of three arithmetic statements; one of five places
  carrying the same rule). "The user had to prompt this audit; it should have been automatic."
- **Root cause:** fix, test, move on. The most reproducible shape is a two-arm dispatch: the repro exercises one
  arm, the tests follow it, and the other arm survives.
- **Fix in the skills:** [variant-analysis](skills/variant-analysis/SKILL.md);
  [engineering-standards §3](skills/engineering-standards/SKILL.md#3-correctness-and-root-cause);
  [review Step 7](skills/review/SKILL.md#step-7---sweep-for-siblings).
- **Evidence:** the two-arm shape recurred at least eight times by the log's own (inconsistent) count and kept
  recurring. One later sweep found four copies where the item named two, plus two unfiled harms.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 071, 113, 1159, 1402, 1474, 1498.

### C62. Silent fallbacks "for convenience" are wrong answers
- **Problem:** a silent-drop fallback was used 13 times; another made every condition the lowering did not
  recognize evaluate TRUE (first seen on comparisons with negative literals).
- **Root cause:** convenient fallbacks that avoided failures at the cost of silent wrong behavior.
- **Fix in the skills:** [engineering-standards §1](skills/engineering-standards/SKILL.md#1-the-quality-bar) "No hacks,
  no shims, no fallbacks"; [§4](skills/engineering-standards/SKILL.md#4-completeness) "Never ship a half-feature".
- **Evidence:** 13 failures in one conformance program traced to one silent drop; removing the other fallback fixed a
  program and exposed a masked bug. Fail-loud has been applied for six months since. (The silent-failure reviewer
  agent is not part of this validation: no production catch is recorded.)
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 080–083, 119, 1098, 1143.

### C63. Deferral and "scope to the test" are debt
- **Problem:** the agent repeatedly proposed deferring spec-correct behavior or scoping a feature to what one test
  referenced. The owner: "you regularly prefer to accumulate technical debt rather than do it correctly."
- **Root cause:** the smallest diff that fits the stated estimate.
- **Fix in the skills:** [engineering-standards §4](skills/engineering-standards/SKILL.md#4-completeness) "Tests
  verify; they do not scope" and "Deferral is debt"; [§2](skills/engineering-standards/SKILL.md#when-re-architecture-is-required-not-optional)
  "A stated scope is an estimate".
- **Evidence:** at least six owner corrections from 2026-03-14 to 2026-07-21; one "deferral" turned out to be a path
  that already rejected legal input. No further owner rebuke for deferral after July.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 020, 629, 651, 942, 954, 1413, 1559.

## Measurement discipline

### C75. Green gates are not evidence when they cannot see what changed
- **Problem:** the transcribed standard was "basically unintelligible" as rendered, with every gate green.
- **Root cause:** "every gate reads the file as TEXT and the reader reads it as a RENDERED PAGE"; a consistency
  check proved agreement with a generator that shared its blind spot.
- **Fix in the skills:** [test-gate](skills/test-gate/SKILL.md#a-gate-that-has-never-failed-proves-nothing) "ask what
  its scope leaves out"; [engineering-standards §5](skills/engineering-standards/SKILL.md#5-verification-and-invariants).
- **Evidence:** four instances in one session, all under green gates; 4,161 rule labels parsed as list items. The
  same discipline later found a filter green over zero of 349 cases.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1063, 1072, 1076, 1426, 1529.

## Model per role

### C88. A 1-hour prompt cache for roles that wait on gates
- **Problem:** agents blocked on gates re-wrote their whole context to the cache after every wait over 5 minutes.
- **Root cause:** the default 5-minute cache TTL; confirmed by a control where roles without the setting re-wrote
  340k+ tokens after each ~9-minute wait.
- **Fix in the skills:** [automating-agent-guardrails §2](skills/automating-agent-guardrails/SKILL.md#2-role-agent-definitions)
  (`cacheTtl: 1h` on every role that waits).
- **Evidence:** over 208 agents, every wait over 5 minutes (164) was followed by a cache read: 55 M tokens read after
  waits, an estimated net saving of ~44 M base-token units at API cache price ratios. Roles that never waited paid
  the 1-hour write premium for nothing. The saving is modelled at API ratios, not an A/B on the weekly meter.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1637, 1711, subagent transcripts
  since 2026-09-25.

## Orchestration mechanics

### C95. Never read a two-stage fleet's output before the completion signal
- **Problem:** a batch was published early; the re-merge moved 10 of 55 rows, three of which had been reported
  closed.
- **Root cause:** stage one writes the file and stage two rewrites it; an adversarial stage two only removes
  confidence, so an early read looks better than the truth.
- **Fix in the skills:** [agent-fleet §9](skills/agent-fleet/SKILL.md#9-isolation-the-frozen-tree-and-the-completion-signal)
  "Never poll a running fleet's output directory".
- **Evidence:** 10 of 55 moved, all downgrades; the published count was corrected. The next day the completion
  notice exposed 5 of 12 dead refuters whose files held unrefuted stage-one output. A later mid-write read of
  reports put a false item in front of the owner.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1116, 1124, 1628.

### C96. A fan-out whose agents all died reported "all clean"
- **Problem:** a nine-agent sweep lost all nine agents to API errors, and its summary said every use was correct.
- **Root cause:** a `defects.length ? … : fallback` branch "unable to distinguish 'nothing was wrong' from 'nothing
  ran'".
- **Fix in the skills:** [test-gate, A missing observation](skills/test-gate/SKILL.md#a-missing-observation-is-not-a-negative-one);
  [agent-fleet §2](skills/agent-fleet/references/inputs-and-briefs.md#2-inputs-one-agent-one-self-contained-input-file) "Reconcile the returns".
- **Evidence:** 9 of 9 dead; later runs lost 9 and 3 and correctly reported INCONCLUSIVE.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1105, 1106, 1124, 1754.

### C101. An agent that ends its turn kills its own background gate
- **Problem:** five implementers and a lander returned "gate PENDING" with logs stopping mid-leg.
- **Root cause:** a workflow agent that stops has ended its turn, and its background process dies with it.
- **Fix in the skills:** [agent-fleet §5](skills/agent-fleet/references/concurrency-and-watchdog.md#5-the-concurrency-budget-and-stopping-before-the-limit)
  "An agent never ends its turn while its own background job is running".
- **Evidence:** one incident of six agents. Across six later workflows, 36 of 38 agents blocked in the foreground and
  got verdict lines back; none returned a pending gate.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1637, 1639, 1752, and workflow
  transcripts.

## Orientation and handoffs

### C111. One self-contained input file per agent
- **Problem:** a fan-out told "read the shared config and process element k" processed four items twice and skipped
  five.
- **Root cause:** agents miscount positional indices into shared input.
- **Fix in the skills:** [agent-fleet §2](skills/agent-fleet/references/inputs-and-briefs.md#2-inputs-one-agent-one-self-contained-input-file);
  [spec-compliance-audit §3](skills/spec-compliance-audit/SKILL.md#3-one-agent-per-rule-with-a-self-contained-input).
  Refinements: file names unique across every run, and returns compared by id set, not by count.
- **Evidence:** 4 double-processed, 5 skipped. Used continuously since. One later agent read another run's
  same-named file and returned 12 foreign rows; a count of 119/120 hid it, and only a set comparison exposed it.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 442, 1713.

### C114. State the bar, not only the output format
- **Problem:** 7 of 19 adjudicated rows cited a differential test as evidence, and all 7 passed the validator.
- **Root cause:** the prompt and the schema said which reference forms resolve, never that evidence must be derived
  from the specification.
- **Fix in the skills:** [agent-fleet §3](skills/agent-fleet/references/inputs-and-briefs.md#3-state-the-bar-not-just-the-output-format)
  (state it, then encode it in the schema or validator);
  [spec-compliance-audit §3](skills/spec-compliance-audit/SKILL.md#3-one-agent-per-rule-with-a-self-contained-input).
- **Evidence:** 7 of 19. The lasting fix was the schema and validator, which every later batch passed through; with
  the bar in the brief, writers still produced a few non-derived tests, which refuters and the schema caught.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entry 1115, and later golden rounds.

## Spec as oracle and citation discipline

### C122. Another implementation is a regression net, never an authority
- **Problem:** the legacy implementation had a non-conforming output that the harness's normalization masked.
- **Root cause:** a differential is blind to every bug both sides share.
- **Fix in the skills:** [spec-oracle, Why other oracles are not authority](skills/spec-oracle/SKILL.md#why-other-oracles-are-not-authority).
- **Evidence:** 7 expected outputs re-baselined with owner approval, each verified twice (generated from verified
  runs whose diff was exactly the documented divergence). The legacy differential was made opt-in ("near-zero
  correctness signal and pure friction"); the default gate then ran in 3 ms instead of compiling hundreds of
  programs.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 475, 517, 569, 997.

### C123. Text extraction of a standard loses its diagrams, always toward "more restrictive"
- **Problem:** a dropped pair of choice bars manufactured an ambiguity that survived two adversarial lenses; grammar
  rules inherited the loss and rejected legal input.
- **Root cause:** the PDF's text layer was unusable, so the Markdown was OCR; prose survived, diagrams did not.
- **Fix in the skills:** [spec-oracle §2](skills/spec-oracle/SKILL.md#2-when-a-diagram-table-or-figure-decides-the-question).
- **Evidence:** 18 of 19 diagrams lost their choice indicators, 17 decision-changing. A figure sweep (2026-07-26): 88
  claims, 61 confirmed, all 19 normative errors falsely restrictive; the full reconciliation found 41 normative
  defects, every one falsely restrictive. Eval: 1.00 vs 0.33 (3 runs per arm).
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 926–929, 1029, 1030, 1561.

### C124. Check a "decision fork" against the text before spending an owner decision
- **Problem:** five claimed owner-decision forks reached a research packet; the first was about the wrong construct.
- **Root cause:** questions were framed without re-reading the governing rule; one fork was an OCR artifact.
- **Fix in the skills:** [spec-oracle §1](skills/spec-oracle/SKILL.md#1-find-the-governing-rule).
- **Evidence:** 4 of 5 dissolved into the spec text. Later "owner questions" kept dissolving the same way; one owner
  decision spent without the check was refuted from the rendered page and its implementation reverted.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 925, 1075, 1091.

### C125. Citations are inherited, not invented; check every one mechanically
- **Problem:** wrong clause numbers with correct quoted text spread into comments, tests and logs; a nonexistent
  clause was cited 21 times across 14 files for months.
- **Root cause:** "The failure is not inventing a citation, it is INHERITING one." "A phantom survives by accreting
  meaning."
- **Fix in the skills:** [spec-oracle §3](skills/spec-oracle/SKILL.md#3-write-down-the-expected-result-and-a-checked-citation)
  and its citation checker.
- **Evidence:** two wrong clause citations in one review, repeated ~6 and ~8 times; 54 doc-versus-spec conflicts,
  ~25 of them wrong clause numbers; ~200 sites citing nine clauses that do not exist. The mechanical check later
  caught citations before they landed.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 924, 990, 1120, 1121, 1146, 1439.

### C127. Validate the premise, not only the rule
- **Problem:** a finding quoted a real rule correctly; a decision and an implementation were built on it, but the
  construct it described cannot occur in legal input.
- **Root cause:** "I validated the rule TEXT and never validated the PREMISE."
- **Fix in the skills:** [spec-oracle, Failure modes](skills/spec-oracle/SKILL.md#failure-modes-each-one-has-shipped-real-bugs)
  "A valid rule with an impossible premise"; [review Step 6](skills/review/SKILL.md#step-6---adversarial-verification).
- **Evidence:** one full implementation reverted. At least ten later entries record a premise refuted before or
  instead of a fix.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1075, 1091, 1152, 1545.

### C128. A checker can be buggier than the thing it checks
- **Problem:** a broad citation audit reported 133 of 183 citations defective, and every one inspected was a checker
  bug; a figure audit reported 76 findings, 1 real.
- **Root cause:** quoted labels, captures spanning blocks, a wrong nearest-clause heuristic, and a population chosen
  by directory (source comments were never scanned).
- **Fix in the skills:** [test-gate, A gate that has never failed proves nothing](skills/test-gate/SKILL.md#a-gate-that-has-never-failed-proves-nothing)
  (make it fail once, then ask what its scope leaves out).
- **Evidence:** the broad check was abandoned as unfixable; a narrow check went 9 → 4 → 0 and 5 real defects were
  fixed; the figure audit went 76 → 1 as three tool bugs came out.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1040, 1120, 1122, 1439.

### C129. A real clause can answer a different question
- **Problem:** comments justifying NOT implementing something cited real, checkable clauses about other subjects,
  and the mechanical check passed them.
- **Root cause:** a mechanical check proves the quote is in the clause, not that the clause governs the question;
  because these citations argue against writing code, no test fails.
- **Fix in the skills:** [spec-oracle, Failure modes](skills/spec-oracle/SKILL.md#failure-modes-each-one-has-shipped-real-bugs);
  [review Step 6](skills/review/SKILL.md#step-6---adversarial-verification).
- **Evidence:** 3 in one session; later the conformance definition was cited by a user-documentation clause in 6
  places, caught by the owner. Later catches came from a subject check and self-review.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1439, 1655.

### C130. Survey the implementations on latitude questions; don't recall
- **Problem:** a first-principles framing of an implementation-defined choice was overturned when the
  implementations were actually surveyed.
- **Root cause:** decisions were framed without a survey, or with one built from memory.
- **Fix in the skills:** [spec-oracle, Where the spec leaves latitude](skills/spec-oracle/SKILL.md#where-the-spec-leaves-latitude).
- **Evidence:** all 5 surveyed compilers made the same choice. A survey first answered from memory had to be asked
  twice; one question was then settled "in minutes" from observed behavior. Survey consensus later became the
  default answer for such questions.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1074, 1161, 1730.

## Work register

### C136. A work item's stated premise is a claim, not a finding
- **Problem:** filed items carried wrong layers, counts and causes; one said "four functions" where the standard said
  twenty.
- **Root cause:** the items had been reasoned, not measured, or had gone stale when another change fixed them.
- **Fix in the skills:** [engineering-standards §3](skills/engineering-standards/SKILL.md#3-correctness-and-root-cause)
  (re-measure the premise; "a remembered pattern is a hypothesis");
  [variant-analysis Step 5](skills/variant-analysis/SKILL.md#step-5-probe-every-candidate-with-a-minimal-repro).
- **Evidence:** the stated premise failed on 14 of 16 items across two sessions. Re-measurement kept finding false
  or stale premises in later waves.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1131, 1171, 1213, 1255, 1616.

### C137. One work register, ranked by harm
- **Problem:** "what is left" was written in five places, three claiming to be canonical; a wrong-answer defect sat
  in a prose paragraph no list could see.
- **Root cause:** hand-maintained parallel lists, and ranking by label instead of consequence.
- **Fix in the skills:** [spec-compliance-audit §2 and §7](skills/spec-compliance-audit/SKILL.md#7-cluster-findings-by-mechanism-into-tracked-work);
  [review Step 8](skills/review/SKILL.md#step-8---report).
- **Evidence:** 5 registers, 3 canonical. The register then picked a silent wrong answer over its label. The first
  harm predicate missed two harm classes; fixing it took actionable items from 10 to 19.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1168, 1188, 1325.

### C140. Link each fix to what it closed
- **Problem:** 131 of 138 defective inventory rows were invisible to the ranker; a witness round paid for an
  already-landed fix for the fourth time.
- **Root cause:** ownership was scraped from row prose in the wrong direction, and nothing linked a landed fix to its
  rows.
- **Fix in the skills:** [spec-compliance-audit §7](skills/spec-compliance-audit/SKILL.md#7-cluster-findings-by-mechanism-into-tracked-work).
- **Evidence:** 131 of 138. The back-link check later caught ten false "closed" claims that a filtered gate missed.
- **Validation:** 2026-09-28, validator and independent refuter. Sources: entries 1418, 1594, 1620, 1621, 1660, 1667,
  1672.

---

## Validation

**VETTED** means all four held, checked against primary sources (the development log, commits, test and CI
records, agent transcripts) by a validator and then by an independent refuter told to overturn it:

1. the **root cause** is confirmed, not a hypothesis later overturned;
2. the **evidence** is re-checked, and the figures above are the corrected ones;
3. **no later source contradicts** it;
4. the fix has been **used since and shown useful**: a measured effect, or sustained use with no reversal.

The procedure is the [`devlog`](skills/devlog/) skill's consolidate-and-validate stages. A learning that later
evidence contradicts is removed from here and from the skills.
