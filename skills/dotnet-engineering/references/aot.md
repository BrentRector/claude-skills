# Trimming and Native AOT compatibility

Adapted from dotnet/skills `plugins/dotnet-upgrade/skills/dotnet-aot-compat` (MIT, © .NET Foundation and
Contributors). Changes: condensed; multi-targeting, TFM conditions and netstandard polyfills removed (single
latest TFM); source generation promoted to the first strategy; run-the-published-binary step added.

## 1. Why the warnings matter

The trimmer and the Native AOT compiler decide statically what code is reachable. Reflection, `Type.GetType`
with a computed name, `Activator.CreateInstance`, dynamic code generation and reflection-based serializers hide
that from them. The IL warnings are the tools saying the published program **will** fail at run time on some
path. They are a correctness signal, not noise.

## 2. Turn the analysis on

```xml
<PropertyGroup>
  <IsAotCompatible>true</IsAotCompatible>   <!-- libraries: enables the trim, AOT and single-file analyzers -->
  <PublishAot>true</PublishAot>             <!-- apps that ship AOT -->
</PropertyGroup>
```

Then build with `--no-incremental` and collect every `IL####` warning. Put these properties in
`Directory.Build.props` when the whole solution ships trimmed. Make the IL warnings errors in CI once they reach
zero, so they stay there.

| Code | Meaning |
|---|---|
| IL2026 | calls a member marked `[RequiresUnreferencedCode]` |
| IL3050 | calls a member marked `[RequiresDynamicCode]` |
| IL2070 / IL2087 | reflection on a `Type` parameter without `[DynamicallyAccessedMembers]` |
| IL2067 / IL2072 / IL2075 | an unannotated `Type` flows into a place that requires an annotation |
| IL2057 | `Type.GetType(string)` with a non-constant name |
| IL2091 | a generic argument lacks the annotation the constraint requires |
| IL3000 | `Assembly.Location` is empty in single-file and AOT apps |

## 3. Fix in this order

Triage by code and count first; the largest group usually has one mechanical fix.

1. **Replace reflection with source generation.** This removes the warning and the run-time cost together.
   - `System.Text.Json`: one `JsonSerializerContext` with `[JsonSerializable(typeof(T))]` for every type you own,
     and every call site passes `MyContext.Default.T`. Set `JsonSerializerIsReflectionEnabledByDefault=false` so a
     forgotten call site fails loudly. For types you don't own, use their own writer (`IJsonModel<T>`) or a
     hand-written `JsonConverter<T>` registered on the context.
   - `[GeneratedRegex]` for `Regex`, `[LoggerMessage]` for logging, `[LibraryImport]` for P/Invoke, the
     configuration binder source generator, and typed factories instead of `Activator.CreateInstance`.
   - Reflection-only serializers (Newtonsoft.Json, `XmlSerializer`, `BinaryFormatter`) are replaced, not
     annotated around.
2. **Flow `[DynamicallyAccessedMembers]`** from the innermost reflection call outward. Annotating a parameter
   pushes the requirement to every caller, and a caller's annotation must include at least the callee's member
   types. Rebuild after every 5-10 fixes; new warnings appear one level out.
3. **Refactor what breaks annotation flow.** A `Type` boxed into `object`, `object[]`, an untyped collection or an
   interface without the annotation loses it. Pass it as a dedicated annotated parameter or a typed field. Better
   still, replace the `Type` with a generic parameter or a delegate, so no reflection is needed.
4. **Label what is truly dynamic** with `[RequiresUnreferencedCode("why")]` / `[RequiresDynamicCode("why")]`.
   This propagates to callers and tells them honestly; it is the last resort, and the message names the reason.

## 4. Never

- `#pragma warning disable IL....` : the analyzer goes quiet, the trimmer still removes the code.
- `[UnconditionalSuppressMessage]` to reach zero. It tells the trimmer too, so it can no longer protect you. It is
  acceptable only with a justification proving the code is safe (for example, the members are rooted another
  way), written in the attribute's `Justification`, and reviewed as such.
- A reflection fallback "in case the generated path misses a type". That is a second mechanism that only runs
  in the configuration nobody tests.
- Chasing warnings inside a dependency you can't change. Record it, choose a trim-safe alternative, or isolate
  the call behind a `[RequiresUnreferencedCode]` boundary.

## 5. Zero warnings is necessary, not sufficient

Publish (`dotnet publish -c Release -r <rid>`) and run the test suite, or a smoke test covering every
serialization, plugin and reflection path, **against the published binary**. The analyzers can't see code
reached through strings in configuration files. Keep the published binary's size and startup time as tracked
numbers; a jump is a signal that something is being rooted wholesale.

If the project rewrites IL after build (an obfuscator, a weaver), verify AOT publishing on the rewritten output,
not only on the compiler's output.
