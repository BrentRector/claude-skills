# Operating-system facts: the other-OS run, CI's environment, paths, line endings, shells, git across WSL

Each fact here was a real incident in a Windows-hosted, Linux-CI project, and each one is invisible from the side
the developer is on.

## 1. Running a change on the other OS

- **Build and test a clone on the target OS.** Clone the committed HEAD (`git clone --shared` borrows the object
  store read-only) onto the target's own filesystem (for WSL, under `~`, not `/mnt/c`), then build and test it there
  with that OS's toolchain, the way CI does. Don't run binaries built on the other OS: anything that embeds build
  paths breaks (section 3).
- **Export nothing into the original tree.** The run's own reads pass their git settings inline (`git -c …`), never
  through exported variables (section 6).
- **Which tests, and whether this run gates at all, is the gate's decision** (`test-gate`, "The three tiers"): in
  the worked design the other OS runs in the merge group, and a local other-OS run reproduces a CI red. *Why the
  local run is worth keeping as a repro tool: a new test was green in every Windows gate and red in CI's Linux unit
  job, a ~30-minute round trip and a dropped change; the local Linux legs reproduced exactly that one red in about
  2.5 minutes.*
- **Host-only witnesses are a filesystem fact.** ReFS (a Windows Dev Drive) deletes differently from NTFS, and a race
  between an open and a delete-pending file reproduced locally in 20 of 7,200 probes may never reproduce on a CI
  runner. Such tests carry a trait naming the property (`Host=ReFS`) and run locally; `test-gate` says where.

## 2. CI's environment is a build input

- **Pin the runner image and keep the local environment the same release.** A floating label (`ubuntu-latest`)
  moves when the provider decides, so no local run can match it. Pin the image (for example `ubuntu-26.04`) and keep
  the local distro on the same release (a WSL distro can be upgraded in place). The provider's own migration notice
  is the warning: read it.
- **A tool that reads text with the platform's default charset has a hidden input.** A parser generator on the JVM
  read a grammar as UTF-8 locally (Java 18+ defaults to UTF-8) and as Cp1252 on the Windows CI runner, so a set of
  Unicode characters became repeated Latin characters: an error only in CI, invisible to every local gate. Declare
  the encoding in the tool's invocation (`-encoding UTF-8`) and use UTF-8 everywhere, rather than avoiding non-ASCII
  text. Reproduce the CI behaviour locally with the JVM option `-Dfile.encoding=COMPAT`, which makes the JVM use the
  native charset, and keep a drift test that the invocation passes the encoding. Write characters that do not
  display (controls, noncharacters) as Unicode escapes so a reader can see them.
- The survey of every other difference between CI and the local gate (SDK patch, Debug against Release, time zone,
  compile caches, a sparse checkout) is `test-gate`'s (`references/ci-flakes-standards.md`).

## 3. Paths: never assume the host's shape

- **Never feed a path literal from one OS to another OS's path API.** `Path.GetFullPath(@"E:\repo\x")` on Linux is a
  RELATIVE path under the current directory. A test that plants a path must plant the form that is real on the OS
  it runs on, so it proves the code on each OS rather than only on the author's.
- **Build paths are embedded.** `[CallerFilePath]`, source-relative fixture lookups, debug symbols and some
  generators bake the BUILD machine's absolute paths into the binary. Binaries built on Windows and run on Linux
  resolve `E:\…` as relative. Measured: 363 false test failures. Build on the OS that runs the tests.
- **Case and separators.** Linux file names are case-sensitive, and Windows accepts both separators. Compare paths
  with the platform's rules, and join them with the platform's API.
- **Drive letters and backslashes in tests** are the first thing to search for when a test fails only on Linux.

## 4. One line-ending format, LF, enforced

**Standardize on LF in the working tree on every OS, and enforce it.** The measured shape of the problem in one
repository: the object database was already LF for 15,234 of 15,500 text files; only the WORKING TREE differed by OS,
under `core.autocrlf=true`, so a Windows gate and a Linux gate tested different bytes of the same commit, scripts died
on `\r`, a workflow script was refused as containing "control characters", and a single CRLF log needed a
byte-splicing insert tool.

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

## 5. Shells, commands and consoles

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
  and Linux does not. A test that depends on locking or ACLs is proven only on the OS it runs on, and, for deletes,
  only on the FILESYSTEM it runs on (ReFS versus NTFS; section 1).

## 6. Git across the Windows/WSL boundary

- **A Windows worktree is not readable by Linux git as-is.** Its `.git` is a file naming a Windows gitdir
  (`gitdir: E:/repo/.git/worktrees/x`), and a tree under `/mnt` trips git's ownership check (`safe.directory`).
- **Never EXPORT `GIT_DIR` or `GIT_WORK_TREE` into processes that run tests.** A test that creates its own scratch
  repository (`git init`, a commit, `git worktree add` in a temp directory) is silently redirected to the REAL
  repository.
  - Measured: `core.worktree` was written into the shared `.git/config`, and every git command in every checkout
    failed until a person removed it. An agent was (rightly) denied the permission to change shared config.
  - Pass git settings inline for your own reads (`git -c …`, `git -C <dir>`), and run tests in a clone (section 1).
- **Tests that create repositories must be hermetic.** Drop every variable `git rev-parse --local-env-vars` lists
  before running git in a scratch repository.
- **A tripwire.** A gate can snapshot the real repository's `HEAD` and `core.worktree` before running and fail loudly
  if either changed.
