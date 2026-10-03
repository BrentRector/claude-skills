## 4. Local cost telemetry

1. Ask first, and on a yes run `python .claude/hooks/readiness_check.py --enable-telemetry`. That writes
   `CLAUDE_CODE_ENABLE_TELEMETRY=1`, the OTLP `http/json` exporters and endpoint `http://127.0.0.1:4318` into the
   **user settings** (`~/.claude/settings.json`, or `$CLAUDE_CONFIG_DIR/settings.json`). That is per machine and never
   committed. It takes effect in the next session. *Why the user settings: Claude Code ignores telemetry-ENABLING
   variables in a project's `.claude/settings.json` and `.claude/settings.local.json`; a project may only turn
   telemetry off. Measured: with the switch in `settings.local.json`, nothing was exported while a check reading that
   same file reported "OK". The readiness check now flags a project file that sets the switch as dead
   configuration.* *(Practice — not yet validated: one instance so far.)*
2. `otlp_sink.py` is the loopback receiver. It is standard-library only and refuses protobuf with a 415. The
   readiness check starts it when it is down and reports REPAIRED.
3. `python .claude/hooks/usage_report.py [--by agent,skill,model] [--all]` reports tokens and cost per group. On
   the first real data, run `--keys` and add your Claude Code version's attribute names if a dimension shows only
   `-`.

## 5. LSP-first navigation

Add a `readiness.json` `lsp` entry per language: the plugin, the server binary, extra paths and the install
command. The line is OK only when both the plugin and the binary are present. Otherwise it is ASK-OWNER, and
nothing is installed without asking. When the LSP line is OK, find definitions, references and symbols with the LSP
tool before grep, and use grep for text.

The language server also reports diagnostics (unnecessary `using`, unused locals, analyzer hints) on every file an
agent edits. Tell agents to act on them: fix each diagnostic on a file they touched in the same change, or name in
the report why they did not. *(Practice, not yet validated: adopted 2026-10-01 after hints scrolled past in-flight
worktrees; no count yet of hints fixed or of review findings avoided.)*

## 6. Regression gates

- **Skill and agent edits:** plugin evals are the regression gate. Each changed rule ships with an eval case that
  beats the no-plugin baseline (this repo's `evals/README.md` explains the rule and how to read Δ). Run it before
  the push, and because it is billed, ask at that trigger.
- **Landings:** run a review step on the merged diff before the landing push (the lander template's step; the
  `review` skill or `/code-review`). A finding blocks the push. *(Practice — not yet validated: six or more reviewed batches have produced no confirmed finding yet.)*
