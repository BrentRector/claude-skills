---
type: llm
focus: last_message
---

PASS if the answer's fix is to stop translating command strings and instead write each check's command
explicitly for each operating system (for example a per-OS command field, separate .cmd and .sh scripts, or
an argument list run without a shell, chosen by OS), and it notes that `exit /b 7` is cmd-only syntax the
substitution missed (sh treats it differently, hence exit code 2).

FAIL if its fix is to add more substitution rules (for example mapping `exit /b` to `exit`) or a smarter
translator, even if it also explains the exit code correctly.
