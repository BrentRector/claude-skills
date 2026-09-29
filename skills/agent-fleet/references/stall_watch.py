#!/usr/bin/env python3
"""stall_watch.py — notice a stalled workflow agent within minutes, not hours.

    python stall_watch.py <workflow transcript dir> [--model-stall 600] [--tool-stall 720] [--idle 600] [--poll 60] [--once]

Run it in the background next to every fleet workflow; it EXITS the moment an agent stalls, so the orchestrator
is woken by its completion rather than by a person asking. It reads the workflow's `journal.jsonl` (an agent that
has `started` but neither a `result` nor a `failed` record is pending; a `failed` one is DEAD and reported as
such) and, for each pending agent, the LAST record of its transcript (`agent-<id>.jsonl`, the record's own
timestamp, never the file's mtime):

  waiting on the MODEL (last record is not an unanswered tool call)  silent > --model-stall seconds  -> STALLED
  inside a TOOL call  (last record is an unanswered tool_use)          silent > --tool-stall seconds   -> STALLED
  NO agent in flight  (every started agent finished or failed)        idle > --idle seconds          -> IDLE
  an agent DIES while the watch runs (a journal `failed` record)      at once                       -> FAILED

A death is work to recover: the scheduler moves on, but the dead agent's checkpoint needs a finisher, so a NEW
death wakes the orchestrator. (Measured: three of six implementers in one wave died near the end with no error
recorded, and nothing noticed until someone looked.) Deaths already present when a live watch starts are listed,
not alarmed; `--once` replays history and alarms on every death.

The IDLE check does not trust the scheduler's own claim to be running. A workflow whose scheduler has hung
reports "running" indefinitely, but no agent is working and no transcript is being written. That happened once:
an agent died on an API error, a scheduler bug left its successor waiting on it forever, and the workflow showed
"running" for 16 hours. A workflow that finished normally delivers its completion notice first; stop the watcher
then, or its IDLE exit is one harmless false wake-up.

Why these thresholds, measured over 150 agent transcripts (~27,800 silences): waiting on the model, 99.9 % of
silences were under 94 s; inside a tool call the maximum was 585 s (a 580 s blocking gate wait; shell tools cap at
600 s). Why it exists: one implementer's model call hung after it had finished and gated its work; nothing
noticed for 90 minutes, and the wave's final train waited on it the whole time. A workflow cannot stop one of
its own agents and nothing outside can either, so the remedy is to let the other agents finish, stop the
workflow, and dispatch the remainder by hand (see the skill's "A stalled agent" rule) - which only works if the
stall is noticed.

Exit codes: 3 = at least one agent stalled, or the workflow is IDLE (printed with the label, silence and last
action); 0 = with --once, nothing stalled. A transcript that cannot be read is reported, never treated as healthy.
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


def journal(wf):
    """(pending, failed) from the workflow's journal.jsonl, each {agentId: label}.

    `started` opens an agent; `result` or `failed` closes it. A `failed` agent is DEAD, not waiting: it is reported
    as failed and never counted as in flight.
    """
    started, done, failed = {}, set(), {}
    for line in (wf / "journal.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        kind, aid = o.get("type"), o.get("agentId")
        if kind == "started":
            started[aid] = o.get("label", "")
        elif kind == "result":
            done.add(aid)
        elif kind == "failed":
            done.add(aid)
            failed[aid] = started.get(aid, "")
    return {a: l for a, l in started.items() if a not in done}, failed


def last_activity(wf):
    """The newest record timestamp across every agent transcript of the workflow, or None.

    journal.jsonl records carry no timestamp, so the workflow's last sign of life is its agents' own records
    (never a file's mtime).
    """
    stamps = [rec[0] for rec in map(last_record, wf.glob("agent-*.jsonl")) if rec]
    return max(stamps, default=None)


def check(wf, model_stall, tool_stall, idle_limit, watch_start, known_failed=frozenset()):
    now = datetime.datetime.now(datetime.timezone.utc)
    stalled, report = [], []
    pending, failed = journal(wf)
    for aid, label in sorted(failed.items(), key=lambda x: x[1]):
        line = f"{label} ({aid}): FAILED (the agent died; the journal holds no result)"
        report.append(line)
        # A death is work to recover (a finisher from its checkpoint), so a NEW one wakes the orchestrator even though
        # the scheduler moves on. Deaths already present when the watch started were reported then.
        if aid not in known_failed:
            stalled.append(line + " — dispatch a finisher from its checkpoint")
    for aid, label in sorted(pending.items(), key=lambda x: x[1]):
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
    if not pending:
        # Nothing in flight. A workflow still reported RUNNING with no agent working is hung in its own scheduler,
        # whatever it says about itself. A finished workflow delivers its completion notice first, and the
        # orchestrator stops this watcher then.
        since = max((t for t in (last_activity(wf), watch_start) if t is not None), default=now)
        idle = (now - since).total_seconds()
        line = f"nothing in flight, idle {int(idle // 60)}m{int(idle % 60):02d}s (limit {idle_limit // 60}m)"
        report.append(line)
        if idle > idle_limit:
            stalled.append(f"IDLE: {line} — if the workflow still reports running, its scheduler is hung")
    return stalled, report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("workflow_dir")
    ap.add_argument("--model-stall", type=int, default=600)
    ap.add_argument("--tool-stall", type=int, default=720)
    ap.add_argument("--idle", type=int, default=600,
                    help="seconds with NO agent in flight and no agent activity before the scheduler is reported hung")
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--once", action="store_true", help="check once, print every agent's state, and exit")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    wf = pathlib.Path(a.workflow_dir)
    # A live watch counts idleness from its own start at the earliest, so a watcher started between two agents
    # does not fire on the gap before it began; --once replays history and counts from the last activity alone.
    watch_start = None if a.once else datetime.datetime.now(datetime.timezone.utc)
    # A live watch alarms on deaths that happen WHILE it watches; --once replays history and reports every death.
    known_failed = frozenset() if a.once else frozenset(journal(wf)[1]) if (wf / "journal.jsonl").exists() else frozenset()
    while True:
        stalled, report = check(wf, a.model_stall, a.tool_stall, a.idle, watch_start, known_failed)
        if a.once:
            print("\n".join(report))
        if stalled:
            print("STALLED:\n  " + "\n  ".join(stalled), flush=True)
            return 3
        if a.once:
            return 0
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
