---
name: cross-platform
description: Use when code, tests, scripts or agents must work on both Windows and Linux (including WSL), when CI runs on an operating system the local gates do not, when a Windows-hosted agent edits files or runs shell commands, or when something passes on one OS and fails on the other. Covers running the other OS's CI legs locally before a push, path and build-path assumptions, line endings and byte-exact edits, shell and console encoding traps, and git across the Windows/WSL boundary (never export GIT_DIR to test processes). Not for platform-specific product features.
---

# Cross-platform: Windows and Linux without surprises

**A test that passes on one operating system proves nothing about the other.** Paths, line endings, shells, console
encodings, file locking and git configuration all differ, and each difference is invisible from the side you are
on. Make the other side cheap to check before you push, and write code that never has to guess which side it's on.

*Why: in one 24-hour stretch of a Windows-hosted, Linux-CI project, eight separate incidents came from these
differences: a Windows path literal that was relative on Linux, build paths baked into binaries, git unable to read
a worktree across the boundary, a line-ending setting visible to only one git, a git variable that let a test
corrupt the shared repository, a text tool that silently rewrote a file's line endings, escapes mangled on their way
into a shell, and a console that could not print a character.* *(Practice — not yet validated: the rules below each
come from one incident.)*

## When to use

- CI runs on an OS your local gates don't (Linux CI with Windows development, or the reverse).
- A test, script or tool touches paths, processes, shells, files, git, environment variables or encodings.
- An agent on Windows edits files or composes shell commands.
- Something passes on one OS and fails on the other.

## 1. Run the other OS's CI legs locally, before the push

- **Every gate runs the other OS's legs**, landers and implementers alike, when the cost allows. Measure it: in one
  project the whole Linux test population ran under WSL in about 3–4 minutes, so no selection of "platform-sensitive
  changes" was worth its misses.
- **Build and test a clone on the target OS.** Clone the committed HEAD (`git clone --shared` borrows the object
  store read-only) onto the target's own filesystem, then build and test it there, the way CI does. Don't run
  binaries built on the other OS: anything that embeds build paths breaks (see 2).
- **Export nothing into the original tree.** The gate's own reads pass their git settings inline (`git -c …`).
- **Keep a drift test** that holds the local legs equal to the test projects the CI jobs run, and see it fail once on
  a planted gap.

*Why: a new test was green in every Windows gate and red in CI's Linux unit job, a ~30-minute round trip and a
dropped change. The local Linux leg reproduced exactly that one red in about 2.5 minutes.* `agent-fleet/references/landing.md` carries
the fleet rule. *(Practice — not yet validated.)*

## 2. Paths: never assume the host's shape

- **Never feed a path literal from one OS to another OS's path API.** `Path.GetFullPath(@"E:\repo\x")` on Linux is a
  RELATIVE path under the current directory. A test that plants a path must plant the form that is real on the OS
  it runs on, so it proves the code on each OS rather than only on the author's.
- **Build paths are embedded.** `[CallerFilePath]`, source-relative fixture lookups, debug symbols and some
  generators bake the BUILD machine's absolute paths into the binary. Binaries built on Windows and run on Linux
  resolve `E:\…` as relative. Measured: 363 false test failures. Build on the OS that runs the tests.
- **Case and separators.** Linux file names are case-sensitive, and Windows accepts both separators. Compare paths
  with the platform's rules, and join them with the platform's API.
- **Drive letters and backslashes in tests** are the first thing to search for when a test fails only on Linux.

*(Practice — not yet validated.)*

## 3. Line endings and byte-exact edits

- **Know which files are CRLF**, and edit them as BYTES: read bytes, replace, write bytes, then check that the diff
  touches only the intended lines. Line-oriented text tools can normalize every ending. Measured: a one-line `sed`
  edit to a CRLF log turned its whole top section into LF, a 493-line diff for a 2-line change.
- **Some files must stay LF.** Shell scripts run by bash, and scripts a tool refuses to run with CR in them: a
  workflow runner rejected a script whose CRLF read as "control characters". On Windows, Python's `write_text` emits
  CRLF, so write bytes or pass `newline="\n"`. Pin the rule in `.gitattributes` (`*.sh text eol=lf`).
- **`core.autocrlf` lives where the other git can't see it.** Git for Windows sets it in its SYSTEM config, so Linux
  git on the same tree (through WSL) reports every CRLF-checked-out file as modified. Measured: 9,543 "changes" on a
  clean tree. Pass `-c core.autocrlf=true` inline when reading a Windows checkout from Linux.
- **BOMs.** An encoding that adds a byte-order mark (Python's `utf-8-sig` when writing) changes the file's first
  bytes, and a parser or a diff sees them.

*(Practice — not yet validated.)*

## 4. Shells, commands and consoles

- **Write per-OS commands explicitly; never translate one OS's command string into another's.** A "cross-platform"
  helper that replaced `>nul` with `>/dev/null` left the cmd-only `exit /b 7` untouched, and on Linux `sh` returned
  exit code 2, not 7. A substitution covers only the tokens you thought of.
- **Don't send escape-heavy scripts through heredocs or nested quoting.** Tool and shell layers each get a chance to
  rewrite backslashes. Write the script to a file with a file-writing tool and run the file.
- **Console encoding.** A Windows console's default code page (cp1252) cannot print many characters, and a script
  that prints them crashes, not the code under test. Set `PYTHONIOENCODING=utf-8` or reconfigure stdout to UTF-8 in
  the script.
- **Environment variables.** Their names are case-insensitive on Windows and case-sensitive on Linux.
- **Process semantics.** Exit codes, signals and file locking differ: Windows locks an open file against deletion,
  and Linux does not. A test that depends on locking or ACLs is proven only on the OS it runs on.

*(Practice — not yet validated.)*

## 5. Git across the Windows/WSL boundary

- **A Windows worktree is not readable by Linux git as-is.** Its `.git` is a file naming a Windows gitdir
  (`gitdir: E:/repo/.git/worktrees/x`), and a tree under `/mnt` trips git's ownership check (`safe.directory`).
- ⛔ **Never EXPORT `GIT_DIR` or `GIT_WORK_TREE` into processes that run tests.** A test that creates its own scratch
  repository (`git init`, a commit, `git worktree add` in a temp directory) is silently redirected to the REAL
  repository.
  - Measured: `core.worktree` was written into the shared `.git/config`, and every git command in every checkout
    failed until a person removed it. An agent was (rightly) denied the permission to change shared config.
  - Pass git settings inline for your own reads, and run tests in a clone (1).
- **Tests that create repositories must be hermetic.** Drop every variable `git rev-parse --local-env-vars` lists
  before running git in a scratch repository.
- **A tripwire.** A gate can snapshot the real repository's `HEAD` and `core.worktree` before running and fail loudly
  if either changed.

*(Practice — not yet validated.)*

## Checklist before pushing a change that touches paths, processes, files, shells or git

- [ ] The other OS's legs ran locally, on a clone built there, and are green.
- [ ] No path literal from one OS reaches another OS's path API; tests plant host-native paths.
- [ ] Nothing depends on build-machine paths, or the tests are built on the OS that runs them.
- [ ] CRLF files were edited as bytes, and the diff touches only the intended lines.
- [ ] Scripts that must be LF are LF, pinned in `.gitattributes`.
- [ ] Per-OS commands are written explicitly, not translated.
- [ ] No git variables are exported to child processes; scratch-repository tests scrub git's local variables.
