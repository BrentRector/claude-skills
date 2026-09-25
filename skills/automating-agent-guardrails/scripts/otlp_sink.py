#!/usr/bin/env python3
"""A local OTLP/HTTP-JSON receiver for Claude Code telemetry. Loopback only, standard library only, no collector.

Claude Code exports telemetry when these are set (per MACHINE, in .claude/settings.local.json `env`; never in the
committed settings, or every clone and cloud session exports to a port nothing listens on):

    CLAUDE_CODE_ENABLE_TELEMETRY=1   OTEL_METRICS_EXPORTER=otlp   OTEL_LOGS_EXPORTER=otlp
    OTEL_EXPORTER_OTLP_PROTOCOL=http/json   OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318

Every POSTed JSON body is appended as one line to <out>/<UTC date>.jsonl. A protobuf body is refused with HTTP 415,
so a wrong OTEL_EXPORTER_OTLP_PROTOCOL fails loudly in the exporter instead of recording nothing readable.
usage_report.py summarizes the files.

    python otlp_sink.py [--port 4318] [--out DIR]    run in the foreground
    python otlp_sink.py --ensure [--port] [--out]    start detached unless something already listens (session start)
    python otlp_sink.py --status [--port]            exit 0 if something listens, else 1
    python otlp_sink.py --stop [--port] [--out]      stop the receiver this script started

Default --out: $CLAUDE_CONFIG_DIR/telemetry, else ~/.claude/telemetry.
"""
import datetime
import http.server
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time

HOST = "127.0.0.1"  # loopback only: telemetry carries prompts' metadata and must not be reachable from the network
DEFAULT_PORT = 4318  # the OTLP/HTTP standard port


def default_out():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(pathlib.Path.home() / ".claude")
    return pathlib.Path(base) / "telemetry"


def listening(port, host=HOST):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def make_handler(out_dir):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server naming
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if "json" not in (self.headers.get("Content-Type") or "").lower():
                self.send_response(415)
                self.end_headers()
                self.wfile.write(b"set OTEL_EXPORTER_OTLP_PROTOCOL=http/json")
                return
            try:
                payload = json.loads(body or b"{}")
            except ValueError:
                payload = {"unparsed_bytes": len(body)}
            now = datetime.datetime.now(datetime.timezone.utc)
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / f"{now:%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"received": now.isoformat(timespec="seconds"), "path": self.path,
                                    "body": payload}, separators=(",", ":")) + "\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):  # no per-request stderr lines
            pass

    return Handler


def serve(port, out_dir):
    server = http.server.ThreadingHTTPServer((HOST, port), make_handler(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    pid_file = out_dir / f"sink-{port}.pid"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    try:
        server.serve_forever()
    finally:
        pid_file.unlink(missing_ok=True)


def ensure(port, out_dir, wait_s=3.0):
    """Start detached unless something already listens. Returns 'running', 'started' or 'failed'."""
    if listening(port):
        return "running"
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, __file__, "--port", str(port), "--out", str(out_dir)], creationflags=flags,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                     start_new_session=(sys.platform != "win32"))
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if listening(port):
            return "started"
        time.sleep(0.1)
    return "failed"


def stop(port, out_dir):
    pid_file = out_dir / f"sink-{port}.pid"
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    pid_file.unlink(missing_ok=True)
    return True


def main(argv):
    def arg(name, default):
        return argv[argv.index(name) + 1] if name in argv else default

    port = int(arg("--port", DEFAULT_PORT))
    out_dir = pathlib.Path(arg("--out", default_out()))
    if "--status" in argv:
        up = listening(port)
        print(f"{HOST}:{port} {'listening' if up else 'not listening'}")
        return 0 if up else 1
    if "--stop" in argv:
        return 0 if stop(port, out_dir) else 1
    if "--ensure" in argv:
        state = ensure(port, out_dir)
        print(f"otlp_sink {HOST}:{port}: {state}")
        return 1 if state == "failed" else 0
    serve(port, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
