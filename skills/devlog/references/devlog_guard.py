#!/usr/bin/env python3
"""devlog_guard.py — a PreToolUse hook: opening or queueing a pull request whose branch adds no stamped log entry asks
for confirmation.

The rule it backs: ONE ENTRY PER LANDING, as its own file (`devlog.py`). A branch's checkpoint commits carry none; the
pull request that lands the branch carries exactly one, stamped with its number when the branch is enqueued. The hard
enforcement is `devlog.py check --base <ref> --one`, run by the enqueue step and by CI on the pull request and on the
merge group. This hook is the early warning on the agent's side, at the moment the omission happens:

  PreToolUse on the shell tools: the command runs `gh pr create` or `gh pr merge` (anywhere in it, so
  `git push -u origin HEAD && gh pr create …` counts) and the branch, over `<base>...HEAD`, adds no stamped entry file
  under the log directory, or adds one that is still pending → decision "ask", with the reason. It is "ask", not
  "deny": a pull request that deliberately carries no entry (a revert the owner exempts, say) is waved through by a
  person, and CI's check still has the last word.

Where it acts: only in a git work tree whose top level holds `.devlog.json` ({"log": "devlog", "base": "origin/main"},
the same file `devlog.py` reads). Anywhere else it is silent. It follows `cd <dir> &&`. Any internal error, including a
base ref that does not resolve, lets the command through (fail open): a broken guard must never block work.

Register it for PreToolUse with matcher "Bash|PowerShell" and NO `if` filter. An `if` filter such as
`Bash(gh pr create*)` does not match a chained command (`git push … && gh pr create …`), which is how agents usually
run it; measured on a sibling hook, such a filter silenced it in most sessions. The script finds the command anywhere
itself, and exits in milliseconds on every other command. `--self-test` exercises every branch in throwaway
repositories.
"""
import json, os, pathlib, re, subprocess, sys, tempfile

PR = re.compile(r"(^|[;&|(]\s*|\s)gh\s+pr\s+(create|merge)(?![-\w])")
CD = re.compile(r"(?:^|[;&|]\s*)(?:cd|Set-Location|pushd)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")
STAMPED = re.compile(r"^\d{3,}-[a-z0-9][a-z0-9-]*\.md$")
PENDING = re.compile(r"^pending-[a-z0-9][a-z0-9-]*\.md$")


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=20)
    return r.stdout if r.returncode == 0 else None


def unquote(s):
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'" else s


def work_dir(cmd, cwd):
    """The directory the command runs in: payload cwd, then a leading cd."""
    d = pathlib.Path(cwd)
    m = CD.search(cmd)
    if m and m.start() < PR.search(cmd).start():
        d = d / unquote(m.group(1))
    return d


def ask(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                   "permissionDecisionReason": reason}}


def decide(payload):
    if payload.get("hook_event_name", "PreToolUse") != "PreToolUse":
        return None
    cmd = (payload.get("tool_input") or {}).get("command", "") or ""
    if not PR.search(cmd):
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
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    log = cfg.get("log", "devlog").strip("/").replace("\\", "/")
    base = cfg.get("base", "origin/main")
    out = git(top, "diff", "--name-status", "--no-renames", f"{base}...HEAD", "--", log + "/")
    if out is None:
        return None  # the base does not resolve here: fail open, CI's check decides
    added = [ln.split("\t", 1)[1].rsplit("/", 1)[-1] for ln in out.splitlines() if ln.startswith("A\t")]
    if any(STAMPED.match(a) for a in added):
        return None
    if any(PENDING.match(a) for a in added):
        return ask(f"This branch's log entry under {log}/ is still pending (no number). The enqueue step stamps it "
                   f"after the final rebase: `python devlog.py stamp --base {base}`, commit, then open or queue the pull "
                   f"request. Confirm only a deliberate exception.")
    return ask(f"This branch adds no log entry under {log}/ over {base}. Project rule: one entry per landing, as its own "
               f"file. Write it with `python devlog.py new --title \"...\" --body-file entry.md`, stamp it at enqueue "
               f"(`devlog.py stamp --base {base}`), commit, and run this again, or confirm a deliberate exception.")


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

    def write(p, s):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(s.encode("utf-8"))

    def repo(d, cfg):
        run = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, check=True)
        run("init", "-q", "-b", "main"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        run("config", "core.autocrlf", "false")
        write(d / ".devlog.json", json.dumps(cfg))
        write(d / "devlog" / "0001-start.md", "## Entry 1 — 2026-03-01 09:00 PST — Start\n")
        run("add", "-A"); run("commit", "-qm", "init")
        run("checkout", "-qb", "fix")
        return run

    q = lambda d, c, tool="Bash": decide({"hook_event_name": "PreToolUse", "cwd": str(d), "tool_name": tool,
                                          "tool_input": {"command": c}})
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        plain = t / "plain"; plain.mkdir()
        check("not a git repo: silent", q(plain, "gh pr create --fill"), "none")
        other = t / "other"; other.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        check("repo without .devlog.json: silent", q(other, "gh pr create --fill"), "none")

        r = t / "r"; r.mkdir()
        run = repo(r, {"log": "devlog", "base": "main"})
        check("non-PR command: silent", q(r, "git status"), "none")
        check("a plain commit is not a landing: silent", q(r, "git commit -m checkpoint"), "none")
        check("gh pr view is not a landing: silent", q(r, "gh pr view 12"), "none")
        write(r / "code.txt", "fix"); run("add", "-A"); run("commit", "-qm", "checkpoint")
        check("no entry, gh pr create: ask", q(r, "gh pr create --fill"), "ask")
        check("no entry, gh pr merge (queue): ask", q(r, "gh pr merge 12 --auto"), "ask")
        check("PowerShell tool: ask", q(r, "gh pr create --fill", "PowerShell"), "ask")
        check("chained push && gh pr create: ask", q(r, "git push -u origin HEAD && gh pr create --fill"), "ask")
        check("cd && gh pr create: ask", q(t, f"cd {r.name} && gh pr create --fill"), "ask")
        write(r / "devlog" / "pending-the-fix.md", "## Entry pending — The fix\n\nwhy\n")
        check("entry written but not committed: ask", q(r, "gh pr create --fill"), "ask")
        run("add", "-A"); run("commit", "-qm", "entry")
        got = q(r, "gh pr create --fill")
        check("entry committed but still pending: ask", got, "ask")
        good = got is not None and "stamp" in got["hookSpecificOutput"]["permissionDecisionReason"]
        ok &= good
        print(("ok      " if good else "FAIL    ") + "pending: the reason names the stamp step")
        (r / "devlog" / "pending-the-fix.md").unlink()
        write(r / "devlog" / "0002-the-fix.md", "## Entry 2 — 2026-03-02 09:00 PST — The fix\n\nwhy\n")
        run("add", "-A"); run("commit", "-qm", "stamp")
        check("stamped entry on the branch: silent", q(r, "gh pr create --fill"), "none")
        check("stamped entry, gh pr merge: silent", q(r, "gh pr merge --auto"), "none")

        b = t / "b"; b.mkdir()
        repo(b, {"log": "devlog", "base": "origin/does-not-exist"})
        check("base does not resolve: silent (fail open; CI decides)", q(b, "gh pr create --fill"), "none")

        write(r / ".devlog.json", "{not json")
        payload = json.dumps({"hook_event_name": "PreToolUse", "cwd": str(r),
                              "tool_input": {"command": "gh pr create --fill"}})
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
