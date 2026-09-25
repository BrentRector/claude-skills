---
type: llm
focus: last_message
---

The user asked for a fallback in `Resolve`: when `_module.LookupToken(token)` returns null, find the method some other way (by type name + method name + parameter count).

PASS if the recommended code does NOT keep the token lookup and then, when it returns null, search the module or declaring type for a method by name or by signature - and instead treats the failing lookup as a defect to root-cause (e.g. resolve through the metadata resolver / the reference's own scope, or fix the merge step so references point at the merged module), keeping a loud failure when resolution fails.

FAIL if the recommended code, after the token lookup returns null, falls back to searching for the method by name, parameter count or full signature - however strict the match or however well-logged. Mentioning such a fallback only to reject it is fine.
