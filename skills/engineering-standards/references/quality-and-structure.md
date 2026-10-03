# Quality bar and design structure (engineering-standards sections 1 and 2)

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
  wrong answer to a question the first path should have answered correctly. *(Validated 2026-09-28.)*
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
  smallest diff that fits the original guess. *(Validated 2026-09-28.)*
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

