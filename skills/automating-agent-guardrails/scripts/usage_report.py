#!/usr/bin/env python3
"""Tokens and cost per agent / skill / model, from the Claude Code telemetry that otlp_sink.py recorded.

    python usage_report.py                         today (UTC), grouped by agent, skill, model
    python usage_report.py 2026-09-25 2026-09-26   named days
    python usage_report.py --all --by agent        every recorded day, one dimension
    python usage_report.py --keys                  the attribute keys your Claude Code version actually sends
    python usage_report.py --selftest              start a receiver on a free port, post a sample, check the sums
    options: --dir DIR (default: $CLAUDE_CONFIG_DIR/telemetry or ~/.claude/telemetry)
             --by DIMS (comma list of agent, skill, model, session; default agent,skill,model)

It reads the `api_request` log events (one per model call: model, token counts, cost_usd). Attribute names vary by
Claude Code version, so each dimension is read from the first attribute present in its candidate list below. Run
--keys once on real data and add your version's names if a dimension shows only "-". An event missing an
attribute is grouped under "-", never dropped, and the event count is printed as the witness: a report over zero
events exits 1 instead of printing an empty table that looks like "no cost".
"""
import collections
import datetime
import json
import os
import pathlib
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request

TOKENS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
DIMENSIONS = {
    "agent": ("agent.name", "agent_name", "agent.type", "agent_type", "subagent_type", "query_source"),
    "skill": ("skill.name", "skill_name", "skill"),
    "model": ("model",),
    "session": ("session.id", "session_id"),
}


def default_dir():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(pathlib.Path.home() / ".claude")
    return pathlib.Path(base) / "telemetry"


def flatten(attributes):
    out = {}
    for a in attributes or []:
        v = a.get("value") or {}
        for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
            if k in v:
                out[a.get("key")] = v[k]
                break
    return out


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def api_requests(files):
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for rl in (rec.get("body") or {}).get("resourceLogs", []):
                resource = flatten((rl.get("resource") or {}).get("attributes"))
                for sl in rl.get("scopeLogs", []):
                    for lr in sl.get("logRecords", []):
                        a = {**resource, **flatten(lr.get("attributes"))}
                        name = str(a.get("event.name") or (lr.get("body") or {}).get("stringValue") or "")
                        if name.endswith("api_request"):
                            yield a


def pick(a, dim):
    return str(next((a[k] for k in DIMENSIONS[dim] if a.get(k) not in (None, "")), "-"))


def summarize(files, dims):
    groups = collections.defaultdict(collections.Counter)
    n = 0
    for a in api_requests(files):
        n += 1
        c = groups[tuple(pick(a, d) for d in dims)]
        c["calls"] += 1
        for t in TOKENS:
            c[t] += num(a.get(t))
        c["cost_usd"] += num(a.get("cost_usd"))
    return n, groups


def render(n, groups, dims, nfiles):
    lines = [f"{n} api_request events in {nfiles} file(s)"]
    head = "".join(f"{d:26}" for d in dims)
    lines.append(f"{head}{'calls':>7} {'input':>11} {'output':>10} {'cache-read':>13} {'cache-write':>12} {'usd':>9}")
    total = collections.Counter()
    for key, c in sorted(groups.items(), key=lambda kv: -kv[1]["cost_usd"]):
        total.update(c)
        lines.append("".join(f"{k[:25]:26}" for k in key) + f"{int(c['calls']):7} {int(c['input_tokens']):11} "
                     f"{int(c['output_tokens']):10} {int(c['cache_read_tokens']):13} "
                     f"{int(c['cache_creation_tokens']):12} {c['cost_usd']:9.2f}")
    lines.append(f"{'TOTAL':{26 * len(dims)}}{int(total['calls']):7} {int(total['input_tokens']):11} "
                 f"{int(total['output_tokens']):10} {int(total['cache_read_tokens']):13} "
                 f"{int(total['cache_creation_tokens']):12} {total['cost_usd']:9.2f}")
    return "\n".join(lines), total


def keys(files):
    seen = collections.Counter()
    for a in api_requests(files):
        seen.update(a.keys())
    return seen


def select_files(argv, directory):
    if "--all" in argv:
        return sorted(directory.glob("*.jsonl"))
    skip = {"--dir", "--by"}
    days = [d for i, d in enumerate(argv) if not d.startswith("-") and (i == 0 or argv[i - 1] not in skip)]
    days = days or [f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d}"]
    return [directory / f"{d}.jsonl" for d in days if (directory / f"{d}.jsonl").exists()]


def _event(agent, skill, model, cost, inp, out):
    attrs = {"event.name": "api_request", "model": model, "cost_usd": cost, "input_tokens": inp,
             "output_tokens": out, "cache_read_tokens": 1000, "cache_creation_tokens": 10}
    if agent:
        attrs["agent.name"] = agent
    if skill:
        attrs["skill.name"] = skill
    kv = [{"key": k, "value": ({"doubleValue": v} if isinstance(v, float) else
                               {"intValue": str(v)} if isinstance(v, int) else {"stringValue": v})}
          for k, v in attrs.items()]
    return {"attributes": kv, "body": {"stringValue": "claude_code.api_request"}}


def selftest():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import otlp_sink
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        server = otlp_sink.http.server.ThreadingHTTPServer(("127.0.0.1", port), otlp_sink.make_handler(out))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            body = {"resourceLogs": [{"resource": {"attributes": [
                {"key": "session.id", "value": {"stringValue": "s1"}}]}, "scopeLogs": [{"logRecords": [
                    _event(None, None, "claude-opus", 0.50, 100, 20),
                    _event("reviewer", "review", "claude-sonnet", 0.20, 50, 10),
                    _event("reviewer", None, "claude-sonnet", 0.05, 5, 1)]}]}]}
            req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/logs", data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            if urllib.request.urlopen(req, timeout=10).status != 200:
                failures.append("JSON POST was not accepted")
            try:
                urllib.request.urlopen(urllib.request.Request(
                    f"http://127.0.0.1:{port}/v1/logs", data=b"\x0a\x00",
                    headers={"Content-Type": "application/x-protobuf"}), timeout=10)
                failures.append("a protobuf POST must be refused (415), not silently recorded")
            except urllib.error.HTTPError as e:
                if e.code != 415:
                    failures.append(f"protobuf POST returned {e.code}, expected 415")
        finally:
            server.shutdown()
            server.server_close()
        files = sorted(out.glob("*.jsonl"))
        n, groups = summarize(files, ["agent"])
        text, total = render(n, groups, ["agent"], len(files))
        if n != 3:
            failures.append(f"expected 3 api_request events, read {n}")
        if abs(total["cost_usd"] - 0.75) > 1e-9:
            failures.append(f"total cost {total['cost_usd']} != 0.75")
        by_agent = {k[0]: c for k, c in groups.items()}
        if abs(by_agent.get("reviewer", {}).get("cost_usd", 0) - 0.25) > 1e-9 or "-" not in by_agent:
            failures.append(f"per-agent grouping wrong: {dict(by_agent)}")
        n2, g2 = summarize(files, ["session"])
        if list(k[0] for k in g2) != ["s1"]:
            failures.append("resource attributes (session.id) were not merged into events")
        if "agent.name" not in keys(files):
            failures.append("--keys did not list agent.name")
        empty, _ = summarize([], ["agent"])
        if empty != 0:
            failures.append("an empty selection must report zero events")
    for f in failures:
        print("FAIL:", f)
    print(f"usage_report self-test: {'GREEN' if not failures else 'RED'} ({len(failures)} failure(s))")
    return 1 if failures else 0


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if "--selftest" in argv:
        return selftest()
    directory = pathlib.Path(argv[argv.index("--dir") + 1]) if "--dir" in argv else default_dir()
    files = select_files(argv, directory)
    if not files:
        print(f"no telemetry files under {directory} for {argv or 'today'}: is the receiver running "
              "(otlp_sink.py --status) and telemetry enabled on this machine?")
        return 1
    if "--keys" in argv:
        for k, c in keys(files).most_common():
            print(f"{c:8} {k}")
        return 0
    dims = (argv[argv.index("--by") + 1] if "--by" in argv else "agent,skill,model").split(",")
    bad = [d for d in dims if d not in DIMENSIONS]
    if bad:
        print(f"unknown dimension(s) {bad}; choose from {sorted(DIMENSIONS)}")
        return 2
    n, groups = summarize(files, dims)
    print(render(n, groups, dims, len(files))[0])
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
