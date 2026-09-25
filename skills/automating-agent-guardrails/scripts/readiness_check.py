#!/usr/bin/env python3
"""Session-start READINESS CHECK: is every adopted agent guardrail actually in force in THIS session?

Run from the SessionStart hook every session. Each adopted capability is CHECKED, never assumed, and every line
ends in one status:

  OK         present and working (a live probe where one is possible)
  REPAIRED   was broken, needed no permission, and this check fixed it (for example, started the telemetry receiver)
  N/A        does not apply in this environment (cloud session, CI), with the reason
  TODO       needs no permission, but Claude must do it this session (for example, the live smoke dispatch that
             proves edited role definitions)
  ASK-OWNER  needs the owner's permission or an owner-only action. The session asks: ONE AskUserQuestion per line,
             at session start, before other work. Never a silent skip.

It FAILS OPEN: an unreadable config, a crashing check or a missing file never fails the session. The failure is
reported as an ASK-OWNER line that says to run this script by hand.

The checks come from readiness.json beside this file (or --config). A section that is absent is not adopted and
prints nothing. Paths in the config are relative to the project directory ($CLAUDE_PROJECT_DIR, else the git top
level). See the template for every key.

Usage:
  python readiness_check.py                 print the report
  python readiness_check.py --hook          SessionStart hook: emit the hook JSON; always exits 0
  python readiness_check.py --json          the lines as JSON (for tests and tools)
  python readiness_check.py --ci            repository checks only (machine-local ones are N/A); exit 1 on any
                                            ASK-OWNER or TODO line, so a broken role or hook fails CI
  python readiness_check.py --stamp ID      record that recurring owner step ID (or `roles-smoke`) was done now
  python readiness_check.py --enable-telemetry
                                            after the owner says yes: write the telemetry env into
                                            .claude/settings.local.json (per machine, git-ignored); effective from
                                            the next session
  python readiness_check.py --selftest      prove every status in a throwaway project
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ORDER = ("ASK-OWNER", "TODO", "REPAIRED", "OK", "N/A")
READONLY_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell")
ROLE_KEYS = ("name", "description", "model", "effort", "maxTurns")
SUBPROCESS_TIMEOUT_S = 20  # a hook has a budget; a check slower than this is reported, not waited on


class Line:
    def __init__(self, status, name, detail="", on_yes=""):
        self.status, self.name, self.detail, self.on_yes = status, name, detail, on_yes

    def as_dict(self):
        return {"status": self.status, "name": self.name, "detail": self.detail, "on_yes": self.on_yes}


# ------------------------------------------------------------------------------------------------ environment

def detect_env(force=None):
    if force:
        return force
    if os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true":
        return "cloud"
    if os.environ.get("CI"):
        return "ci"
    return "local"


NOT_HERE = {"cloud": "cloud session: a fresh VM with no machine-local setup; applies on the owner's machines",
            "ci": "CI: machine-local checks do not apply"}


def project_dir():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return pathlib.Path(env)
    try:
        r = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           timeout=SUBPROCESS_TIMEOUT_S)
        if r.returncode == 0 and r.stdout.strip():
            return pathlib.Path(r.stdout.strip())
    except Exception:  # noqa: BLE001
        pass
    return HERE.parent.parent


def user_config_dir():
    return pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")


def state_dir(project):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(project.resolve())).strip("-")[-80:]
    base = os.environ.get("READINESS_STATE_DIR") or str(user_config_dir() / "readiness")
    return pathlib.Path(base) / slug


def load_json(path, default=None):
    path = pathlib.Path(path)
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def rel(ctx, p):
    return (ctx["project"] / p).as_posix() if not os.path.isabs(p) else p


def this_script():
    return pathlib.Path(__file__).as_posix()


# ------------------------------------------------------------------------------------------------ stamps

def read_stamp(ctx, sid):
    try:
        return json.loads((state_dir(ctx["project"]) / f"{sid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_stamp(ctx, sid):
    d = state_dir(ctx["project"])
    d.mkdir(parents=True, exist_ok=True)
    rec = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    if sid == "roles-smoke":
        rec["hash"] = roles_hash(ctx)
    (d / f"{sid}.json").write_text(json.dumps(rec), encoding="utf-8")
    return rec


def age_days(stamp):
    at = datetime.datetime.fromisoformat(stamp["at"])
    return (datetime.datetime.now(datetime.timezone.utc) - at).total_seconds() / 86400


# ------------------------------------------------------------------------------------------------ checks

def _matches(matcher, tool):
    if matcher in (None, "", "*"):
        return True
    try:
        return re.fullmatch(matcher, tool) is not None
    except re.error:
        return matcher == tool


def check_guard(ctx):
    g = ctx["cfg"].get("guard")
    if g is None:
        return []
    script = g.get("script", ".claude/hooks/guard_commands.py")
    name = pathlib.Path(script).name
    settings = load_json(ctx["project"] / g.get("settings", ".claude/settings.json"))
    entries = (settings.get("hooks") or {}).get("PreToolUse") or []
    problems = []
    for tool in g.get("shell_tools", ["Bash", "PowerShell"]):
        if not any(_matches(e.get("matcher"), tool) and any(name in (h.get("command") or "") for h in e.get("hooks") or [])
                   for e in entries):
            problems.append(f"{tool} calls are not routed through {name} (add {tool} to the PreToolUse matcher)")
    for e in entries:
        for h in e.get("hooks") or []:
            if name in (h.get("command") or "") and re.search(r"\|\|\s*exit\s+2\s*$", h.get("command") or ""):
                problems.append("the hook command ends in `|| exit 2`, so it fails CLOSED; remove it")
    path = pathlib.Path(rel(ctx, script))
    probe = ""
    if not path.exists():
        problems.append(f"{script} does not exist")
    else:
        rules = load_json(path.parent / "guard-rules.json", {"rules": []}).get("rules", [])
        sample = next((r for r in rules if r.get("block") and r.get("allow")), None)
        if not sample:
            problems.append("guard-rules.json has no rule with block and allow examples")
        else:
            env = dict(os.environ, CLAUDE_PROJECT_DIR=str(ctx["project"]))

            def run(tool, cmd):
                payload = json.dumps({"tool_name": tool, "cwd": str(ctx["project"]), "tool_input": {"command": cmd}})
                return subprocess.run([sys.executable, str(path)], input=payload.encode("utf-8"), capture_output=True,
                                      env=env, timeout=SUBPROCESS_TIMEOUT_S).returncode
            b, a = sample["block"][0], sample["allow"][0]
            tools = g.get("shell_tools", ["Bash", "PowerShell"])
            for tool in tools:  # probe every shell tool live, not only the one the matcher was read for
                rb, ra = run(tool, b), run(tool, a)
                if rb != 2 or ra != 0:
                    problems.append(f"live {tool} probe failed: `{b}` -> exit {rb} (want 2), `{a}` -> exit {ra} "
                                    f"(want 0); run `python {script} --selftest`")
            probe = f"{len(rules)} rules; live probe ({', '.join(tools)}) blocked `{b}` and passed `{a}`"
    if problems:
        return [Line("ASK-OWNER", "guard hook", "; ".join(problems) + ". These are committed-file fixes: ask before "
                     "changing them.", on_yes=f"fix it, then `python {script} --selftest --settings "
                     f"{g.get('settings', '.claude/settings.json')}`")]
    return [Line("OK", "guard hook", probe)]


def frontmatter(text):
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.DOTALL)
    return m.group(1).replace("\r\n", "\n") if m else None


def top_keys(fm):
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^([A-Za-z][\w-]*):[ \t]*(.*)$", fm, re.MULTILINE)}


def block_of(fm, key):
    m = re.search(rf"^{key}:[ \t]*\n((?:(?:[ \t]+.*|[ \t]*)(?:\n|$))*)", fm, re.MULTILINE)
    return m.group(1) if m else ""


def role_files(ctx):
    r = ctx["cfg"].get("roles") or {}
    d = ctx["project"] / r.get("dir", ".claude/agents")
    return sorted(d.glob("*.md")) if d.is_dir() else []


def roles_hash(ctx):
    h = hashlib.sha256()
    for f in role_files(ctx):
        h.update(f.name.encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def check_roles(ctx):
    r = ctx["cfg"].get("roles")
    if r is None:
        return []
    readonly, long_wait = set(r.get("readonly", [])), set(r.get("long_wait", []))
    problems, names = [], {}
    for f in role_files(ctx):
        fm = frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            problems.append(f"{f.name}: no YAML frontmatter")
            continue
        top = top_keys(fm)
        name = top.get("name") or f.stem
        names[name] = f
        missing = [k for k in ROLE_KEYS if not top.get(k)]
        if missing:
            problems.append(f"{f.name}: missing {', '.join(missing)}")
        if name in readonly:
            hooks = block_of(fm, "hooks")
            if "readonly_guard" not in hooks:
                problems.append(f"{f.name}: read-only role without the readonly_guard hook in its own `hooks:` block")
            else:
                matchers = re.findall(r"matcher:[ \t]*['\"]?([^'\"\n]+)", hooks)
                uncovered = [t for t in READONLY_TOOLS if not any(_matches(m.strip(), t) for m in matchers)]
                if uncovered:
                    problems.append(f"{f.name}: readonly_guard matcher misses {', '.join(uncovered)}")
        if name in long_wait and not re.search(r"^[ \t]+cacheTtl:[ \t]*['\"]?1h", block_of(fm, "experimental"),
                                               re.MULTILINE):
            problems.append(f"{f.name}: waits on long gates but has no `experimental: cacheTtl: 1h`")
    for n in sorted(set(r.get("required", [])) | readonly | long_wait):
        if n not in names:
            problems.append(f"role `{n}` has no definition in {r.get('dir', '.claude/agents')}")
    lines = []
    if problems:
        lines.append(Line("ASK-OWNER", "role agents", "; ".join(problems) + ". Committed-file fixes: ask first.",
                          on_yes=f"fix the definitions, then `python {this_script()} --ci`"))
    else:
        lines.append(Line("OK", "role agents", f"{len(names)} roles ({', '.join(sorted(names))}); dispatch by "
                          "agentType / subagent_type, never per-call model or effort"))
    if ctx["env"] != "local":
        lines.append(Line("N/A", "role smoke proof", NOT_HERE[ctx["env"]]))
        return lines
    stamp = read_stamp(ctx, "roles-smoke")
    if stamp and stamp.get("hash") == roles_hash(ctx):
        lines.append(Line("OK", "role smoke proof", f"current definitions live-proven {stamp['at'][:10]}"))
    else:
        lines.append(Line("TODO", "role smoke proof", "the role definitions changed since their last live proof (or "
                          "were never proven). Definitions load at session start, so THIS session has the current "
                          "files: dispatch one short smoke agent per role by agentType; each reports its model and "
                          "effort; each read-only role tries one Write inside the repo (must be BLOCKED) and one in "
                          f"scratch (must pass). Then run `python {this_script()} --stamp roles-smoke`."))
    return lines


def telemetry_env(port):
    return {"CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_METRICS_EXPORTER": "otlp", "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json", "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{port}"}


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_telemetry(ctx):
    t = ctx["cfg"].get("telemetry")
    if t is None:
        return []
    port = int(t.get("port", 4318))
    lines = []
    committed = (load_json(ctx["project"] / ".claude" / "settings.json").get("env") or {})
    if str(committed.get("CLAUDE_CODE_ENABLE_TELEMETRY", "")) == "1":
        lines.append(Line("ASK-OWNER", "telemetry scope", "telemetry is enabled in the COMMITTED .claude/settings.json, "
                          "so every clone, CI run and cloud session exports to a loopback port with no receiver. "
                          "Ask to move it to .claude/settings.local.json.",
                          on_yes=f"remove the OTEL/telemetry env from .claude/settings.json; `python {this_script()} "
                          "--enable-telemetry`"))
    if ctx["env"] != "local":
        return lines + [Line("N/A", "telemetry", NOT_HERE[ctx["env"]])]
    local = load_json(ctx["project"] / ".claude" / "settings.local.json").get("env") or {}
    user = load_json(user_config_dir() / "settings.json").get("env") or {}
    enabled = any(str(src.get("CLAUDE_CODE_ENABLE_TELEMETRY", "")) == "1" for src in (local, user, os.environ))
    if not enabled:
        return lines + [Line("ASK-OWNER", "telemetry", "not enabled on this machine. Ask: \"Enable local cost "
                             "telemetry (tokens and cost per agent, skill and model, recorded only on this "
                             "machine)?\" It takes effect from the next session.",
                             on_yes=f"python {this_script()} --enable-telemetry")]
    report = rel(ctx, t.get("report", ".claude/hooks/usage_report.py"))
    if listening(port):
        return lines + [Line("OK", "telemetry", f"receiver on 127.0.0.1:{port}; report: python {report}")]
    sink = pathlib.Path(rel(ctx, t.get("sink", ".claude/hooks/otlp_sink.py")))
    try:
        r = subprocess.run([sys.executable, str(sink), "--ensure", "--port", str(port)], capture_output=True,
                           text=True, timeout=SUBPROCESS_TIMEOUT_S)
        started = r.returncode == 0 and listening(port)
    except Exception as exc:  # noqa: BLE001
        started, r = False, exc
    if started:
        return lines + [Line("REPAIRED", "telemetry", f"the receiver was down; started it on 127.0.0.1:{port}. "
                             f"Report: python {report}")]
    return lines + [Line("ASK-OWNER", "telemetry", f"the receiver is down and could not be started ({r}); "
                         "this session's usage is not being recorded.", on_yes=f"python {sink.as_posix()} --port {port}")]


def plugin_enabled(ctx, plugin):
    for path in (user_config_dir() / "settings.json", ctx["project"] / ".claude" / "settings.json",
                 ctx["project"] / ".claude" / "settings.local.json"):
        if (load_json(path).get("enabledPlugins") or {}).get(plugin):
            return True
    return False


def check_lsp(ctx):
    lines = []
    for spec in ctx["cfg"].get("lsp") or []:
        label = f"LSP ({spec.get('name', spec.get('server'))})"
        if ctx["env"] != "local":
            lines.append(Line("N/A", label, NOT_HERE[ctx["env"]]))
            continue
        plugin_ok = plugin_enabled(ctx, spec["plugin"])
        server_ok = bool(shutil.which(spec["server"])) or any(
            pathlib.Path(os.path.expanduser(p)).exists() for p in spec.get("paths", []))
        if plugin_ok and server_ok:
            lines.append(Line("OK", label, "navigate with the LSP tool (definition, references, symbols) before grep"))
            continue
        need = ([] if plugin_ok else [("the plugin is not enabled", f"/plugin install {spec['plugin']}")]) + \
               ([] if server_ok else [(f"the `{spec['server']}` server binary is missing",
                                       spec.get("install", f"install {spec['server']}"))])
        lines.append(Line("ASK-OWNER", label, "; ".join(n for n, _ in need) + ". Ask before installing anything; it "
                          "takes effect from the next session.", on_yes="; then ".join(f"`{c}`" for _, c in need)))
    return lines


def check_recurring(ctx):
    lines = []
    for item in ctx["cfg"].get("recurring") or []:
        label = item["command"]
        if ctx["env"] != "local":
            lines.append(Line("N/A", label, NOT_HERE[ctx["env"]]))
            continue
        every = float(item.get("every_days", 7))
        stamp = read_stamp(ctx, item["id"])
        age = age_days(stamp) if stamp else None
        if age is not None and age < every:
            lines.append(Line("OK", label, f"last run {stamp['at'][:10]}; due again in {every - age:.0f} day(s)"))
        else:
            last = stamp["at"][:10] if stamp else "never"
            lines.append(Line("ASK-OWNER", label, f"owner-only, due every {every:g} days (last: {last})"
                              + (f"; {item['why']}" if item.get("why") else "")
                              + f". Ask the owner to run `{label}`.",
                              on_yes=f"after it runs: python {this_script()} --stamp {item['id']}"))
    return lines


CHECKS = (check_guard, check_roles, check_telemetry, check_lsp, check_recurring)


def run_checks(ctx):
    lines = []
    for check in CHECKS:
        try:
            lines.extend(check(ctx))
        except Exception as exc:  # noqa: BLE001 - one crashing check never hides the others
            lines.append(Line("ASK-OWNER", check.__name__.replace("check_", ""),
                              f"the check crashed ({type(exc).__name__}: {exc}), so this capability is UNVERIFIED",
                              on_yes=f"python {this_script()}  (read the error, fix the cause)"))
    return lines


# ------------------------------------------------------------------------------------------------ output

def render(lines, ctx):
    counts = {s: sum(1 for l in lines if l.status == s) for s in ORDER}
    out = [f"READINESS CHECK ({this_script()}), {ctx['env']} session. Every line was checked now, not assumed."]
    for l in sorted(lines, key=lambda l: ORDER.index(l.status)):
        out.append(f"  {l.status:10} {l.name}" + (f": {l.detail}" if l.detail else "")
                   + (f"\n             On yes: {l.on_yes}" if l.on_yes and l.status == "ASK-OWNER" else ""))
    if counts["ASK-OWNER"]:
        out.append(f"ACTION: {counts['ASK-OWNER']} ASK-OWNER line(s). Before other work, ask the owner about EACH "
                   "one: one AskUserQuestion per line, offering its On-yes step. Never skip one silently. On yes, do "
                   "it; on no, carry on without it and do not re-ask this session.")
    if counts["TODO"]:
        out.append(f"ACTION: {counts['TODO']} TODO line(s): no permission needed. Do them this session.")
    triggers = ctx["cfg"].get("ask_at_trigger") or []
    if triggers:
        out.append("Owner-only or billed steps, asked at their trigger (not now):")
        out.extend(f"  - `{t['step']}`: {t['trigger']}" for t in triggers)
    summary = "Readiness: " + ", ".join(f"{counts[s]} {s}" for s in ORDER if counts[s])
    if counts["ASK-OWNER"]:
        summary += " (Claude will ask you about each ASK-OWNER item)"
    return "\n".join(out), summary


def failure_text(exc):
    return (f"READINESS CHECK FAILED TO RUN ({type(exc).__name__}: {exc}). Nothing was verified this session.\n"
            f"  ASK-OWNER  readiness check: tell the owner, then run `python {this_script()}` by hand and fix the "
            "cause (often a malformed readiness.json).")


def build_ctx(argv, env_force=None):
    cfg_path = pathlib.Path(argv[argv.index("--config") + 1]) if "--config" in argv else HERE / "readiness.json"
    return {"project": project_dir(), "cfg": load_json(cfg_path), "env": detect_env(env_force)}


def hook_payload(argv=()):
    """(additionalContext, systemMessage). Never raises."""
    try:
        ctx = build_ctx(list(argv))
        return render(run_checks(ctx), ctx)
    except Exception as exc:  # noqa: BLE001 - fail open, loudly
        return failure_text(exc), "Readiness check FAILED to run; Claude will tell you."


def enable_telemetry(ctx):
    port = int((ctx["cfg"].get("telemetry") or {}).get("port", 4318))
    path = ctx["project"] / ".claude" / "settings.local.json"
    data = load_json(path)
    data.setdefault("env", {}).update(telemetry_env(port))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    note = ""
    ignored = subprocess.run(["git", "-C", str(ctx["project"]), "check-ignore", "-q", str(path)], capture_output=True)
    if ignored.returncode == 1:
        exclude = subprocess.run(["git", "-C", str(ctx["project"]), "rev-parse", "--git-path", "info/exclude"],
                                 capture_output=True, text=True).stdout.strip()
        if exclude:
            exclude_path = pathlib.Path(exclude)
            if not exclude_path.is_absolute():
                exclude_path = ctx["project"] / exclude_path
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            with open(exclude_path, "a", encoding="utf-8") as f:
                f.write("\n.claude/settings.local.json\n")
            note = " Added it to .git/info/exclude so it is never committed."
    print(f"Wrote the telemetry env to {path.as_posix()}.{note} It takes effect from the next session.")
    return 0


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if "--hook" in argv:
        try:
            if not sys.stdin.isatty():
                sys.stdin.read()
        except Exception:  # noqa: BLE001
            pass
        context, summary = hook_payload(argv)
        try:
            json.dump({"systemMessage": summary,
                       "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}},
                      sys.stdout)
        except Exception:  # noqa: BLE001
            pass
        return 0
    if "--selftest" in argv:
        return selftest()
    ctx = build_ctx(argv, "ci" if "--ci" in argv else None)
    if "--stamp" in argv:
        rec = write_stamp(ctx, argv[argv.index("--stamp") + 1])
        print(f"stamped {argv[argv.index('--stamp') + 1]} at {rec['at']}")
        return 0
    if "--enable-telemetry" in argv:
        return enable_telemetry(ctx)
    lines = run_checks(ctx)
    if "--json" in argv:
        print(json.dumps([l.as_dict() for l in lines], indent=1))
        return 0
    print(render(lines, ctx)[0])
    if "--ci" in argv:
        return 1 if any(l.status in ("ASK-OWNER", "TODO") for l in lines) else 0
    return 0


# ------------------------------------------------------------------------------------------------ self-test

GOOD_ROLES = {
    "implementer.md": "---\nname: implementer\ndescription: fixes\nmodel: opus\neffort: high\nmaxTurns: 220\n"
                      "experimental:\n  cacheTtl: 1h\n---\nbody\n",
    "refuter.md": "---\nname: refuter\ndescription: refutes\nmodel: opus\neffort: xhigh\nmaxTurns: 160\nhooks:\n"
                  "  PreToolUse:\n    - matcher: \"Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell\"\n      hooks:\n"
                  "        - type: command\n          command: python \"$CLAUDE_PROJECT_DIR/.claude/hooks/"
                  "readonly_guard.py\"\nexperimental:\n  cacheTtl: 1h\n---\nbody\n",
    "chore.md": "---\nname: chore\ndescription: chores\nmodel: sonnet\neffort: medium\nmaxTurns: 80\n---\nbody\n",
}


def selftest():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        proj, conf, state = tmp / "project", tmp / "config", tmp / "state"
        hooks, agents = proj / ".claude" / "hooks", proj / ".claude" / "agents"
        for d in (hooks, agents, conf):
            d.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(proj)], check=True, capture_output=True)
        for f in ("guard_commands.py", "otlp_sink.py"):
            shutil.copy(HERE / f, hooks / f)
        (hooks / "guard-rules.json").write_text(json.dumps({"rules": [{
            "id": "no-stash", "scope": "repo", "pattern": r"\bgit\s+stash\b(?!\s+list\b)", "reason": "r",
            "instead": "i", "block": ["git stash"], "allow": ["git stash list"]}]}), encoding="utf-8")
        settings = {"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell", "hooks": [
            {"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_commands.py\""}]}]}}
        (proj / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        for name, text in GOOD_ROLES.items():
            (agents / name).write_text(text, encoding="utf-8")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        fake_ls = tmp / "bin" / "fake-ls"
        cfg = {"guard": {}, "roles": {"required": ["implementer", "refuter", "chore"], "readonly": ["refuter"],
                                      "long_wait": ["implementer", "refuter"]},
               "telemetry": {"port": port},
               "lsp": [{"name": "fake", "plugin": "fake-lsp@x", "server": "fake-ls-not-on-path",
                        "paths": [str(fake_ls)], "install": "install-fake-ls"}],
               "recurring": [{"id": "weekly-review", "command": "/weekly-review", "every_days": 7}],
               "ask_at_trigger": [{"step": "/code-review ultra", "trigger": "before a landing push"}]}
        cfg_path = hooks / "readiness.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        base_env = {k: v for k, v in os.environ.items()
                    if k not in ("CLAUDE_CODE_REMOTE", "CI", "PYTHONIOENCODING", "PYTHONUTF8")}
        base_env.update(CLAUDE_PROJECT_DIR=str(proj), CLAUDE_CONFIG_DIR=str(conf), READINESS_STATE_DIR=str(state))

        def run(*args, **env_extra):
            env = dict(base_env, **env_extra)
            return subprocess.run([sys.executable, __file__, "--config", str(cfg_path), *args], capture_output=True,
                                  env=env, timeout=120, stdin=subprocess.DEVNULL)

        def statuses(**env_extra):
            r = run("--json", **env_extra)
            return {l["name"]: l for l in json.loads(r.stdout.decode("utf-8"))}

        def expect(label, cond):
            if not cond:
                failures.append(label)

        def hook_output(r, label):
            try:
                payload = json.loads(r.stdout.decode("utf-8"))
                return payload, payload["hookSpecificOutput"]["additionalContext"]
            except Exception:  # noqa: BLE001
                failures.append(f"{label}: the hook emitted no valid hook JSON (rc {r.returncode}): "
                                f"{(r.stdout + r.stderr).decode('utf-8', 'replace')[-300:]}")
                return {}, ""

        try:
            s = statuses()
            expect(f"fresh: guard OK ({s.get('guard hook')})", s.get("guard hook", {}).get("status") == "OK")
            expect(f"fresh: roles OK ({s.get('role agents')})", s.get("role agents", {}).get("status") == "OK")
            expect("fresh: smoke proof TODO", s.get("role smoke proof", {}).get("status") == "TODO")
            expect("fresh: telemetry ASK-OWNER", s.get("telemetry", {}).get("status") == "ASK-OWNER")
            expect("fresh: telemetry ASK-OWNER carries the on-yes command",
                   "--enable-telemetry" in s.get("telemetry", {}).get("on_yes", ""))
            expect("fresh: LSP ASK-OWNER", s.get("LSP (fake)", {}).get("status") == "ASK-OWNER")
            expect("fresh: recurring ASK-OWNER", s.get("/weekly-review", {}).get("status") == "ASK-OWNER")

            r = run("--hook", CLAUDE_CODE_REMOTE="false")
            payload, ctx_text = hook_output(r, "hook")
            expect("hook: exit 0", r.returncode == 0)
            expect("hook: tells Claude to ask with AskUserQuestion", "AskUserQuestion" in ctx_text)
            expect("hook: lists the trigger-bound steps", "/code-review ultra" in ctx_text)
            expect("hook: systemMessage shown to the owner", "ASK-OWNER" in payload.get("systemMessage", ""))

            for sid in ("roles-smoke", "weekly-review"):
                run("--stamp", sid)
            run("--enable-telemetry")
            (conf / "settings.json").write_text(json.dumps({"enabledPlugins": {"fake-lsp@x": True}}), encoding="utf-8")
            fake_ls.parent.mkdir()
            fake_ls.write_text("", encoding="utf-8")
            s = statuses()
            expect(f"after stamp: smoke OK ({s.get('role smoke proof')})", s.get("role smoke proof", {}).get("status") == "OK")
            expect("after stamp: recurring OK", s.get("/weekly-review", {}).get("status") == "OK")
            expect(f"telemetry enabled + receiver down: REPAIRED ({s.get('telemetry')})",
                   s.get("telemetry", {}).get("status") == "REPAIRED")
            expect("telemetry: second run OK", statuses().get("telemetry", {}).get("status") == "OK")
            expect("LSP plugin + server: OK", s.get("LSP (fake)", {}).get("status") == "OK")
            ignored = subprocess.run(["git", "-C", str(proj), "check-ignore", "-q",
                                      str(proj / ".claude" / "settings.local.json")])
            expect("settings.local.json is git-ignored after --enable-telemetry", ignored.returncode == 0)

            stamp = state / next(state.iterdir()).name / "weekly-review.json"
            old = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
            stamp.write_text(json.dumps({"at": old}), encoding="utf-8")
            expect("stamp 8 days old: ASK-OWNER", statuses().get("/weekly-review", {}).get("status") == "ASK-OWNER")
            (agents / "chore.md").write_text(GOOD_ROLES["chore.md"].replace("medium", "low"), encoding="utf-8")
            expect("edited role: smoke TODO again", statuses().get("role smoke proof", {}).get("status") == "TODO")

            s = statuses(CLAUDE_CODE_REMOTE="true")
            for name in ("role smoke proof", "telemetry", "LSP (fake)", "/weekly-review"):
                expect(f"cloud: {name} N/A (got {s.get(name, {}).get('status')})", s.get(name, {}).get("status") == "N/A")
            expect("cloud: guard still checked", s.get("guard hook", {}).get("status") == "OK")
            expect("--ci on a good repo exits 0", run("--ci").returncode == 0)

            (agents / "chore.md").write_text(GOOD_ROLES["chore.md"].replace("maxTurns: 80\n", ""), encoding="utf-8")
            (agents / "refuter.md").write_text(GOOD_ROLES["refuter.md"].split("hooks:")[0] + "---\nbody\n",
                                               encoding="utf-8")
            (agents / "implementer.md").write_text(GOOD_ROLES["implementer.md"].replace("  cacheTtl: 1h\n", ""),
                                                   encoding="utf-8")
            settings["hooks"]["PreToolUse"][0]["matcher"] = "Bash"
            settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] += " || exit 2"
            settings["env"] = {"CLAUDE_CODE_ENABLE_TELEMETRY": "1"}
            (proj / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
            s = statuses()
            roles = s.get("role agents", {})
            expect("broken roles: ASK-OWNER", roles.get("status") == "ASK-OWNER")
            for needle in ("maxTurns", "readonly_guard", "cacheTtl"):
                expect(f"broken roles: names `{needle}`", needle in roles.get("detail", ""))
            guard = s.get("guard hook", {})
            expect("guard: PowerShell not routed is flagged", "PowerShell" in guard.get("detail", ""))
            expect("guard: fail-closed wrapper is flagged", "fails CLOSED" in guard.get("detail", ""))
            expect("committed telemetry is flagged", s.get("telemetry scope", {}).get("status") == "ASK-OWNER")
            expect("--ci on a broken repo exits 1", run("--ci").returncode == 1)

            cfg_path.write_text("{ corrupt", encoding="utf-8")
            r = run("--hook")
            payload, text = hook_output(r, "corrupt config")
            expect("corrupt config: hook exits 0", r.returncode == 0)
            expect("corrupt config: hook still emits an ASK-OWNER line", "ASK-OWNER" in text and "FAILED" in text)
        finally:
            subprocess.run([sys.executable, str(hooks / "otlp_sink.py"), "--stop", "--port", str(port)],
                           env=base_env, capture_output=True)
    for f in failures:
        print("FAIL:", f)
    print(f"readiness_check self-test: {'GREEN' if not failures else 'RED'} ({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
