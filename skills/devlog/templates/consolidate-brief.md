# Brief: consolidate the development log into CANDIDATE learnings

<!-- Give this to ONE agent, as a file it reads ("Read and follow <path>"). Fill the <placeholders>. A 1,750-entry
     log produced 145 candidate learnings and 15 open problems in about 30 minutes with this brief. Its output is
     NOT LEARNINGS.md: every candidate goes through templates/validate-brief.md, and only the VETTED ones are
     published or encoded into a skill or rule. -->

**Goal.** Turn `<DEVLOG.md or docs/devlog/>` (<N> entries, <first date> to <last date>) into `LEARNINGS-CANDIDATES.md`:
every learning the project appears to have paid for, as a CANDIDATE that a separate validation run will vet, leave
unproven or refute. The log records hypotheses as well as conclusions, so treat nothing you read as settled; your job
is to find the candidates and cite them precisely enough to be checked. Do not edit the log.

**Sources.** The log first. Also `<CLAUDE.md, the practices file, the memory or notes directory, evidence records>`
where they state a rule the log explains. Where they disagree with the log, the later dated statement wins, and the
disagreement is itself a finding.

**Work through the whole log**, oldest to newest, in chunks. After each chunk append your notes to
`<scratch>/learnings-notes.md` (entry range done, learnings found), so a restarted agent resumes instead of
re-reading. Do not sample: the report states how many entries were read.

**Each candidate gets an id (C1, C2, ...) and gives:**
- **Problem:** what was observed, or what it cost (with the number).
- **Root cause:** the mechanism as it was established at the time.
- **Fix:** what changed, and where it lives now (a link to the rule, script, skill or document that encodes it; or
  "not encoded").
- **Evidence:** measurements with n and dates, citing entry numbers; or "unmeasured".
- **When:** the date it was learned.

**Shape.** Group by theme (<suggested themes, or let them emerge>), oldest first within each theme, so a reader sees
how a practice evolved. A short intro says what the file is, the fields above and any terms of art.

**Keep what went wrong.** Failures, dead ends, rejected ideas and null results are learnings. Where a later entry
overturned an earlier claim, give both, and label the correction ("Correction, <date>: …"). Never silently keep only
the final answer.

**Accuracy over prose.** Every number traces to an entry. If the log does not establish a cause, write "cause not
established". Prefer one plain sentence to a paragraph.

**Do not act on any candidate:** do not edit a skill, rule, hook or document from this run. Only validated
learnings are encoded.

**Close with two lists:**
1. **Open problems:** measured or observed, not solved.
2. **Not yet acted on:** lessons the project learned that its rules, tools or documents do not carry yet, and any
   place where a current rule CONTRADICTS a learning. Contradictions are the most valuable output: one surfaced this
   way was a documented setting the tool silently ignored.

**Report back:** entries read (all <N>, or which were skipped and why), candidates written, open problems, items in
"not yet acted on", every contradiction found, and anything you could not interpret.
