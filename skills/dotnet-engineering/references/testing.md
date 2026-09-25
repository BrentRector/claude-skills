# Testing .NET code

Adapted from dotnet/skills `plugins/dotnet-test/skills/filter-syntax`, `test-gap-analysis` and
`test-smell-detection` (MIT, © .NET Foundation and Contributors). Changes: condensed; .NET SDK 8/9 argument forms
dropped; zero-match and witness rules added.

## 1. Filters

### VSTest `--filter` (MSTest, NUnit, xUnit v2; also MSTest and NUnit on Microsoft.Testing.Platform)

Grammar: `<Property><Operator><Value>` joined by `|` (OR) and `&` (AND), grouped with parentheses.

| Operator | Meaning |
|---|---|
| `=` / `!=` | exact match / not |
| `~` / `!~` | contains / does not contain |

| Framework | Properties |
|---|---|
| MSTest | `FullyQualifiedName`, `Name`, `ClassName`, `Priority`, `TestCategory` |
| NUnit | `FullyQualifiedName`, `Name`, `Priority`, `TestCategory` |
| xUnit v2 | `FullyQualifiedName`, `DisplayName`, `Traits` (by trait name, e.g. `Category=Unit`) |

**The traps:**

- **Every term needs its own property.** `FullyQualifiedName~A|FullyQualifiedName~B` selects A and B.
  `~A|~B` matches **nothing**, and so does the mixed `FullyQualifiedName~A|~B`: the second term has an empty
  property name. A bare value with no operator at all (`--filter Parser`) is shorthand for
  `FullyQualifiedName~Parser`, which is why people assume the operator-only form also works. It doesn't.
- **Zero matches exits 0 under VSTest.** The only sign is "No test matches the given testcase filter" and
  `Total: 0`. Treat a zero or missing count as a failed gate. Under Microsoft.Testing.Platform a run of zero tests
  returns exit code 8, which scripts often swallow; set `--minimum-expected-tests <n>` to make the floor explicit.
- **`~` is substring.** `Name~Parse` also selects `ParseHeaderTests`, `ReparseFixture` and `NoParse`. When the set
  matters, use `=` on `FullyQualifiedName` or a namespace prefix ending in `.`.
- **Shell quoting.** `|` and `&` are shell operators: always quote the whole expression. In PowerShell, `!` and
  parentheses are safe inside quotes; in bash, `!` inside double quotes triggers history expansion interactively,
  so use single quotes there.
- **Commas and parentheses inside values** must be escaped with a backslash (`\,` `\(`), which matters for
  parameterized test names.

### xUnit v3 on Microsoft.Testing.Platform

xUnit v3 does **not** accept the VSTest expression. It has its own flags, each accepting several values:

| Flag | Selects |
|---|---|
| `--filter-class` / `--filter-not-class` | a class (wildcards allowed: `*LoginTests`) |
| `--filter-method` / `--filter-not-method` | a fully qualified method |
| `--filter-namespace` / `--filter-not-namespace` | a namespace |
| `--filter-trait "Name=Value"` / `--filter-not-trait` | a trait |
| `--filter-query "/asm/ns/class/method[trait=value]"` | the path query language; `*` matches a segment |

Translating `FullyQualifiedName~Foo` needs explicit wildcards: `--filter-class *Foo*`. Without them it is an exact
match and very likely selects nothing.

### TUnit

`--treenode-filter "/<Assembly>/<Namespace>/<Class>/<Test>"`, `*` per segment, properties as
`[Category=Smoke]` / `[Category!=Slow]`, OR inside a segment as `(A)|(B)`.

### Checking a filter before trusting it

1. `dotnet test --list-tests --filter "<expr>"` and count the lines. Compare with the number you expected.
2. After the real run, read `Total:` / `Passed:` / `Skipped:` from the summary or the TRX
   (`--logger trx`), not the exit code.
3. Wrap the repository's gate in a script that rejects an operator without a property and fails on a zero or
   missing count. A convention people have to remember is not a gate.

## 2. Writing tests that verify

- **The expected value comes from the authority**: the spec clause, the documented contract, a worked example
  derived by hand. Cite it next to the assertion. A value pasted from the current output only proves the code
  still does what it did.
- **Assert values, not "it ran".** An assertion on `DoesNotThrow`, a non-null result or an exit code alone
  verifies nothing about behaviour.
- **One behaviour per test, all of its observable outcomes.** Returned value, state change, exception type and
  side effect are separate observations; asserting one does not cover the others.
- **Hit every branch the spec names**, including the rejecting ones and the boundaries (`limit - 1`, `limit`,
  `limit + 1`). A test scoped to the reproduced bug leaves its siblings and the other arm of the dispatch
  unguarded.
- **Hermetic by default.** Temp files created and removed by the test, no network, time and randomness injected
  (`TimeProvider`, a seeded `Random`). A declared integration test may use a real resource; it still may not
  sleep for a fixed time.
- **Unique names for anything global** (assembly names, temp paths, ports), so parallel runs don't read each
  other's output.
- **Parameterize instead of branching**: `[Theory]` / `[TestCase]` / `[DataRow]` / `[Arguments]` with a
  `TheoryData<T>` or source method, never an `if` inside the test body choosing which assertion to run.

## 3. Test-gap analysis: would the tests catch a bug?

Answer by pseudo-mutation. The goal is a list of caller-visible behaviours no assertion observes, not a score.

1. **Set the scope** to the component or named risk. Turn a named risk into a list of public outcomes before
   reading code ("money math" means amounts, rates, tier boundaries, rounding, caps; not formatting).
2. **Run the narrowest existing test command once** and confirm tests executed (a count, not a build-only 0).
   If it can't run, continue statically and label findings *unverified*; don't debug the runner.
3. **Inventory outcomes.** For each public entry point: input partitions (every classifier arm, both sides of
   every guard, the default case), and every independent observation (return field, exception type, state
   transition, side effect). Write rows as `input -> expected outcome -> asserting test -> gap`.
   Authorization: every role × resource × action, especially the denials. Retries and guards:
   `invalid | first valid | last allowed | first blocked | later blocked`.
4. **Admit only observable mutants.** For a candidate edit (flip `<` to `<=`, drop a guard, change a constant,
   remove a side effect), name a witness input and state `witness -> original -> mutant`. If the two observations
   are identical on every input, it is equivalent: drop it. Replay the mutant against every existing asserted
   input first; if any assertion would change, it is already killed.
5. **Classify:** *Killed* (an assertion observes it), *Candidate survivor* (observable, unasserted, not run),
   *Survived* (applied, tests stayed green), *No coverage* (no test reaches the outcome), *Equivalent* (omit).
6. **Verify only when asked or when closing gaps:** apply one edit, run the narrow tests, revert immediately,
   confirm the clean baseline. Never leave a mutation in the tree.
7. **Close gaps** with one behaviour-focused test per gap, whose expected value comes from the authority. Re-apply
   the mutation and watch the new test fail, then restore.

Rank findings: security denials, money, errors and state changes first; wholly unasserted outcomes next;
weakly-asserted boundaries after; variants of already-asserted behaviour last. Verdict **Strong / Mixed / Weak**
from the completed inventory, never from the first few rows.

## 4. Test smells

Use the formal names (testsmells.org taxonomy) with evidence from the code, never from a method name. Severity
follows demonstrated risk.

| Severity | Smell | Evidence | Fix |
|---|---|---|---|
| High | **Missing await** (not in the catalog; report separately) | an async assertion or `Task`-returning call not awaited | `await` it; enable CS4014 / xUnit1030-style analyzers as errors |
| High | **Unknown Test** | no assertion, no expected-exception check, no mock verification | assert the observable outcome |
| High | **Conditional Test Logic** | an assertion behind `if` / `switch` / a loop that can skip it | split or parameterize |
| High | **Sleepy Test** | `Thread.Sleep` / `Task.Delay` waiting for an outcome | await the signal or poll with a timeout |
| Medium | **Mystery Guest** / **Resource Optimism** | an undeclared file, env var, database or network dependency | create it in the test, or declare the integration boundary |
| Medium | **Assertion Roulette** | several unlabelled assertions of the same shape; a failure doesn't say which | one behaviour per test, or messages / `Assert.Multiple` |
| Medium | **Sensitive Equality** | asserting `ToString()` output that is not the contract | assert the fields |
| Medium | **Eager Test** | one test drives several unrelated behaviours | separate tests |
| Medium | **Magic Number Test** | an unexplained oracle literal | name it and cite where it comes from |
| Medium | **Exception Handling** | `try { ...; Assert.Fail(); } catch { }` | `Assert.Throws<T>` and check the meaningful detail |
| Low | **Ignored Test** | `Skip = ...` / `[Ignore]`; an untracked reason ranks higher | fix it or file it in the work register |
| Low | **General Fixture** | shared setup most tests don't use | narrow the fixture |
| Low | **Empty Test**, **Redundant Print**, **Redundant Assertion**, **Duplicate Assert**, **Lazy Test**, **Constructor Initialization**, **Default Test** | as named | remove or merge |

Calibration: parameterized theories are not Conditional Test Logic; one assertion is never Assertion Roulette; a
declared integration test may use its real resource; a temp file created and deleted by the test is still a
Mystery Guest, just a low-severity one. If nothing material remains after calibration, say the suite is clean.
Never pad a report.
