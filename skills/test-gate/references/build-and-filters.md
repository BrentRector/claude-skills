# Build fresh, filters that match nothing, confirming new tests ran

## Always first: build fresh

A no-build test run tests whatever binary was copied into the test output at the last full build.

- .NET: `dotnet build <Solution>.sln`, **the solution rather than one project**, then `dotnet test --no-build`.
  Building only the library does not re-copy it into the test projects' `bin`. Or just drop `--no-build`.
- Python: reinstall editable or compiled extensions (`pip install -e .`, rebuild the C extension) and clear
  stale `__pycache__` / `.pyc` only when you have a reason to think they're stale.
- JS/TS: rebuild workspace packages the tests import from `dist/` (`npm run build -w <pkg>`) before running.

The symptom: local stays green commit after commit while CI, which checks out clean and builds everything, has
been red since the first one.

Then confirm the build itself **succeeded**: a failed or incremental build can still leave a stale assembly
behind, so when in doubt, hash the assemblies the tests load. *(Validated 2026-09-28.)*

## A filter that matches nothing is a silent green

The most common false green is a selector that selects nothing and still exits 0.

- **.NET `dotnet test --filter`: every OR/AND term needs its own property.**
  `--filter "FullyQualifiedName~Parser|FullyQualifiedName~Lexer"` works.
  `--filter "~Parser|~Lexer"` matches **nothing**, and so does the mixed form `"FullyQualifiedName~Parser|~Lexer"`.
  Both print "No test matches the given testcase filter" and **exit 0**.
- **pytest `-k`**: an expression that deselects everything exits **5** ("no tests collected"), and CI scripts
  often swallow that code (`|| true`, or `[ $? -eq 5 ]` treated as a pass). `-k` also matches substrings, so a
  typo can quietly pick a different, smaller set than you meant.
- **Jest / Vitest `-t`**: a name pattern that matches nothing still loads the files, marks every test skipped
  and exits 0. (A `testPathPattern` that matches no file does fail, unless `--passWithNoTests` is set, which
  many configs set.)

**Fix:** read the **count**, not just the pass/fail word. `Total: 0` or "0 passed, 312 skipped" means the gate
did not run. Better still, wrap the gate in a script that normalises the filter and **fails on a zero or missing
count**. With several OR'd terms, check each term's own count: one dead term among live ones still prints
a clean verdict. *(Validated 2026-09-28.)*

## Confirm the new tests actually ran, by name

A test that was written but never discovered (wrong attribute, missing `test_` prefix, a file outside the glob,
a data-driven source that yields no cases, a class that isn't public) passes by never running. It is a red
failure even though nothing printed red. After adding tests, search the run's output for **their names** or list
them (`dotnet test --list-tests`, `pytest --collect-only -q`, `jest --listTests`) and check that the count went up
by the number you added. *(Validated 2026-09-28.)*
