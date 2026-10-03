## 1. Guard hooks that block forbidden commands

1. Encode **only the rules the owner stated**. A rule you think is missing (a refspec rule, "PRs only") is a
   proposal: ask, never add it silently. Every extra rule blocks the owner's own work.
2. Write one rule per forbidden command in `guard-rules.json`: `pattern`, `reason`, `instead` (the right
   alternative, as a command), `block` examples, and `allow` examples. The allow list holds the rule's legitimate
   neighbours, for example `git stash list` for a stash rule, or a feature-branch push for a push-to-main rule.
3. Set `"scope": "repo"` on every rule that encodes this repository's policy: its landing route, protected
   branches, stash hygiene. Only rules about the harness itself, such as escapes in heredocs, stay `"any"`.
4. Register the guard for every shell tool (`"matcher": "Bash|PowerShell"`, see `templates/settings.json`), with a
   plain `python ...` command and no `|| exit 2`.
5. Run `python .claude/hooks/guard_commands.py --selftest --settings .claude/settings.json` until it is GREEN, and
   add the same command to CI. A workflow file that has never run is not a gate: until you have seen a green CI
   run, report CI as unproven.

**Contract.** Every item is required.

| The guard… | Why |
|---|---|
| exits 2 with a stderr message naming the rule and an `Instead:` command | A bare "no" invites the agent to rephrase the command; a named alternative gets followed. |
| covers every shell tool (Bash and PowerShell) | A rule on Bash alone is bypassed by the first PowerShell call. |
| **fails OPEN**: unparseable input, a missing or corrupt rules file, a git error or a crash all exit 0 (with a stderr note) | A guard that fails closed turns one bad field, a missing interpreter or a harness format change into a block on every shell call in every session and subagent. These rules are workflow conventions with real backstops (branch protection, CI). A security boundary belongs in permissions, a sandbox or the server. *(Practice — not yet validated: no production measure of fail-open silent passes against fail-closed blocks.)* |
| writes stderr as UTF-8 | Windows otherwise writes the console code page, and the agent reads mojibake. *(Practice — not yet validated: one incident so far.)* |
| is **scoped to this repository**: a `repo` rule fires only when the command's working tree has the same git common dir as `$CLAUDE_PROJECT_DIR`, following `cwd`, `cd`/`Set-Location` and `git -C` | The same session also works in other repos, and each has its own rules. A push rule keyed on the branch name alone blocks `git push origin main` everywhere. *(Practice — not yet validated: not yet exercised across a rename or a second checkout in production.)* |
| has a self-test in CI proving each rule fires on `block`, passes `allow`, and passes when the same command runs in an **unrelated** repo | A guard is only trusted once its failure branch has fired. Two checkouts of one repo don't test scope, because they share it. *(Validated 2026-09-28.)* |

Don't use `permissions.deny` for these rules. Deny rules match a prefix, can't see which repository a command runs
in, and can't tell the agent what to do instead.
