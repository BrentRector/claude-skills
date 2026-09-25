---
type: llm
focus: last_message
---

The task: a `CommandRegistry` for a CLI published with PublishTrimmed=true, mapping command names to ~30 ICommand implementations.

PASS if the production `CommandRegistry` builds its entries explicitly (a hand-written list/array of `new XCommand()` entries, or a source generator that emits that list at compile time) and does NOT discover command types at run time by scanning an assembly (GetTypes/GetExportedTypes/Activator.CreateInstance) in the shipped code. Reflection used only inside a TEST that cross-checks the explicit list is fine and does not cause a FAIL.

FAIL if the production registry discovers commands by reflection at run time (even with [DynamicallyAccessedMembers] annotations or a trimming caveat).
