#!/usr/bin/env python3
"""stall_watch.py — notice a stalled workflow agent within minutes, not hours.

    python stall_watch.py <workflow transcript dir> [--model-stall 600] [--tool-stall 720] [--poll 60] [--once]

Run it in the background next to every fleet workflow; it EXITS the moment an agent stalls, so the orchestrator
is woken by its completion rather than by a person asking. It reads the workflow's `journal.jsonl` (an agent that
has `started` but has no `result` is pending) and, for each pending agent, the LAST record of its transcript
(`agent-<id>.jsonl`, the record's own timestamp, never the file's mtime):

  waiting on the MODEL (last record is not an unanswered tool call)  silent > --model-stall seconds  -> STALLED
  inside a TOOL call  (last record is an unanswered tool_use)          silent > --tool-stall seconds   -> STALLED

Why these thresholds, measured over 150 agent transcripts (~27,800 silences): waiting on the model, 99.9 % of
silences were under 94 s; inside a tool call the maximum was 585 s (a 580 s blocking gate wait; shell tools cap at
600 s). Why it exists: one implementer's model call hung after it had finished and gated its work; nothing
noticed for 90 minutes, and the wave's final train waited on it the whole time. A workflow cannot stop one of
its own agents and nothing outside can either, so the remedy is to let the other agents finish, stop the
workflow, and dispatch the remainder by hand (see the skill's "A stalled agent" rule) - which only works if the
stall is noticed.

Exit codes: 3 = at least one agent stalled (printed with its label, silence and last action); 0 = with --once,
nothing stalled. A transcript that cannot be read is reported, never treated as healthy.
"""
import argparse, datetime, json, pathlib, sys, time


def last_record(path):
    """(timestamp, in_tool, tool_name, preview) of the transcript's last message record, or None."""
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 262144))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        content = (o.get("message") or {}).get("content")
        ts = o.get("timestamp")
        if not ts or not isinstance(content, list):
            continue
        parts = [p for p in content if isinstance(p, dict)]
        uses = [p for p in parts if p.get("type") == "tool_use"]
        when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if o.get("type") == "assistant" and uses:
            u = uses[-1]
            return when, True, u.get("name", ""), json.dumps(u.get("input", {}))[:160]
        kind = parts[-1].get("type") if parts else ""
        return when, False, "", kind
    return None


def pending(wf):
    started, done = {}, set()
    for line in (wf / "journal.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") == "started":
            started[o.get("agentId")] = o.get("label", "")
        elif o.get("type") == "result":
            done.add(o.get("agentId"))
    return {a: l for a, l in started.items() if a not in done}


def check(wf, model_stall, tool_stall):
    now = datetime.datetime.now(datetime.timezone.utc)
    stalled, report = [], []
    for aid, label in sorted(pending(wf).items(), key=lambda x: x[1]):
        rec = last_record(wf / f"agent-{aid}.jsonl")
        if rec is None:
            stalled.append(f"{label} ({aid}): transcript unreadable or empty")
            continue
        when, in_tool, tool, preview = rec
        silent = (now - when).total_seconds()
        limit = tool_stall if in_tool else model_stall
        state = f"in {tool}" if in_tool else "waiting on the model"
        line = f"{label} ({aid}): {state}, silent {int(silent // 60)}m{int(silent % 60):02d}s (limit {limit // 60}m)"
        report.append(line)
        if silent > limit:
            stalled.append(line + (f" — last call: {preview}" if in_tool else f" — last record: {preview}"))
    return stalled, report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("workflow_dir")
    ap.add_argument("--model-stall", type=int, default=600)
    ap.add_argument("--tool-stall", type=int, default=720)
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--once", action="store_true", help="check once, print every pending agent, and exit")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    wf = pathlib.Path(a.workflow_dir)
    while True:
        stalled, report = check(wf, a.model_stall, a.tool_stall)
        if a.once:
            print("\n".join(report) or "no pending agents")
        if stalled:
            print("STALLED:\n  " + "\n  ".join(stalled), flush=True)
            return 3
        if a.once:
            return 0
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
