#!/usr/bin/env python3
"""SessionStart hook: the project's own live-state probe (optional) plus the guardrail readiness check, injected as
context at the start of every session (startup, resume, clear, compact).

Copy to .claude/hooks/session_start.py beside readiness_check.py and register it in .claude/settings.json:

    "SessionStart": [{"matcher": "startup|resume|clear|compact",
                      "hooks": [{"type": "command", "timeout": 60,
                                 "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/session_start.py\""}]}]

It never fails the session: every error becomes text in the context, and the readiness part degrades to an
ASK-OWNER line telling Claude to run the check by hand.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def project_probe() -> str:
    """Replace with your project's mechanical state probe (branch, unpushed commits, next work item, gate baseline).
    Return plain text; return "" to omit the section."""
    return ""


def readiness() -> tuple:
    try:
        sys.dont_write_bytecode = True  # no __pycache__ litter in the tree on every session start
        sys.path.insert(0, str(HERE))
        import readiness_check
        return readiness_check.hook_payload()
    except Exception as exc:  # noqa: BLE001 - a hook must never break the session
        return (f"READINESS CHECK FAILED TO LOAD ({type(exc).__name__}: {exc}).\n"
                f"  ASK-OWNER  readiness check: tell the owner, then run "
                f"`python {(HERE / 'readiness_check.py').as_posix()}` by hand.",
                "Readiness check FAILED to load; Claude will tell you.")


def main() -> int:
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()  # the SessionStart event JSON; not needed here
    except Exception:  # noqa: BLE001
        pass
    try:
        probe = project_probe()
    except Exception as exc:  # noqa: BLE001
        probe = f"project probe failed: {type(exc).__name__}: {exc}"
    context, summary = readiness()
    text = (probe + "\n\n" if probe else "") + context
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    json.dump({"systemMessage": summary,
               "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
