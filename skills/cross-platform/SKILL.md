---
name: cross-platform
description: Keeps code, tests, scripts and agents behaving the same on Windows and Linux. Use when a test or bug shows up on one OS, host or filesystem and not another (a failure only the developer's machine reproduces, or one only CI sees), when CI runs an operating system the local gates do not, when a Windows-hosted agent edits files or writes a command for another shell, or when git, line endings, paths or encodings differ across the Windows/WSL boundary. Not for platform-specific product features.
---

# Cross-platform: Windows and Linux without surprises

**The result is code, tests and tooling that behave the same on Windows and Linux, with each change's other-OS
behaviour checked before anyone depends on it.** It is verified on the other OS itself: a clone built and tested
there (locally or in the merge group, wherever the project's gate puts it), a line-ending drift check seen to fail
once on a planted CR, and scratch-repository tests that cannot reach the real repository.

A test that passes on one operating system proves nothing about the other. Paths, line endings, shells, console
encodings, file locking and git configuration all differ, and each difference is invisible from the side the
developer is on. The aim is code that never has to guess which side it is on, and an other-OS check cheap enough
to run for every change.

**Where the other OS runs is the gate's decision, not this skill's.** `test-gate` holds the gate rule and its worked
design (the developer's OS locally, the other OS in the merge group) and says when a local other-OS leg of the
change's own tests is still right: no merge group, or the change's own tests often going red only there. This skill holds the facts that make any other-OS run trustworthy. Read `references/platform-facts.md`
before running a change on the other OS, touching CI's runner image or a tool's encoding, writing a tracked text
file from a tool, composing a shell command for another OS, or running git or tests across the Windows/WSL
boundary.

## The judgment calls

- **The other-OS run is a clone built on that OS.** Clone the committed HEAD onto the target's own filesystem and
  build it there. Running the first OS's binaries, or the Windows working tree through `/mnt/c`, tests something CI
  never runs: build paths are embedded in binaries, and the working tree's line endings and git metadata differ.
- **A difference CI sees and the local gate cannot is a build input to pin or declare**, never luck: the runner
  image, a tool's default charset, the shell. Pin it, declare it in the invocation, or reproduce it locally.
- **LF everywhere, enforced by the repository, not by each developer's setting.** `* text=auto eol=lf` in
  `.gitattributes`, one renormalization landing, every tool writing LF, and a drift check in every gate and CI.
  `core.autocrlf` lives in Git for Windows' system config, which Linux git never reads, so a per-developer setting
  cannot make the two sides agree.
- **Git state stays inside the process that owns it.** Never export `GIT_DIR` or `GIT_WORK_TREE` into a process that
  runs tests: a test's scratch `git init` or `git worktree add` is then redirected into the real repository. Pass
  settings inline (`git -c`, `git -C`), and make repository-creating tests drop every variable
  `git rev-parse --local-env-vars` lists.
- **A path literal belongs to one OS.** `E:\repo\x` is a relative path on Linux; tests plant the host's native form.
- **A command string belongs to one shell.** Write per-OS commands explicitly; a translation covers only the tokens
  its author thought of.

## Checklist before pushing a change that touches paths, processes, files, shells or git

- [ ] The change ran on the other OS as the project's gate decides (a clone built there, never the first OS's binaries), host-only witnesses included.
- [ ] CI's runner image is pinned and the local environment is the same release; tools that read text declare their encoding.
- [ ] No path literal from one OS reaches another OS's path API; tests plant host-native paths.
- [ ] Nothing depends on build-machine paths, or the tests are built on the OS that runs them.
- [ ] `.gitattributes` starts with `* text=auto eol=lf`; every tool wrote LF; the CR drift check is green (a not-yet-normalized CRLF file was edited as bytes, and the diff touches only the intended lines).
- [ ] Per-OS commands are written explicitly, not translated.
- [ ] No git variables are exported to child processes; scratch-repository tests scrub git's local variables.
