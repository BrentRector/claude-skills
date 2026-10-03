# Checkpointing rules in detail

The detail behind agent-fleet section 4 (the checkpoint table stays in `SKILL.md`): stash, checkpoint files, conflict markers, the stamped handoff, stage inputs. Read it before writing the checkpoint and resume block of a brief, and before resuming or merging another agent's worktree.

## 4. Checkpoint to disk after every unit of work


- **Never use `git stash` for WIP; commit it instead** - and that includes the implicit stash of
  `git rebase --autostash` / `git pull --autostash`. *Why: the stash stack is shared by every linked worktree, so one
  agent's `stash pop` can take another agent's work. *(Practice — not yet validated: one near-miss recorded; no loss yet traced to the shared stack.)**
- **Keep checkpoint files out of landings**: add them to `.gitignore` and unstage them explicitly before
  committing. *Why: a checkpoint that reaches main conflicts with the next agent's checkpoint.*
- **Assert on conflict markers between staging and committing**, at every checkpoint and every landing commit:
  ```
  git grep --cached -nI -e "^<<<<<<< " -e "^||||||| " -e "^>>>>>>> "
  git diff --cached --check | grep -i "conflict marker"
  ```
  Both must print nothing. Read their OUTPUT, not their exit codes: `--check` also reports whitespace, and on a
  CRLF file it flags every line, so a gate on its exit code is always red and gets dropped. Back it with a
  repo-wide conflict-marker test, seen to fail once on a planted hunk (`test-gate`). *Why: an implementer's
  blanket `git add -A` checkpoint committed four unresolved hunks into a script that no test imports, the lander
  resolved conflicts by judgement and never re-checked, and the markers passed three green gates. Since the test
  was adopted, no marker has reached main.* *(Validated 2026-09-28.)*
- **Stamp the handoff.** `STATUS.md`'s first line is `STATUS-AT: <sha>`, the commit it describes, written AFTER
  the checkpoint commit (the file is untracked and ignored, so writing it never moves HEAD). An agent that resumes
  a worktree, or merges a predecessor's branch, first runs `references/status_delta.py <worktree>` and reads what
  it prints:
  - `CURRENT`: the summary covers every commit; read it, then only the uncommitted changes it lists.
  - `STALE by N`: read the summary plus ONLY the N commits it lists.
  - `UNSTAMPED` or `DIVERGED` (no stamp, or a stamp rebased or amended away): read every commit since the base.
  The summary stays navigation, never evidence. *Why: an agent killed after a commit but before rewriting its
  summary leaves one that silently omits the last commits. Without a stamp a successor cannot tell stale from
  current, so the only safe rule is to re-read the whole branch on every resume, which spends the orientation the
  summary was written to save. Measured with 88 fresh resumers over 22 scenarios from 11 real branches: without the
  stamp, agents misjudged what the summary covered in 11 of 44 resumes; with it, in none. Tokens fell about 17 %
  overall and 31 % when the summary was current.* *(Practice — not yet validated: a controlled A/B on 11 branches; resume accuracy in production is not yet measured.)*
- **Design workflow stages to read their inputs from disk** (`out-<slug>.json`). *Why: then a rewritten or
  resumed script never re-runs completed stages.* *(Practice — not yet validated: adopted after a resume by run id failed; not separately measured.)*
