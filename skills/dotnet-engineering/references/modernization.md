# Modernizing an existing .NET codebase

The language bar in `SKILL.md` says what new code looks like. This file is how to move an EXISTING codebase there:
the whole tree, in behavior-neutral steps, driven by analyzers rather than by hand. It is phase 4 of
`architecture-audit`. *(Practice — not yet validated: assembled from the analyzers' documented code fixes and the
behavior-neutrality contract; not yet run end to end on a large codebase.)*

## 1. Upgrade the platform first, alone

- **Target the latest STABLE .NET**, whose C# version comes with it. A preview SDK is a decision for the owner,
  not a default: previews change behavior and break analyzers between releases.
- **Change the pins in one wave, with nothing else in it:**
  - `global.json` (`sdk.version`, a `rollForward` policy such as `latestMinor`; `allowPrerelease` stays false unless
    a preview was chosen);
  - `<TargetFramework>` in `Directory.Build.props`;
  - `<LangVersion>` (or none, so the SDK default applies);
  - package versions in `Directory.Packages.props`;
  - CI's `setup-dotnet` version.
- **Named exceptions stay.** A Roslyn source generator or analyzer project targets `netstandard2.0` because the
  compiler hosts it there: a real consumer, and the one legitimate reason for that target.
- **Prove the upgrade neutral** with the full test suite on every OS, output differentials where the product emits
  artifacts, and a performance re-measure (runtime upgrades change JIT, GC and collection behavior).

## 2. Turn the analyzers on, then climb

- Set `<AnalysisLevel>latest-all</AnalysisLevel>` (or `latest-recommended` as a first step) with
  `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`. Every rule you don't want is disabled in `.editorconfig`,
  with a one-line reason.
- Take the backlog in waves, one rule per wave, never one file at a time.

## 3. One feature, one analyzer rule, one wave

For each modern idiom, enable its IDE rule, apply its code fix across the whole tree, review the diff, and prove it
neutral:

```
dotnet format style --diagnostics IDE0290 --severity info    # use primary constructors
dotnet format style --diagnostics IDE0300 IDE0301 IDE0302 IDE0303 IDE0304 IDE0305 --severity info  # collection expressions
dotnet format analyzers --diagnostics IDE0330 --severity info   # System.Threading.Lock instead of lock(object)
```

Features without a code fix, or where one needs judgment, go through `roslyn-analysis`'s rewriter harness
(dry-run first; it preserves encodings and line endings):
- the `field` keyword, replacing a backing field used by one property;
- C# 14 extension members, replacing static helper classes of extension methods;
- `params ReadOnlySpan<T>`;
- `FrozenDictionary`/`FrozenSet` for static lookup tables;
- `[GeneratedRegex]` for constant patterns;
- `required` members instead of constructor-validated setters;
- switch expressions over type-test ladders.

**Keep a wave only if it is neutral AND not slower.** A modern idiom on a hot path (a primary constructor that
captures, a collection expression that allocates) is measured against the baseline (`performance-diagnosis`), and
reverted with a recorded reason if it regresses.

## 4. What NOT to modernize

- Code about to be deleted.
- Generated code: change the generator instead.
- Public API surface that others consume: modernizing it is a breaking change and needs its own decision.

## 5. Keep it modern

- Leave the analyzer rules on at error severity, so new code can't regress.
- Record the current SDK and language target in one place: the build props, which CI reads, not a document.
