#!/usr/bin/env python3
"""PreToolUse hook for READ-ONLY agent roles (refuters, auditors, analysts, probes).

Register it in the role's OWN definition (.claude/agents/<role>.md frontmatter `hooks:`), not in the project settings.
A frontmatter hook runs for that agent and only that agent, however it was dispatched (Agent tool `subagent_type`,
a workflow's `agentType`). A project-wide hook would have to work out the role from the hook input, and when that
field is missing it cannot tell a read-only role from the main session.

Blocks:
  Write / Edit / MultiEdit / NotebookEdit whose target is inside ANY git working tree (the project, a linked
  worktree, another checkout).
  Bash / PowerShell git subcommands that change a repository (add, commit, push, reset, checkout, stash, ...).
  Bash / PowerShell writes to a file inside a git working tree: `> f`, `>> f`, `tee f`, `Out-File`, `Set-Content`,
  `Add-Content` (a path-like target: it has a directory separator or an extension; heredoc bodies and single-quoted
  text are not scanned, so `awk '$1 > 5'` and `print(1 > 0)` pass).
  Git Bash spellings of Windows paths (`/e/repo/x.py`, `/cygdrive/e/...`) are resolved, not waved through.
Passes:
  writes outside every git tree, which is where the role's checkpoint and report files go (a scratch directory);
  read-only git (status, log, diff, show, grep, rev-parse, worktree list, ...).
Fails open: unparseable input, a missing path or a git failure all pass. The hook is a guardrail on a cooperative
agent, not a sandbox: a write from inside a script, `rm`, or a variable target (`> $f`) is not seen, so the role's
instructions still say "report changes, never make them".

Usage:
  python readonly_guard.py              hook mode (PreToolUse JSON on stdin)
  python readonly_guard.py --selftest   prove repo writes are blocked and scratch writes pass
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

GIT_TIMEOUT_S = 10  # a slower git answer is treated as "not a git tree" (fail open)
FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
MUTATING_GIT = re.compile(
    r"\bgit\s+(?:-[Cc]\s+\S+\s+)*(add|commit|push|reset|restore|rm|mv|clean|merge|rebase|cherry-pick|revert|am|apply|"
    r"stash|tag|switch|checkout|pull|fetch|worktree\s+(?:add|remove|move|prune)|branch\s+-[dDmMfc]|update-ref|"
    r"update-index|notes\s+add|submodule\s+update|gc|prune)\b")
SHELL_WRITE = re.compile(
    r"(?:(?<![0-9&<>=|-])>>?|\b(?:Out-File|Set-Content|Add-Content)\b(?:\s+-(?:FilePath|Path|LiteralPath)\b)?"
    r"|\btee\b(?:\s+-a\b)?)\s*(\"[^\"]+\"|[^\s;&|<>()\"'`]+)", re.IGNORECASE)
PATH_LIKE = re.compile(r"[/\\]|\.[A-Za-z0-9]{1,8}$")
NULL_SINKS = {"/dev/null", "nul", "$null", "/dev/stderr", "/dev/stdout"}
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?")


def utf8_stdio():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def native_path(p):
    """Git Bash spells E:\\repo as /e/repo (or /cygdrive/e/repo). Windows Python cannot resolve that spelling, and an
    unresolved path would pass (fail open), so translate it first."""
    if sys.platform == "win32":
        m = re.match(r"^(?:/cygdrive)?/([a-zA-Z])(/.*)?$", p)
        if m:
            return m.group(1).upper() + ":" + (m.group(2) or "/")
    return p


def shell_write_targets(cmd):
    """Path-like file targets the command writes through the shell; heredoc bodies and '...' text are not scanned."""
    kept, terminators = [], []
    for line in cmd.splitlines():
        if terminators:
            if line.strip() == terminators[0]:
                terminators.pop(0)
            continue
        kept.append(line)
        terminators += HEREDOC.findall(line)
    text = re.sub(r"'[^'\n]*'", "''", "\n".join(kept))
    for m in SHELL_WRITE.finditer(text):
        t = m.group(1).strip('"')
        if t and t.lower() not in NULL_SINKS and "$" not in t and PATH_LIKE.search(t):
            yield t


def git_toplevel(target, cwd):
    d = pathlib.Path(native_path(target))
    if not d.is_absolute():
        d = pathlib.Path(cwd or os.getcwd()) / d
    d = d.parent
    while not d.exists() and d != d.parent:  # a new file in a not-yet-created directory
        d = d.parent
    try:
        r = subprocess.run(["git", "-C", str(d), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def decide(event):
    """Return a block message, or None to allow."""
    tool = event.get("tool_name") or ""
    tin = event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        target = tin.get("file_path") or tin.get("notebook_path")
        if not target:
            return None
        top = git_toplevel(target, event.get("cwd"))
        if top:
            return (f"BLOCKED: this agent role is READ-ONLY and {target} is inside the git working tree {top}.\n"
                    "Instead: write only your checkpoint and report files, in the scratch directory your brief names, "
                    "and put proposed changes in your report for the orchestrator to apply.\n")
        return None
    cmd = tin.get("command")
    if isinstance(cmd, str):
        m = MUTATING_GIT.search(cmd)
        if m:
            return (f"BLOCKED: this agent role is READ-ONLY and `git {m.group(1)}` changes a repository.\n"
                    "Instead: use read-only git (status, log, diff, show, grep) and put proposed changes in your "
                    "report.\n")
        for target in shell_write_targets(cmd):
            top = git_toplevel(target, event.get("cwd"))
            if top:
                return (f"BLOCKED: this agent role is READ-ONLY and this command writes {target}, inside the git "
                        f"working tree {top}.\n"
                        "Instead: send output to the scratch directory your brief names, and put proposed changes in "
                        "your report.\n")
    return None


def hook():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        message = decide(json.loads(raw))
    except Exception as exc:  # noqa: BLE001 - FAIL OPEN, and say so
        sys.stderr.write(f"readonly_guard.py: internal error ({type(exc).__name__}: {exc}); the call was ALLOWED.\n")
        return 0
    if message:
        sys.stderr.write(message)
        return 2
    return 0


def selftest():
    failures, checks = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        repo = tmp / "repo"
        (repo / "src").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        scratch = tmp / "scratch"
        scratch.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        cases = [
            # (label, payload, expect_block)
            ("Write into the repo", {"tool_name": "Write", "tool_input": {"file_path": str(repo / "src" / "a.py")}}, True),
            ("Write into a not-yet-created repo dir",
             {"tool_name": "Write", "tool_input": {"file_path": str(repo / "new" / "deeper" / "b.md")}}, True),
            ("Edit by relative path, cwd = repo",
             {"tool_name": "Edit", "cwd": str(repo), "tool_input": {"file_path": "src/a.py"}}, True),
            ("MultiEdit into the repo", {"tool_name": "MultiEdit", "tool_input": {"file_path": str(repo / "x.txt")}}, True),
            ("NotebookEdit into the repo",
             {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(repo / "n.ipynb")}}, True),
            ("Write a scratch checkpoint",
             {"tool_name": "Write", "tool_input": {"file_path": str(scratch / "out" / "refute-a.jsonl")}}, False),
            ("Write a scratch report", {"tool_name": "Write", "tool_input": {"file_path": str(scratch / "report.md")}}, False),
            ("git commit", {"tool_name": "Bash", "tool_input": {"command": "git commit -am x"}}, True),
            ("git -C repo push", {"tool_name": "PowerShell", "tool_input": {"command": f"git -C {repo} push"}}, True),
            ("git stash", {"tool_name": "Bash", "tool_input": {"command": "cd repo && git stash"}}, True),
            ("git checkout -- file", {"tool_name": "Bash", "tool_input": {"command": "git checkout -- src/a.py"}}, True),
            ("git status", {"tool_name": "Bash", "tool_input": {"command": "git status --short"}}, False),
            ("git log/diff/show", {"tool_name": "Bash", "tool_input": {"command": "git log -3 && git diff HEAD~1 && git show HEAD"}}, False),
            ("git worktree list", {"tool_name": "Bash", "tool_input": {"command": "git worktree list"}}, False),
            ("running a probe", {"tool_name": "Bash", "tool_input": {"command": "python tools/probe.py case1"}}, False),
            ("Read tool", {"tool_name": "Read", "tool_input": {"file_path": str(repo / "src" / "a.py")}}, False),
            ("redirect into the repo",
             {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": "python probe.py > src/out.txt"}}, True),
            ("append by absolute path",
             {"tool_name": "Bash", "tool_input": {"command": f"echo x >> {repo.as_posix()}/log.md"}}, True),
            ("tee into the repo",
             {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": "ls | tee -a notes.txt"}}, True),
            ("Out-File into the repo", {"tool_name": "PowerShell", "cwd": str(repo),
                                        "tool_input": {"command": 'Get-Date | Out-File -FilePath "src/d.txt"'}}, True),
            ("Set-Content into the repo",
             {"tool_name": "PowerShell", "tool_input": {"command": f"Set-Content {repo / 'x.cfg'} 1"}}, True),
            ("redirect to scratch", {"tool_name": "Bash", "cwd": str(repo), "tool_input": {
                "command": f"python probe.py > {scratch.as_posix()}/probe.txt 2>&1"}}, False),
            ("redirect to /dev/null and $null", {"tool_name": "Bash", "cwd": str(repo), "tool_input": {
                "command": "git status > /dev/null; Get-Item . > $null"}}, False),
            ("comparisons, not writes", {"tool_name": "Bash", "cwd": str(repo), "tool_input": {
                "command": "awk '$1 > 5 {print > \"o.txt\"}' in.txt; python -c \"print(1 > 0)\"; "
                           "node -e \"[1].map(x => x.y)\""}}, False),
            ("heredoc body is not scanned", {"tool_name": "Bash", "cwd": str(repo), "tool_input": {
                "command": "python - <<'EOF'" + chr(10) + "print(2 > 1)  # > out.txt" + chr(10) + "EOF"}}, False),
        ]
        if sys.platform == "win32":  # Git Bash spelling of the same repo path must not slip through
            posix = "/" + repo.as_posix()[0].lower() + repo.as_posix()[2:]
            cases.append(("Write by Git Bash path /e/...",
                          {"tool_name": "Write", "tool_input": {"file_path": posix + "/src/g.py"}}, True))
            cases.append(("redirect by Git Bash path",
                          {"tool_name": "Bash", "tool_input": {"command": f"echo x > {posix}/g.txt"}}, True))
        for label, payload, want in cases:
            checks += 1
            r = subprocess.run([sys.executable, __file__], input=json.dumps(payload).encode("utf-8"),
                               capture_output=True, env=env, timeout=60)
            if (r.returncode == 2) != want:
                failures.append(f"expected {'BLOCK' if want else 'PASS'}: {label} (rc {r.returncode})")
        for label, raw in (("malformed JSON", "{nope"), ("empty stdin", ""),
                           ("Write without a path", json.dumps({"tool_name": "Write", "tool_input": {}}))):
            checks += 1
            r = subprocess.run([sys.executable, __file__], input=raw.encode("utf-8"), capture_output=True, env=env,
                               timeout=60)
            if r.returncode != 0:
                failures.append(f"{label} must PASS (fail open), got rc {r.returncode}")
    for f in failures:
        print("FAIL:", f)
    print(f"readonly_guard self-test: {checks - len(failures)}/{checks} " + ("GREEN" if not failures else "RED"))
    return 1 if failures else 0


if __name__ == "__main__":
    utf8_stdio()
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else hook())
