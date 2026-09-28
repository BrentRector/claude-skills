# Brief: validate a batch of candidate learnings

<!-- Give this to ONE agent per batch of candidates (about 10-20), as a file it reads ("Read and follow <path>").
     Use a fresh agent that did not write the candidates. Fill the <placeholders>. When every batch has reported,
     the orchestrator marks each candidate in LEARNINGS-CANDIDATES.md with its verdict and writes LEARNINGS.md from
     the VETTED ones only (see "Publishing" at the end). -->

**Goal.** Rule on candidates `<C12 to C27>` in `LEARNINGS-CANDIDATES.md`. Each is a claim the consolidation run read
out of `<DEVLOG.md or docs/devlog/>`; none is known to be true yet. **Your job is to try to overturn each one.** A
log records hypotheses as well as conclusions, and some were refuted later; a candidate you pass without checking
spreads that error into every skill and rule built on it. Do not edit the log or the candidates file.

**For each candidate, check all four. VETTED requires every one:**
1. **Root cause confirmed.** The cause is the one the project finally established, not a hypothesis a later entry,
   test or measurement overturned. Search the whole log for the topic after the candidate's date
   (`python <skills>/devlog/references/devlog.py search -i "<words>"`), not only the entries it cites.
2. **Evidence re-checked against primary sources.** Open the cited entries and, where they point further, the
   commit, test, script output or measurement record itself. Every number in the candidate matches its source, with
   the same n and the same conditions. A number that exists only in the candidate or in a later summary fails.
3. **No later contradiction.** No later log entry, rule, commit or document says otherwise. A later correction
   entry, a reverted commit or a rule that was removed is a contradiction.
4. **The fix was used and shown useful:** a measured effect (with n), or sustained use with no reversal (name the
   period and where it was used). A fix that was written but never exercised, or whose trial was null, fails this.

**Verdicts.**
- **VETTED:** all four hold. Record the sources you opened and the proof of use.
- **UNPROVEN:** nothing contradicts it, but one or more of the four is not established. Name exactly which, and what
  evidence would settle it (a measurement, a production run, a primary source that could not be found).
- **REFUTED:** a source contradicts it. Quote or cite the contradicting source (entry number, commit, file and line)
  and say what the correct statement is, if the source establishes one.

When in doubt between VETTED and UNPROVEN, rule UNPROVEN. A missing observation is not a positive one.

**Output:** `<scratch>/verdicts-<batch>.md`, appended after EACH candidate so a restarted agent resumes instead of
re-checking:

```
## C14 — <candidate title>
Verdict: VETTED | UNPROVEN | REFUTED
1 root cause: <confirmed / overturned by entry N / not established>
2 evidence: <sources opened; numbers matched or not>
3 contradictions: <none found after searching "<terms>" / entry N says ...>
4 proof of use: <measured effect with n / used from <date> to <date> with no reversal / none>
Missing (UNPROVEN) or contradicting source (REFUTED): <...>
```

**Report back:** counts of VETTED, UNPROVEN and REFUTED; every REFUTED candidate with its contradicting source; and
any candidate you could not rule on and why.

**Publishing (the orchestrator, after every batch).** Mark every candidate in `LEARNINGS-CANDIDATES.md` with its
verdict and the validation date; REFUTED and UNPROVEN candidates stay there, marked, and are never silently dropped.
Write `LEARNINGS.md` with the VETTED ones only, each recording its validation: the date, the sources checked and the
proof of use. Only a learning in `LEARNINGS.md` may be encoded into a skill, a rule, a hook or a `CLAUDE.md` block.
