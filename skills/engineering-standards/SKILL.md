---
name: engineering-standards
description: Use whenever writing, changing, designing or reviewing production code - it states the non-negotiable quality bar (commercial-grade, decades-maintainable), the structural rules (no god classes, one mechanism per job, one rule in one place), the root-cause and every-bug-is-a-pattern discipline, and when re-architecture is required rather than optional.
---

# Engineering standards

The bar every change is held to. These rules were each earned by a real correction on long-lived production
work: a compiler, a binary rewriter, format decoders, libraries meant to outlive their authors. They are
deliberately short. Each is a rule and the reason it exists; where a rule is easy to misread, an example shows
what it rules out.

A change that breaks one of these is not "done with caveats". It is debt, and it is reported as debt.

## 1. The quality bar

- **Code is production quality, always.** Commercial-grade, maintainable by a team for a decade or more.
  *Why: the maintenance cost dwarfs the cost of writing it well the first time; "good enough for now" is never
  revisited.*
- **Ask "what would I ship if I owned this for five years?" and build that.** Not the simplest diff, not the
  "minimal blast radius" option.
  *Why: minimizing today's diff maximizes tomorrow's rework.*
- **No hacks, no shims, no fallbacks, no dead code, no TODOs left behind.**
  *Why: each one is a defect that has been hidden instead of fixed, and it misleads the next reader.*
  Example: a "try the exact lookup, and if that fails match by name" fallback is not robustness; it is a second,
  wrong answer to a question the first path should have answered correctly.
- **Latest stable language and runtime; zero backward-compatibility baggage unless a real user needs it.** Use
  the modern idioms (records, pattern matching, spans, primary constructors, or the equivalents in your
  language).
  *Why: compatibility shims for users who do not exist are pure maintenance cost.*
- **The tie-breakers for every judgment call: usability, understanding, support, maintenance.** Diagnostics that
  name the problem and the fix; code a reader understands six years from now; failures that are diagnosable on
  someone else's machine; structure that handles the next case.
  *Why: a plan can be complete on correctness and still fail the people who use and maintain it.*

## 2. Design and structure

- **No god classes.** Each type has one real responsibility; split a type the moment it acquires a second.
  *Why: a class that does everything is the place every change collides and every bug hides.*
- **One mechanism per job.** One type, one helper, one dispatch path for each concept. A new mechanism is
  allowed only if it is genuinely better AND every existing use migrates to it in the same change.
  *Why: two coexisting mechanisms double the surface and are guaranteed to drift apart.*
- **One rule in one place.** Before fixing "construct X fails", search for the RULE, not the construct. If the
  rule is written down in more than one place, extracting it is the fix.
  *Why: duplication is what makes a systematic bug look like a one-off.* Example: a value mapping hand-copied
  into three evaluators works in two and throws in the third; patching the third leaves two copies waiting to
  drift. The same holds for constants: two symbols with the same value are one definition written twice.
- **Change the dispatch, not the callers.** When a new variant appears, extend the one canonical dispatch point.
  Never add `if (x is NewThing)` to each consumer or wrap the old type at call sites "transitionally".
  *Why: smeared type checks are where the next completeness bug hides, and "transitional" wrappers never leave.*
- **Model the rule's full shape before fixing a table or schema.** Read every rule the structure must hold, then
  let the widest one choose the shape (scalar, set, per-position, predicate).
  *Why: a scalar column where a rule names a set silently rejects valid input.*
- **Keep phases and layers one-directional.** No semantics in the parser, no code generation in the analyzer, no
  later stage writing back into an earlier stage's model.
  *Why: back-edges make every stage depend on the order of every other.*
- **Resolve to typed objects at load time; encode only at the boundary.** Known-format data is a typed model, not
  a byte array or a raw index; serialization happens in exactly one place.
  *Why: indices and offsets go stale when anything upstream shifts; typed references do not.*
- **Build output from the model; do not patch the input in place.** Rebuilding computes every offset fresh.
  *Why: in-place patching needs delta arithmetic that breaks on the first case nobody anticipated.*
- **Use the standard tool for a solved problem.** A parser generator for syntax, the platform library for
  formats, generated exhaustive visitors for tree walks. Never hand-roll a second parser beside the real one.
  *Why: hand-rolled copies drift, and a generated visitor turns a missing case into a compile error.*
- **Construct registries explicitly; do not discover by reflection** where trimming or AOT is in play.
  *Why: a discovered entry the trimmer drops vanishes from the shipped binary while every test still passes.*
- **Check what already exists before proposing a design.** Search the repo and its history first, then converge
  on one answer.
  *Why: a menu of fresh proposals over an already-settled design is churn, not progress.*

### When re-architecture is required, not optional

- **A stated scope is an estimate, never a ceiling.** When implementation shows "one small change" actually
  needs restructuring, the restructuring IS the task. Correct the estimate and the design doc; do not ship the
  smallest diff that fits the original guess.
- **Prefer the shape that makes the NEXT case automatic over the one that makes THIS case small**, and pair it
  with a drift test so "automatic" stays true.
  *Example: seven ambient flags each needed save/restore around a new construct. Restructuring them into one
  copyable snapshot, while there were seven and not the fifteen coming, beat a hand-written save/restore every
  future flag would have to remember to join.*
- **Temporarily breaking the build is acceptable on the way to the right structure.** A type change propagates
  through every layer in one pass; land it when it is whole and green again.
  *Why: a half-migrated codebase with two shapes is worse than a short, deliberate red.*
- **Re-architect when the same fix keeps recurring.** At the third patch to one component, stop and study (or
  adopt) a design that is correct for every input, not just the inputs seen so far.
- **Answer the structural question first.** Before semantic detail, state: is there ONE lexer, ONE evaluator, ONE
  dispatch for this job? Design the clean end state, not the least change to the current one.
  *Why: anchoring on the existing shape produces patches over patches.*

## 3. Correctness and root cause

- **Fix the root cause. Never paper over a symptom.** No retry loops, no "skip this case", no environment flag
  that hides the output, no special-casing to match an expected answer.
  *Why: a workaround leaves the defect in place to hit the next input, and hides it while it waits.*
- **Never change valid input to dodge a bug in the tool.** If a valid program, file or query fails, the tool is
  broken; the failure is the signal pointing at the bug.
- **Never relabel a bug a "quirk" or "known limitation".** Honest diagnosis has always turned out to be a real bug.
- **When a correction arrives, fix the interpretation, not the output.** Treat "this result is wrong" as evidence
  that the model is wrong, and find the general flaw that makes every observation fall out correctly.
  *Why: special-casing to the correction overfits and breaks on the next case.*
- **Every bug is a pattern: sweep for its siblings in the same change.** Name the pattern, search the whole
  codebase (code and docs), fix every instance, and add a test that catches a recurrence.
  *Why: every time this was skipped, the siblings existed.* Show the search you ran; "swept" without the query is
  an assertion, not evidence.
- **Two-arm dispatch: ask which arm you fixed, and what the other one is.** Exact vs approximate path,
  validating vs value-producing twin, read vs write half, debug vs release.
  *Why: a repro exercises one arm, the existing tests follow the same arm, and the other arm survives a green
  suite.* At the second occurrence, restructure so both arms share one rule.
- **Implement the named operation, not a convenient equivalent.** When a spec or contract names an exact
  operation or rounding or error condition, implement that, not a nearby library call that behaves slightly
  differently.
- **Diagnose from evidence, never from a plausible story.** State what is known, then read the code, dump the
  data, reproduce in isolation. "Probably because..." is not a diagnosis.
- **A remembered pattern is a hypothesis.** When a known bug shape fits the symptom, find its mechanism in THIS
  code before acting. If you cannot point at it, the pattern does not apply.
- **Apply a coordinated set of fixes as one change and test once.** Cherry-picking pieces of an interdependent
  fix, then reverting some of them, creates states worse than either end.
- **Output must be reproducible.** The same input produces the same output: no process-randomized hashes, no
  wall-clock stamps in artifacts.
  *Why: nondeterminism makes every later comparison meaningless.*

## 4. Completeness

- **Implement the COMPLETE feature to its spec or design. Tests verify; they do not scope.** Enumerate every rule
  the feature owes and build all of it.
  *Why: a slice shaped by one test fails the next real input and re-litigates the design.*
- **Deferral is debt, and only the owner may choose it.** "Documented limitation", "follow-up pass", "staged",
  and a loud rejection of valid input are all forms of unfinished work. If the full job is genuinely large,
  surface the size as a decision; do not pre-decide the deferral.
- **Never ship a half-feature.** Parsing something and silently doing nothing is worse than an error: the program
  runs and produces wrong results. The feature, its tests and its docs land together.
- **Handle every legal input shape, not the shapes you happen to use.** A bug found on your own code is a bug a
  user will hit; fence it with a standalone regression test.
- **Future-proof when the option exists.** Take the hardening path (the extra validator, the gate, the
  re-verification trigger) rather than labeling it optional.

## 5. Verification and invariants

- **Propose invariants, validators and drift tests unprompted.** With each change, ask "what could go wrong?" and
  encode the answer as a check that fails.
  *Why: they should arrive with the change, not after someone asks.*
- **Prefer structural guarantees to conventions.** An exhaustive generated switch, a dependency graph asserted at
  construction, or a type that cannot represent the invalid state beats a comment asking the reader to remember.
- **Pin every collapse with a drift test.** When two copies become one, add a test that fails if a copy
  reappears; when a model restates what an engine decides, add a test that cross-checks them.
- **Surface the drift rules BEFORE the edit, from one home.** Each structural test states its rule in its own doc
  comment — that is the rule's only home. Generate an index from them and answer "which rules govern this file?" before
  anyone edits it (`references/rule_index.py`: `--tests "<glob>"` regenerates the index, `--check` in CI fails when it
  is stale or a test states no rule, `<file>` lists the governing rules). Never copy the rules into docs or skills.
  *Why: 200+ drift tests whose rules lived only in the tests were rediscovered one red gate at a time; copying them
  into a skill would have made a second copy of every rule to drift.*
- **A guard that cannot fail is not a guard. Make every new check fail once, for the right reason.** Restore the
  defect or point it at an old revision before trusting its green.
  *Example: a test that verified a registry against the same reflection scan that populated it asked "did the
  scan find what the scan found?" and could never fail.*
- **Ask what a check's scope EXCLUDES, and whether each exclusion's premise is still true.** Couple every
  exemption to the precondition that justifies it.
- **Verify the values, not "it ran".** Assert on specific output values, never on exit codes alone.
- **Compute expected results from the authority** (the spec, the contract), never by copying an oracle's output.
- **Every measurement carries a witness** (a count, a version, a marker) that proves it did the work, and you
  check the witness before reporting. A stale binary, a swallowed argument or a filter that matched nothing all
  look like a pass.
- **Reachability is measured, not deduced.** "Nothing calls this" and "not observable" are claims with a probe
  attached. Run the probe and record the result.
- **Vary the axis your current subject holds fixed.** A probe built while working on X inherits X's premise, so
  flip that property before believing a green result.
- **Compare against an independent implementation, not a round trip of your own.** A model that loses the same
  information on read and write passes its own round trip perfectly.

## 6. Docs and honesty

- **Keep docs current in the same change set.** Design docs, README, API docs and the project instructions
  describe the code as it is NOW. History (what changed, what was tried) belongs in the commit message and the
  changelog or dev log, never in the design doc.
  *Why: a stale design doc tells the next implementer to build the rejected approach.*
- **Implement from the design doc; a design correction updates the doc in the same change.**
- **Sweep docs on discovery.** When a doc is wrong, fix it and every other doc that repeats the stale fact, now.
- **Comments carry the WHY.** Document every public type and member; comment non-obvious logic; never narrate
  "this used to do X". A comment that lies is worse than none.
- **Cite the authority in the code.** A rule implemented from a spec names its clause at the implementation site.
- **Forensic commit messages.** A subject, then what changed, why, what was considered and rejected.
- **Report honestly and calibrated to the evidence.** Never write "verified", "complete" or "no regressions"
  without the evidence in hand. Say which gates ran, what they covered, and what is still pending.
  *Why: the closing summary line is where overreach creeps in, and it is the line others act on.*
- **Say it immediately when you were wrong.** Record the misstep, its cause and the fix, clinically. Never
  minimize, and never present a guess, a recollection or training data as measured fact.

## Using this skill

- **Before writing code:** read the governing spec or design, answer the structural question (section 2), and
  decide the complete scope (section 4).
- **While fixing a bug:** root cause, then sibling sweep, then the other arm, then the drift test (sections 3
  and 5).
- **Before calling it done:** the change is complete, swept, one-mechanism, verified by a check that has been
  seen to fail, and its docs are current. If any of these is not true, report it as debt, not as done.
- **In review:** every rule above is a finding category. A god class, a duplicated mechanism, a workaround or an
  unswept sibling is a defect even when the tests pass.

## Project hooks

This skill is the generic floor. A repository tightens it or adds to it in its `CLAUDE.md` (or `AGENTS.md`,
`CONTRIBUTING.md`) under a section such as **"Engineering standards"**:

```markdown
## Engineering standards
- Authority: <standard or spec, and the precedence when it leaves latitude>
- Architectural commitments: <settled decisions not to relitigate>
- Language/runtime: <versions, warnings-as-errors, analyzers>
- Docs that must stay current: <design docs, README, changelog, fix log>
- Work register: <the one place new defects and deferrals are filed>
```

**Project rules win on conflict.** Where a project sets a stricter rule, follow it. Where it deliberately relaxes
one (for example, a prototype that is explicitly throwaway), follow it and say so once. Settled architectural
commitments in the project instructions are designed within, not reopened.
