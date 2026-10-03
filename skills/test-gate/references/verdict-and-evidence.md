# Reading the verdict, missing observations, proving a gate can fail

## Read the verdict line, not the exit code

1. **Redirect the full output to a file.** Never `| tail -N` it: that drops the failing test's name, which is
   the one thing you need. Then grep the file for the summary (`Passed!|Failed!|Total:`,
   `=== .* passed`, `Tests: `) and for crashes (`crash|abort|Segmentation|OutOfMemory|Failed: *[1-9]`).
2. **Never chain anything after a test or build run** with `&&`, `||` or `;`, and above all never `git commit`
   or `git push`. In `test | tail && git push`, the exit code is `tail`'s. Run the gate alone to a log, read the
   verdict, then take the next step in a separate command. To keep the status in the same call, append
   `; echo "EXIT=$?"` (read-only commands on the log may follow that). This is cheap to enforce with a guard hook
   (`automating-agent-guardrails`, rule `no-chain-after-verdict`); a prose rule alone was broken after it was
   written. *(Validated 2026-09-28; the hook form is not yet proven in production.)*
3. **Never edit source while a gate is running.** Legs that compile from the working tree will pick up
   half-made edits and report failures that aren't real. Staging first doesn't protect you. Work on docs or the
   commit message while it runs. *(Practice — not yet validated: no before/after measure of false reds.)*
4. **Run long legs one at a time** when one of them rebuilds. A rebuild in the middle of another leg's
   `--no-build` run leaves that leg with no verdict at all.
5. **Know which kind of failure you're looking at before you diagnose it.** A stack trace, a compile error, a
   validation or diagnostic message and a timeout (usually an infinite loop) are four different problems.

## A missing observation is not a negative one

A verdict needs the evidence it claims to have. "Passed" means the thing ran to completion and was checked. A
killed process leaves truncated output, and truncated output can compare exactly like a wrong answer, or like a
correct one. A non-zero exit with no reason attached is a **lost result**, not a failure you can reason about.
Anything like that is **no verdict**, and should be reported loudly as such, never folded into pass or fail. *(Validated 2026-09-28.)*

- **Check the population, not only the failure count.** Pass, fail and no-verdict should add up to the declared
  set. A harness that only counts failures will report "all green" when a case disappears.
- **Compare against a committed baseline or manifest,** never a number someone remembers.
- **Compare differential or snapshot results case by case, never by totals.** Totals that barely move can hide
  one fix plus two regressions. *(Validated 2026-09-28.)*
- **A filter, ranker or selector tells you about what it returned and nothing about what it dropped.** Before
  you trust one, look at its complement. *(Validated 2026-09-28.)*
- Re-running something that produced no observation is legitimate. Re-running a failed assertion until it
  passes is not.

## A gate that has never failed proves nothing

Before trusting a new check, a new guard test or a watcher on a long job, **make it fail once**: restore the
defect, point it at an older revision, kill the process it watches. Make sure it fails **for the right reason**,
not because some unrelated problem had already turned it red. Then ask **what its scope leaves out** and whether
the reasoning behind each exclusion still holds. A guard can be green, correct, and aimed at the wrong
population. For long jobs, only positive evidence (the process exists, the log shows the expected phase line,
artifacts are growing) counts as proof that the job is alive. A broken monitor and a healthy job both look like
silence. *(Validated 2026-09-28.)*
