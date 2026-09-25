#!/usr/bin/env python3
"""PreToolUse guard: block the shell commands a project forbids, with a reason that names the right alternative.

Register it in .claude/settings.json for EVERY shell tool (matcher "Bash|PowerShell"). A PreToolUse hook also fires
inside subagents and workflow agents, which is why a hook holds where a sentence in CLAUDE.md or a brief does not.

Rules live in guard-rules.json beside this file (or --rules PATH). Each rule is an object:

  id        short name, shown in the block message
  pattern   Python regex, searched in the command text
  target    "command" (default): the command text with heredoc bodies removed
            "heredoc": the heredoc bodies only
  scope     "any" (default)
            "repo": fires only when the command runs in THIS project's repository, meaning the same git common dir
            as $CLAUDE_PROJECT_DIR (its linked worktrees count). The working directory is the hook's `cwd`,
            followed through `cd` / `pushd` / `Set-Location` / `Push-Location` and `git -C <dir>`. Another
            repository has its own rules and is left alone.
  reason    why the command is forbidden
  instead   what to do instead. Required: a block that does not name the alternative invites a workaround.
  block     commands that MUST be blocked     } --selftest proves both lists. A rule without at least one
  allow     legitimate neighbours that MUST pass } entry in each list fails the self-test.

Contract:
  exit 2, message on stderr   blocked. Claude Code feeds stderr back to the agent.
  exit 0                      allowed. ALSO exit 0 on ANY internal error (bad JSON, a missing or broken rules file,
                              a git failure). The guard FAILS OPEN: a guard that fails closed turns one malformed
                              input, a missing interpreter or a harness format change into a wedge of every shell
                              call in every session and subagent. These rules are workflow conventions with real
                              backstops (branch protection, CI); a security boundary belongs in permissions, a
                              sandbox or the server, not in a regex.
  stderr is UTF-8 whatever the console code page is (Windows would otherwise mangle every non-ASCII character).

Usage:
  python guard_commands.py                          hook mode: reads the PreToolUse JSON on stdin
  python guard_commands.py --selftest               prove every rule fires on its block list, passes its allow
                                                    list, stays inside this repo, and that the contract holds
  python guard_commands.py --selftest --settings .claude/settings.json
                                                    ...and that every shell tool is routed through this guard
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_RULES = HERE / "guard-rules.json"
SHELL_TOOLS = ("Bash", "PowerShell")
# A git query slower than this is treated as "unknown", and an unknown working tree lets the call pass (fail open).
GIT_TIMEOUT_S = 10

# `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`, but not the here-string `<<<`.
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# Directory changes in bash and PowerShell. The target is a quoted string or a bare word.
CD = re.compile(r"(?<![\w.$-])(?:cd|pushd|Set-Location|Push-Location)[ \t]+(?:-(?:Path|LiteralPath)[ \t]+)?"
                r"(\"[^\"]*\"|'[^']*'|[^\s;&|)]+)", re.IGNORECASE)
GIT_C = re.compile(r"\bgit[ \t]+-C[ \t]+(\"[^\"]*\"|'[^']*'|[^\s;&|)]+)")
# Separators between commands in one tool call (bash and PowerShell).
SEPARATOR = re.compile(r"&&|\|\||[;|\n]")


def utf8_stdio():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - a stream that cannot be reconfigured is left as it is
            pass


def load_rules(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["rules"]


def split_heredocs(cmd):
    """Return (command text without heredoc bodies, the heredoc bodies)."""
    commands, bodies, pos = [], [], 0
    while True:
        m = HEREDOC.search(cmd, pos)
        newline = cmd.find("\n", m.end()) if m else -1
        if not m or newline < 0:
            commands.append(cmd[pos:])
            break
        commands.append(cmd[pos:newline + 1])  # the line holding the operator is command text
        end = re.compile(r"^[ \t]*" + re.escape(m.group(2)) + r"[ \t]*$", re.MULTILINE).search(cmd, newline + 1)
        if not end:
            bodies.append(cmd[newline + 1:])
            break
        bodies.append(cmd[newline + 1:end.start()])
        pos = end.end()
    return "".join(commands), "\n".join(bodies)


def resolve(base, raw):
    """Resolve a cd / -C target against `base`. None means unknown (a variable, `cd -`, a missing directory)."""
    p = raw.strip("\"'")
    if not p or p == "-" or any(ch in p for ch in "$`%"):
        return None
    p = os.path.expanduser(p)
    if sys.platform == "win32":
        drive = re.match(r"^/([a-zA-Z])(/.*)?$", p)  # Git Bash spelling: /e/repo -> E:/repo
        if drive:
            p = drive.group(1) + ":" + (drive.group(2) or "/")
    path = pathlib.Path(p)
    if not path.is_absolute():
        if base is None:
            return None
        path = base / path
    return path if path.is_dir() else None


def git_common_dir(path, cache):
    if path is None:
        return None
    key = str(path)
    if key not in cache:
        try:
            r = subprocess.run(["git", "-C", key, "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                               timeout=GIT_TIMEOUT_S)
            out = r.stdout.strip()
            if r.returncode or not out:
                cache[key] = None
            else:
                common = pathlib.Path(out)
                if not common.is_absolute():
                    common = pathlib.Path(key) / common
                cache[key] = os.path.normcase(os.path.realpath(common))
        except Exception:  # noqa: BLE001 - unknown means "not this repo": fail open
            cache[key] = None
    return cache[key]


def project_dir():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return pathlib.Path(env)
    try:
        r = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
        return pathlib.Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:  # noqa: BLE001
        return None


def workdir_at(commands, start, end, cwd):
    """The directory the command segment holding commands[start:end] runs in: the hook's cwd, then every cd before
    it, then a `git -C <dir>` in the same segment (anywhere before the match end, not only inside the match)."""
    wd = pathlib.Path(cwd) if cwd else None
    for m in CD.finditer(commands, 0, start):
        wd = resolve(wd, m.group(1))
    segment = 0
    for m in SEPARATOR.finditer(commands, 0, start):
        segment = m.end()
    dash_c = None
    for dash_c in GIT_C.finditer(commands, segment, end):
        pass
    if dash_c:
        wd = resolve(wd, dash_c.group(1))
    return wd


def evaluate(rules, cmd, cwd, project):
    """Return the first rule the command breaks, or None."""
    commands, bodies = split_heredocs(cmd)
    cache = {}
    project_common = None
    for rule in rules:
        try:
            pattern = re.compile(rule["pattern"])
        except (KeyError, re.error, TypeError):
            continue  # one broken rule never disables the others; --selftest reports it
        text = bodies if rule.get("target") == "heredoc" else commands
        for m in pattern.finditer(text):
            if rule.get("scope", "any") == "repo":
                if project_common is None:
                    project_common = git_common_dir(project, cache) or ""
                here = git_common_dir(workdir_at(commands, m.start(), m.end(), cwd), cache)
                if not project_common or here != project_common:
                    continue
            return rule
    return None


def block_message(rule):
    return (f"BLOCKED by the project guard hook [{rule.get('id', '?')}]: {rule.get('reason', '')}\n"
            f"Instead: {rule.get('instead', '')}\n"
            "This block is the project's rule speaking. Comply with the Instead line; never rephrase, split, encode "
            "or relocate the command to get past the guard. If the rule looks wrong for this case, stop and ask "
            "the owner.\n")


def hook(rules_path):
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
        cmd = (event.get("tool_input") or {}).get("command")
        if not isinstance(cmd, str) or not cmd.strip():
            return 0
        rule = evaluate(load_rules(rules_path), cmd, event.get("cwd") or os.getcwd(), project_dir())
    except Exception as exc:  # noqa: BLE001 - FAIL OPEN, and say so
        sys.stderr.write(f"guard_commands.py: internal error ({type(exc).__name__}: {exc}); the call was ALLOWED "
                         f"(the guard fails open). Run `python {pathlib.Path(__file__).as_posix()} --selftest`.\n")
        return 0
    if rule is None:
        return 0
    sys.stderr.write(block_message(rule))
    return 2


# ---------------------------------------------------------------------------------------------------- self-test

def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=60)


def _make_repo(path):
    path.mkdir(parents=True)
    _git("init", "-q", str(path))
    _git("-c", "user.email=guard@selftest", "-c", "user.name=guard", "commit", "-q", "--allow-empty", "-m", "init",
         cwd=path)
    return path


def _bash_path(p):
    s = pathlib.Path(p).as_posix()
    return ("/" + s[0].lower() + s[2:]) if sys.platform == "win32" and re.match(r"^[A-Za-z]:/", s) else s


def selftest(rules_path, settings_path=None):
    failures, checks = [], 0

    def expect(label, cond):
        nonlocal checks
        checks += 1
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        project = _make_repo(tmp / "project")
        other = _make_repo(tmp / "other")
        worktree = tmp / "project-wt"
        _git("worktree", "add", "-q", "--detach", str(worktree), cwd=project)
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        env["CLAUDE_PROJECT_DIR"] = str(project)

        def run(cmd, cwd, tool="Bash", rules=rules_path, raw=None):
            payload = raw if raw is not None else json.dumps(
                {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(cwd), "tool_input": {"command": cmd}})
            r = subprocess.run([sys.executable, __file__, "--rules", str(rules)], input=payload.encode("utf-8"),
                               capture_output=True, env=env, timeout=60)
            return r.returncode, r.stderr

        try:
            rules = load_rules(rules_path)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: cannot load {rules_path}: {exc}")
            return 1

        for rule in rules:
            rid = rule.get("id", "?")
            print(f"rule [{rid}] scope={rule.get('scope', 'any')} target={rule.get('target', 'command')}: "
                  f"{len(rule.get('block') or [])} block / {len(rule.get('allow') or [])} allow examples")
            for field in ("id", "pattern", "reason", "instead"):
                expect(f"[{rid}] has no `{field}`", bool(rule.get(field)))
            expect(f"[{rid}] has no `block` examples (prove it fires)", bool(rule.get("block")))
            expect(f"[{rid}] has no `allow` examples (prove it passes its legitimate neighbour)", bool(rule.get("allow")))
            try:
                re.compile(rule.get("pattern", ""))
            except re.error as exc:
                expect(f"[{rid}] pattern does not compile: {exc}", False)
                continue
            for cmd in rule.get("block", []):
                for tool in SHELL_TOOLS:
                    rc, err = run(cmd, project, tool)
                    expect(f"[{rid}] {tool}: expected BLOCK: {cmd!r} (rc {rc})", rc == 2)
                    expect(f"[{rid}] {tool}: block message lacks the rule id / Instead line: {cmd!r}",
                           rc != 2 or (f"[{rid}]" in err.decode("utf-8", "replace") and b"Instead:" in err))
            for cmd in rule.get("allow", []):
                for tool in SHELL_TOOLS:
                    rc, _ = run(cmd, project, tool)
                    expect(f"[{rid}] {tool}: expected PASS: {cmd!r} (rc {rc})", rc == 0)
            if rule.get("scope") == "repo":
                for cmd in rule.get("block", []):
                    rc, _ = run(cmd, worktree)
                    expect(f"[{rid}] a linked worktree of this repo is this repo: expected BLOCK: {cmd!r}", rc == 2)
                    rc, _ = run(cmd, other)
                    expect(f"[{rid}] cwd in ANOTHER repo: expected PASS: {cmd!r}", rc == 0)
                    rc, _ = run(f'cd "{other}" && {cmd}', project)
                    expect(f"[{rid}] `cd <other repo> && ...`: expected PASS: {cmd!r}", rc == 0)
                    rc, _ = run(f"cd {_bash_path(other)} && {cmd}", project)
                    expect(f"[{rid}] `cd /x/other (Git Bash path) && ...`: expected PASS: {cmd!r}", rc == 0)
                    rc, _ = run(f'Set-Location -Path "{other}"; {cmd}', project, "PowerShell")
                    expect(f"[{rid}] `Set-Location <other repo>; ...`: expected PASS: {cmd!r}", rc == 0)
                    rc, _ = run(f'cd "{project}" && {cmd}', other)
                    expect(f"[{rid}] `cd <this repo> && ...` from another repo: expected BLOCK: {cmd!r}", rc == 2)
                    if cmd.startswith("git ") and not cmd.startswith("git -C"):
                        rc, _ = run(f'git -C "{other}" ' + cmd[4:], project)
                        expect(f"[{rid}] `git -C <other repo> ...`: expected PASS: {cmd!r}", rc == 0)

        # the contract: fail open, UTF-8 stderr
        rc, _ = run("", project, raw="{not json")
        expect("malformed JSON must PASS (fail open)", rc == 0)
        rc, _ = run("", project, raw="")
        expect("empty stdin must PASS", rc == 0)
        rc, _ = run("", project, raw=json.dumps({"tool_name": "Bash", "tool_input": {}}))
        expect("input without a command must PASS", rc == 0)
        rc, _ = run("git status", project, rules=tmp / "missing-rules.json")
        expect("a missing rules file must PASS (fail open)", rc == 0)
        broken = tmp / "broken-rules.json"
        broken.write_text("{ this is not json", encoding="utf-8")
        rc, _ = run("git status", project, rules=broken)
        expect("a corrupt rules file must PASS (fail open)", rc == 0)
        probe = tmp / "utf8-rules.json"
        probe.write_text(json.dumps({"rules": [
            {"id": "bad-regex", "pattern": "(", "reason": "x", "instead": "x"},
            {"id": "utf8-probe", "pattern": "utf8probe", "reason": "caf\u00e9 \u2014 na\u00efve",
             "instead": "\u2192 fine"}]}), encoding="utf-8")
        rc, err = run("echo utf8probe", project, rules=probe)
        expect("a broken rule must not disable the rules after it", rc == 2)
        expect("stderr must be UTF-8 (got %r)" % err[:120], "caf\u00e9 \u2014".encode("utf-8") in err)

    if settings_path:
        try:
            settings = json.loads(pathlib.Path(settings_path).read_text(encoding="utf-8"))
            entries = (settings.get("hooks") or {}).get("PreToolUse") or []
        except Exception as exc:  # noqa: BLE001
            entries = []
            expect(f"cannot read {settings_path}: {exc}", False)
        me = pathlib.Path(__file__).name
        for tool in SHELL_TOOLS:
            routed = any(_matches(e.get("matcher"), tool) and any(me in (h.get("command") or "")
                                                                   for h in e.get("hooks") or [])
                         for e in entries)
            expect(f"settings: {tool} calls are not routed through {me}", routed)
        for e in entries:
            for h in e.get("hooks") or []:
                c = h.get("command") or ""
                expect(f"settings: `{c}` fails CLOSED (`|| exit 2`); the guard must fail open",
                       not (me in c and re.search(r"\|\|\s*exit\s+2\s*$", c)))

    for f in failures:
        print("FAIL:", f)
    print(f"guard_commands self-test: {checks - len(failures)}/{checks} " + ("GREEN" if not failures else "RED"))
    return 1 if failures else 0


def _matches(matcher, tool):
    if matcher in (None, "", "*"):
        return True
    try:
        return re.fullmatch(matcher, tool) is not None
    except re.error:
        return matcher == tool


def main(argv):
    utf8_stdio()
    rules = DEFAULT_RULES
    if "--rules" in argv:
        rules = pathlib.Path(argv[argv.index("--rules") + 1])
    if "--selftest" in argv:
        settings = argv[argv.index("--settings") + 1] if "--settings" in argv else None
        return selftest(rules, settings)
    return hook(rules)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
