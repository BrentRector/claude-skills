# Report format, posting and run scale (Step 8 and Scale)

## Step 8 detail

```markdown
# Review
**Target:** <diff / PR / subsystem>  **Context:** scale=<...>, consequence=<...> (<stated | inferred from ...>)
**Dimensions run:** <list>; skipped: <dimension - reason>
**Verification:** <N> candidates -> <M> survived

## Critical / ## High / ## Medium / ## Low / ## Info   (omit empty sections)
### path/file.ext:L10-L25 - <title>
Scenario / Why / Fix, as above.  Siblings: <locations, or "swept <pattern> in <scope>: none">
```

If nothing survives, say so plainly. **Findings become tracked work**: if the project names an issue tracker or work
register, offer to file each surviving defect there rather than leaving it in prose that evaporates.

**Posting is confirm-first.** For a PR, show the report and ask before posting; then write it to a temp file and
post with `gh pr review <n> --comment --body-file <file>` (a file avoids shell-escaping damage). Never approve or
request changes on the author's behalf unless asked.

## Severity

One scale for every finder, specialist agent and skeptic, and for the branch form's blocking threshold (which grades
block is the dispatch's to name: SKILL.md Step 1, and the `merge-queue-landing` skill). Grade a finding by what
it does, never raise it to make it block:

- **critical** - a reachable wrong answer, silent no-op, data loss or security hole, or a test or gate that cannot fail.
- **high** - a concrete failure reached on an ordinary path: a crash or loud failure on legal input, a false claim
  someone will act on, a new nondeterministic test.
- **medium** - a concrete failure that needs an unusual path, or a drift path (a duplicated rule, a god class, a
  convention-only invariant) not yet out of sync.
- **low** - a strength or clarity improvement; reported only when the calibration asks for it.
- **info** - an observation that needs no change.

The specialist agents (`agents/`) define their own classes on this scale. A finder that grades on the three-level
scale maps Critical to critical, Warning to high when an ordinary path reaches it and medium otherwise, and
Suggestion to low.

## Scale

- **"Review this diff"** - the selected dimensions in one finder, single-skeptic verification; one finder per
  dimension plus the matching specialists only for a large, cross-subsystem or high-consequence change (SKILL.md
  Step 5 says what each added agent costs and buys).
- **"Audit this subsystem" / "be comprehensive"** - several finders per dimension with different starting points,
  3-5 independent skeptics per finding (majority must fail to refute), plus a **completeness critic** that asks what
  was *not* examined - files, paths, error branches, configurations - and sends finders there.
