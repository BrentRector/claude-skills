# Report format, posting and run scale (Step 8 and Scale)

Moved out of `SKILL.md` verbatim. Read it before writing the Step 8 report, before posting to a PR, and before an audit-sized run.

## Step 8 detail

```markdown
# Review
**Target:** <diff / PR / subsystem>  **Context:** scale=<...>, consequence=<...> (<stated | inferred from ...>)
**Dimensions run:** <list>; skipped: <dimension - reason>
**Verification:** <N> candidates -> <M> survived

## Critical / ## Warnings / ## Suggestions   (omit empty sections)
### path/file.ext:L10-L25 - <title>
Scenario / Why / Fix, as above.  Siblings: <locations, or "swept <pattern> in <scope>: none">
```

If nothing survives, say so plainly. **Findings become tracked work**: if the project names an issue tracker or work
register, offer to file each surviving defect there rather than leaving it in prose that evaporates. *(Validated 2026-09-28.)*

**Posting is confirm-first.** For a PR, show the report and ask before posting; then write it to a temp file and
post with `gh pr review <n> --comment --body-file <file>` (a file avoids shell-escaping damage). Never approve or
request changes on the author's behalf unless asked.

## Scale

- **"Review this diff"** - the selected dimensions, one finder per dimension, single-skeptic verification.
- **"Audit this subsystem" / "be comprehensive"** - several finders per dimension with different starting points,
  3-5 independent skeptics per finding (majority must fail to refute), plus a **completeness critic** that asks what
  was *not* examined - files, paths, error branches, configurations - and sends finders there. *(Validated 2026-09-28.)*
