# Conflict markers between staging and committing

A green gate says nothing about a file no test loads. After `git add` and before `git commit` (every commit,
including WIP checkpoints and merge resolutions), run both:

```
git grep --cached -nI -e "^<<<<<<< " -e "^||||||| " -e "^>>>>>>> "
git diff --cached --check | grep -i "conflict marker"
```

Both must print **nothing**. Read the OUTPUT, not the exit code: `--check` also reports whitespace errors, and on a
CRLF file it flags every line as trailing whitespace, so a rule gated on its exit code is red on every commit and
gets abandoned. Then add a **repo-wide conflict-marker test** to the suite (scan every tracked text file for the
three marker lines) and see it fail once on a planted hunk before trusting it.
*Why: a blanket `git add -A` committed four unresolved conflict hunks into a script that no test imports, and they
passed three green gates, none of which looked at that file. Since the test was adopted, no marker has reached
main.* *(Validated 2026-09-28.)*
