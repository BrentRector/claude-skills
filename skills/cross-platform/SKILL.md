---
name: cross-platform
description: Use when code, tests, scripts or agents must work on both Windows and Linux (including WSL), when CI runs on an operating system the local gates do not, when a Windows-hosted agent edits files or runs shell commands, or when something passes on one OS and fails on the other. Covers running the targeted leg on both OSes in every local gate (CI's merge group runs the whole population), host-only witnesses (a filesystem CI lacks), one line-ending format (LF) enforced, path and build-path assumptions, shell and console encoding traps, and git across the Windows/WSL boundary (never export GIT_DIR to test processes). Not for platform-specific product features.
---

# Cross-platform: Windows and Linux without surprises

**A test that passes on one operating system proves nothing about the other.** Paths, line endings, shells, console
encodings, file locking and git configuration all differ, and each difference is invisible from the side you are
on. Make the other side cheap to check for every change, and write code that never has to guess which side it's on.

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

## 1. The targeted leg runs on both OSes; the whole population runs in CI

- **Every local gate runs the TARGETED leg on both hosts** the project supports: natively, then, under the same gate
  slot, the same targeted leg in a clone on the other OS (for a Windows host, a WSL clone), fail-fast native first.
  This holds for the implementer and for the landing (enqueue) step alike. *Why: in one measured campaign (2026-10-10)
  3 of 38 landed changes had reds only on Linux, all in the changes' OWN tests (a locale golden whose text differs by
  OS, a lock-race fix red 10 of 10 on Linux, a path-length test), and each was caught by the other-OS run before a CI
  round trip. A targeted leg there costs the clone and build (about 1–2 min) plus the leg.* *(Owner decision
  2026-10-11; practice, not yet validated as a gate shape.)*
- **The WHOLE population runs in CI, on every OS, on the merge group** — never as a local gate on either OS. Running
  CI's full legs locally (5–10 min for the other OS's legs in that campaign, much longer under load) is what goes;
  keep it only as the tool that REPRODUCES a CI red. *Why: in the same campaign local whole-population runs were 41 %
  of the landing time, mostly red from the host's load, while CI ran the same population on 20 free runners in 13 min.*
  *(Validated 2026-10-11 (measurement); the redesign's effect is not yet measured.)*
- **Host-only witnesses run locally at every gate.** Some tests reproduce only on the developer host, because its
  FILESYSTEM differs from CI's runners: ReFS (a Windows Dev Drive) deletes differently from NTFS, and a race between
  an open and a delete-pending file reproduced locally in 20 of 7,200 probes may never reproduce on a runner. Give
  those test classes a trait naming the property (`Host=ReFS`), put every test with it in the local targeted leg
  whatever the diff, derive the membership from the trait, never a list, and keep a drift test that the known
  witnesses carry it. List the filesystem in the local-versus-CI survey (1b).
- **Build and test a clone on the target OS.** Clone the committed HEAD (`git clone --shared` borrows the object
  store read-only) onto the target's own filesystem, then build and test it there, the way CI does. Don't run
  binaries built on the other OS: anything that embeds build paths breaks (see 2).
- **Export nothing into the original tree.** The gate's own reads pass their git settings inline (`git -c …`).
- **Keep a drift test** that holds the repro run's legs equal to the test projects the CI jobs run, and see it fail
  once on a planted gap.

*Why the repro run is kept: a new test was green in every Windows gate and red in CI's Linux unit job, a ~30-minute
round trip and a dropped change; the local Linux legs reproduced exactly that one red in about 2.5 minutes.*
`agent-fleet/references/landing.md` carries the fleet rule. *(Practice — not yet validated.)*

## 1b. CI's environment is a build input: pin it, declare it, reproduce it locally

**The invariant, under a merge queue: a pull request the queue bounces is a defect fixed on its branch before it is
enqueued again.** CI's merge-group run is the whole-population regression net, so a red there in a test OUTSIDE the
targeted scope is the net working. A red INSIDE the targeted scope is also a defect in the LOCAL process: find why the
targeted gate did not see it and fix that in the same change (a missing leg, an unpinned tool, a setting CI has and the
local run lacks, a filesystem difference), then sweep for the others like it. Keep a drift test that maps every CI job to a local leg
or to a recorded reason it cannot run locally.

- **Pin the runner image and keep the local environment the same release.** A floating label (`ubuntu-latest`) moves when
  the provider decides, so no local gate can match it. Pin the image (`ubuntu-26.04`) and keep the local distro on the same
  release (a WSL distro can be upgraded in place). The provider's own migration notice is the warning: read it.
- **A tool that reads text with the platform's default charset has a hidden input.** A parser generator on the JVM read a
  grammar as UTF-8 locally (Java 18+ defaults to UTF-8) and as Cp1252 on the Windows CI runner, so a set of Unicode
  characters became repeated Latin characters: an error only in CI, invisible to every local gate. Declare the encoding in
  the tool's invocation (`-encoding UTF-8`) and use UTF-8 everywhere, rather than avoiding non-ASCII text. Reproduce the
  CI behaviour locally with the JVM option `-Dfile.encoding=COMPAT`, which makes the JVM use the native charset, and keep a
  drift test that the invocation passes the encoding. Write characters that do not display (controls, noncharacters) as
  Unicode escapes so a reader can see them.
- **Run every CI job that can run locally.** A CI job with no local equivalent (here a guard job whose conformance loop ran
  only on CI) is the next CI-only red. Survey the differences once (runner image, SDK, JDK and shell patch versions, Debug
  versus Release, locale and time zone, compile caches, shard composition, jobs and audits with no local counterpart) and
  settle each as identical, reproduced locally, or irreducible with the reason recorded.

*Why: two finished changes were dropped from landings in a day for failures that only CI could see (the charset, and the
guard job), each costing a ~30-minute CI round trip.* *(Practice — not yet validated: two measured incidents; the pin and
the survey are recent.)*

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

## 3. One line-ending format, LF, enforced

**Standardize on LF in the working tree on every OS, and enforce it.** The measured shape of the problem in one
repository: the object database was already LF for 15,234 of 15,500 text files; only the WORKING TREE differed by OS,
under `core.autocrlf=true`, so a Windows gate and a Linux gate tested different bytes of the same commit, scripts died
on `\r`, a workflow script was refused as containing "control characters", and a single CRLF log needed a
byte-splicing insert tool. The owner's call (2026-10-11): "We should probably standardize on a single line-ending
format. CRLF vs others keeps biting us." *(Practice — not yet validated: adopted 2026-10-11.)*

- **`.gitattributes` first rule: `* text=auto eol=lf`.** Name any file that must be CRLF explicitly, with its reason
  (`*.bat text eol=crlf  # cmd.exe needs CRLF`). The attribute wins over every developer's `core.autocrlf`, so the
  setting no longer decides what a gate tests.
- **One normalization landing**: add the rule, `git add --renormalize .`, commit, land it alone. Document
  `git config merge.renormalize true` in the setup, so branches still open rebase across the normalization without
  conflicts.
- **Every tool and script that writes a tracked text file writes LF.** On Windows, Python's `write_text` emits CRLF:
  write bytes or pass `newline="\n"`. PowerShell's `Set-Content`/`Out-File` add CRLF: use
  `[IO.File]::WriteAllText` with `\n` joins. A test fixture written in text mode on Windows is CRLF too.
- **A drift check, run by every gate and by CI, fails on a CR in any tracked text file** (outside the files named CRLF):
  `git ls-files --eol` shows the index and working-tree form of each file, or scan `git grep -lI $'\r'`. See it fail
  once on a planted CR.
- **Until a repository is normalized, edit a CRLF file as BYTES**: read bytes, replace, write bytes, then check that
  the diff touches only the intended lines. Line-oriented text tools can normalize every ending. Measured: a one-line
  `sed` edit to a CRLF log turned its whole top section into LF, a 493-line diff for a 2-line change.
- **`core.autocrlf` lives where the other git can't see it.** Git for Windows sets it in its SYSTEM config, so Linux
  git on the same tree (through WSL) reports every CRLF-checked-out file as modified. Measured: 9,543 "changes" on a
  clean tree. With `eol=lf` in `.gitattributes` the difference disappears; before that, pass `-c core.autocrlf=true`
  inline when reading a Windows checkout from Linux.
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
  and Linux does not. A test that depends on locking or ACLs is proven only on the OS it runs on — and, for deletes,
  only on the FILESYSTEM it runs on (ReFS versus NTFS; see the host-only witnesses in 1).

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

- [ ] The targeted leg ran on both OSes (native, then a clone built on the other OS) and is green, host-only witnesses included; the whole population is left to CI's merge-group run.
- [ ] CI's runner image is pinned and the local environment is the same release; tools that read text declare their encoding; every CI job that can run locally does.
- [ ] No path literal from one OS reaches another OS's path API; tests plant host-native paths.
- [ ] Nothing depends on build-machine paths, or the tests are built on the OS that runs them.
- [ ] `.gitattributes` starts with `* text=auto eol=lf`; every tool wrote LF; the CR drift check is green (a not-yet-normalized CRLF file was edited as bytes, and the diff touches only the intended lines).
- [ ] Per-OS commands are written explicitly, not translated.
- [ ] No git variables are exported to child processes; scratch-repository tests scrub git's local variables.
