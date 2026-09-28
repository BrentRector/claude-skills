#!/usr/bin/env python3
"""devlog_guard.py — a PreToolUse hook: a commit that carries no devlog entry asks for confirmation.

The rule it backs: every commit carries its devlog entry, in the same commit. Written as an instruction alone, the
rule was broken in real sessions, and each miss lost the in-the-moment reasoning the log exists to keep. This hook
makes the omission visible at the moment it happens.

  PreToolUse on the shell tools: the command runs `git commit` (anywhere in it, so `git add -A && git commit …`
  counts) and the commit will not carry a devlog change → decision "ask", with the reason. It is "ask", not "deny":
  an amend of a message, or a commit the owner deliberately exempts, is waved through by a person, not refused.

"Carries a devlog change" means one of:
  * the log path (a file, or any file under a log directory) is staged;
  * the command stages before it commits (`git add`, `git commit -a/--all`) and the log has an uncommitted change,
    tracked or new, for the command to pick up;
  * the command is `git commit --amend` and HEAD already touches the log.

Where it acts: only in a git work tree whose top level holds `.devlog.json` ({"log": "DEVLOG.md"} or a directory,
the same file `devlog.py` reads). Anywhere else it is silent. It follows `cd <dir> &&` and `git -C <dir>`. Any
internal error lets the command through (fail open): a broken guard must never block work.

Register it for PreToolUse with matcher "Bash|PowerShell" and NO `if` filter. An `if: Bash(git commit*)` filter does
not match `git add -A && git commit …`, which is how agents usually commit; measured on a sibling hook, the filter
silenced it in most sessions. The script finds `git commit` anywhere in the command itself, and exits in
milliseconds on every other command. `--self-test` exercises every branch in throwaway repositories.
"""
import json, os, pathlib, re, shlex, subprocess, sys, tempfile

COMMIT = re.compile(r"(^|[;&|(]\s*|\s)git(\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+))?\s+commit(?![-\w])")
ADD = re.compile(r"(^|[;&|(]\s*|\s)git(\s+-C\s+\S+)?\s+add(?![-\w])")
ALL_FLAG = re.compile(r"\bcommit\b[^;&|]*\s(-[a-zA-Z]*a[a-zA-Z]*|--all)\b")
AMEND = re.compile(r"\bcommit\b[^;&|]*\s--amend\b")
CD = re.compile(r"(?:^|[;&|]\s*)(?:cd|Set-Location|pushd)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=20)
    return r.stdout if r.returncode == 0 else None


def unquote(s):
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'" else s


def work_dir(cmd, cwd):
    """The directory the commit runs in: payload cwd, then a leading cd, then git -C."""
    d = pathlib.Path(cwd)
    m = CD.search(cmd)
    if m and m.start() < COMMIT.search(cmd).start():
        d = d / unquote(m.group(1))
    c = COMMIT.search(cmd)
    if c.group(3):
        d = d / unquote(c.group(3))
    return d


def decide(payload):
    if payload.get("hook_event_name", "PreToolUse") != "PreToolUse":
        return None
    cmd = (payload.get("tool_input") or {}).get("command", "") or ""
    if not COMMIT.search(cmd):
        return None
    d = work_dir(cmd, payload.get("cwd") or os.getcwd())
    if not d.is_dir():
        return None
    top = git(d, "rev-parse", "--show-toplevel")
    if not top:
        return None
    top = pathlib.Path(top.strip())
    cfg_path = top / ".devlog.json"
    if not cfg_path.is_file():
        return None
    log = json.loads(cfg_path.read_text(encoding="utf-8")).get("log", "DEVLOG.md").strip("/").replace("\\", "/")

    def touches(paths):
        return any(p == log or p.startswith(log + "/") for p in paths)

    staged = (git(top, "diff", "--cached", "--name-only") or "").split("\n")
    if touches(staged):
        return None
    if ADD.search(cmd) or ALL_FLAG.search(cmd):
        pending = [line[3:].strip().strip('"') for line in
                   (git(top, "status", "--porcelain", "--untracked-files=all", "--", log) or "").splitlines()]
        if touches(pending):
            return None
    if AMEND.search(cmd):
        head = (git(top, "show", "--name-only", "--format=", "HEAD") or "").split("\n")
        if touches(head):
            return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": (
            f"This commit carries no change to {log}. Project rule: every commit carries its devlog entry, in the "
            f"same commit. Add it (for example `python devlog.py new --title \"...\" --body-file entry.md`, which "
            f"stamps the time from the clock), stage it, and commit again, or confirm this is a deliberate exception.")}}


def main():
    if "--self-test" in sys.argv:
        return self_test()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        out = decide(payload)
    except Exception as e:  # fail open
        sys.stderr.write(f"devlog_guard: internal error, allowing: {e}\n")
        return 0
    if out is not None:
        sys.stdout.write(json.dumps(out))
    return 0


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        kind = "none" if got is None else got["hookSpecificOutput"]["permissionDecision"]
        good = kind == want
        ok &= good
        print(("ok      " if good else "FAIL    ") + f"{name}: {kind} (want {want})")

    def repo(d, log):
        run = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, check=True)
        run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        run("config", "core.autocrlf", "false")
        (d / ".devlog.json").write_text(json.dumps({"log": log}), encoding="utf-8")
        (d / "a.txt").write_text("1")
        run("add", "-A"); run("commit", "-qm", "init")
        return run

    ask = lambda d, c, tool="Bash": decide({"hook_event_name": "PreToolUse", "cwd": str(d), "tool_name": tool,
                                            "tool_input": {"command": c}})
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        plain = t / "plain"; plain.mkdir()
        check("not a git repo: silent", ask(plain, "git commit -m x"), "none")
        other = t / "other"; other.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        check("repo without .devlog.json: silent", ask(other, "git commit -m x"), "none")

        r = t / "r"; r.mkdir()
        run = repo(r, "DEVLOG.md")
        (r / "DEVLOG.md").write_text("# Log\n", encoding="utf-8"); run("add", "DEVLOG.md"); run("commit", "-qm", "log")
        check("non-commit command: silent", ask(r, "git status"), "none")
        check("git commit-tree is not a commit: silent", ask(r, "git commit-tree abc"), "none")
        (r / "a.txt").write_text("2"); run("add", "a.txt")
        check("code staged, no devlog: ask", ask(r, "git commit -m fix"), "ask")
        check("PowerShell tool: ask", ask(r, "git commit -m fix", "PowerShell"), "ask")
        check("git -C form: ask", ask(t, f"git -C {r.name} commit -m fix"), "ask")
        check("cd && commit form: ask", ask(t, f"cd {r.name} && git commit -m fix"), "ask")
        (r / "DEVLOG.md").write_text("# Log\n## Entry 1\n", encoding="utf-8")
        check("devlog modified but not staged, plain commit: ask", ask(r, "git commit -m fix"), "ask")
        check("chained add + commit picks the devlog up: silent", ask(r, "git add -A && git commit -m fix"), "none")
        check("commit -am picks the devlog up: silent", ask(r, "git commit -am fix"), "none")
        run("add", "DEVLOG.md")
        check("devlog staged: silent", ask(r, "git commit -m fix"), "none")
        run("commit", "-qm", "with log")
        check("amend when HEAD has the devlog: silent", ask(r, "git commit --amend --no-edit"), "none")
        (r / "a.txt").write_text("3"); run("commit", "-qam", "no log")
        check("amend when HEAD lacks the devlog: ask", ask(r, "git commit --amend --no-edit"), "ask")
        check("chained add + commit with no devlog change: ask", ask(r, "git add -A && git commit -m y"), "ask")

        dd = t / "dd"; dd.mkdir()
        run2 = repo(dd, "docs/devlog")
        (dd / "docs" / "devlog").mkdir(parents=True)
        (dd / "docs" / "devlog" / "0001-2026-03-01-a.md").write_text("# 0001\n", encoding="utf-8")
        (dd / "b.txt").write_text("x"); run2("add", "b.txt")
        check("dir layout: new untracked entry + git add -A: silent", ask(dd, "git add -A; git commit -m z"), "none")
        check("dir layout: new entry not added by the command: ask", ask(dd, "git commit -m z"), "ask")
        run2("add", "docs")
        check("dir layout: entry staged: silent", ask(dd, "git commit -m z"), "none")

        (r / ".devlog.json").write_text("{not json", encoding="utf-8")
        payload = json.dumps({"hook_event_name": "PreToolUse", "cwd": str(r),
                              "tool_input": {"command": "git commit -m x"}})
        proc = subprocess.run([sys.executable, __file__], input=payload, capture_output=True, text=True)
        good = proc.returncode == 0 and proc.stdout == "" and "allowing" in proc.stderr
        ok &= good
        print(("ok      " if good else "FAIL    ") + "corrupt .devlog.json: exit 0, no decision, stderr note (fail open)")
    proc = subprocess.run([sys.executable, __file__], input="not json", capture_output=True, text=True)
    good = proc.returncode == 0 and proc.stdout == ""
    ok &= good
    print(("ok      " if good else "FAIL    ") + "malformed hook input: exit 0, no output (fail open)")
    check("other hook event: silent", decide({"hook_event_name": "Stop"}), "none")
    print("=== SELF-TEST: " + ("GREEN" if ok else "RED") + " ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
