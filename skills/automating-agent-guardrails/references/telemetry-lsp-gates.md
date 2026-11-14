## 4. Local cost telemetry

1. Ask first, and on a yes run `python .claude/hooks/readiness_check.py --enable-telemetry`. That writes
   `CLAUDE_CODE_ENABLE_TELEMETRY=1`, the OTLP `http/json` exporters and endpoint `http://127.0.0.1:4318` into the
   **user settings** (`~/.claude/settings.json`, or `$CLAUDE_CONFIG_DIR/settings.json`). That is per machine and never
   committed. It takes effect in the next session. *Why the user settings: Claude Code ignores telemetry-ENABLING
   variables in a project's `.claude/settings.json` and `.claude/settings.local.json`; a project may only turn
   telemetry off. Measured: with the switch in `settings.local.json`, nothing was exported while a check reading that
   same file reported "OK". The readiness check flags a project file that sets the switch as dead configuration.*
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
the report why they did not.

## 6. Regression gates

- **Skill and agent edits, in a repository that ships skills or agent definitions with an eval suite:** plugin
  evals are the regression gate. Each changed rule ships with an eval case that beats the no-plugin baseline (the
  `brent-tools` repository's `evals/README.md` explains the rule and how to read Δ). Run it before the push, and
  because it is billed, ask at that trigger.
- **Landings:** run a read-only review of each branch when it is DONE, before the enqueue step (the `review` skill's
  branch form or `/code-review`); a confirmed finding goes to the implementer or a finisher and blocks the enqueue.
