#!/usr/bin/env bash
# Cloud-environment setup script TEMPLATE for Claude Code cloud sessions (claude.ai/code, Anthropic-hosted VM).
# Distilled from a production script measured on 2026-09-24. Set the placeholder variables below; replace the commented examples.
#
# WHAT THIS IS
#   * Runs as ROOT on Ubuntu 24.04 x86_64, BEFORE Claude Code launches.
#   * MUST exit 0: a non-zero exit fails the session start. Keep it under about 5 minutes.
#   * Its filesystem result is SNAPSHOTTED and reused by later sessions. It re-runs only when this script or the
#     allowed network hosts change, or after about 7 days. Resuming a session never re-runs it.
#   * The REPO is re-cloned fresh for every session, so anything this script writes INSIDE the clone is lost.
#     Per-clone work (submodules, git-ignored corpora, dependency installs into the tree) belongs in the repo's
#     SessionStart hook. This script's job is to make that hook RUN (see the user-level shim below).
#
# CANONICAL COPY: keep this file in the repo (e.g. scripts/cloud/setup-env.sh). The environment runs only the text
# pasted into its "Setup script" field. Re-paste after every edit (the platform trims the final newline, so to
# verify, hash field+"\n").
#
# NETWORK: set the environment to Custom = the default package-manager list PLUS every host your installers
# download from (list them here). GitHub goes through the separate GitHub proxy, which serves ONLY repositories
# ATTACHED to the session. A private submodule clones only when its repo is attached too.
#     <extra.host.one>     (why it is needed)
#     <extra.host.two>     (why it is needed)

set -uo pipefail          # never -e: one failed optional step must not fail the whole session

# ── Placeholders: set these for your project ──────────────────────────────────────────────────────────────────────
PROJECT="myproject"                       # used for log, cache and shim names
REPO_NAME="myrepo"                        # the clone lands at /home/user/$REPO_NAME
HOOK_REL="scripts/hooks/session_start.py" # the repo's SessionStart hook, relative to the repo root
HOOK_CMD="python"                         # interpreter for the hook (python, bash, node, ...)
PYVER="3.14"                              # the interpreter version your scripts need
PIP_DEPS=""                               # space-separated third-party pip packages, or empty

# Tee everything into the snapshot. The platform shows setup stdout nowhere a session can read it (measured).
SETUP_LOG="/var/log/$PROJECT-setup-env.log"
exec > >(tee "$SETUP_LOG") 2>&1
log() { echo "[setup-env] $*"; }

# ── 1. Package index refresh in the background, in parallel with the big downloads ──────────────────────────────
( export DEBIAN_FRONTEND=noninteractive; apt-get update -qq || log "WARN: apt-get update failed" ) &
APT_PID=$!

# ── 2. Toolchains the image lacks. Pattern: preferred installer, fallback, symlink into /usr/local/bin, log. ───────
install_toolchain() {
  # Example (.NET SDK): vendor install script first, distro package as the fallback.
  #   curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
  #     && bash /tmp/dotnet-install.sh --channel <X.Y> --install-dir /usr/share/dotnet >/tmp/tc.log 2>&1 \
  #     || { wait "$APT_PID"; apt-get install -y -qq <distro-package> >/dev/null; }
  #   ln -sf /usr/share/dotnet/dotnet /usr/local/bin/dotnet
  :
}
install_toolchain || log "WARN: toolchain install failed (tail /tmp/tc.log)"
wait "$APT_PID" 2>/dev/null || true

# ── 3. Interpreters: the image's /usr/local/bin/python{,3} can be OLDER than /usr/bin's and sits ahead of it on PATH
#       (measured: 3.11). Install the version you need and point BOTH names at it. ─────────────────────────────────
PY=""
if python3 -m pip install -q --break-system-packages --root-user-action=ignore uv >/tmp/uv.log 2>&1 \
   && UV_PYTHON_INSTALL_DIR=/opt/uv-python python3 -m uv python install "$PYVER" >>/tmp/uv.log 2>&1; then
  PY=$(UV_PYTHON_INSTALL_DIR=/opt/uv-python python3 -m uv python find --managed-python "$PYVER" 2>/dev/null)
fi
if [ -n "$PY" ]; then
  ln -sf "$PY" /usr/local/bin/python && ln -sf "$PY" /usr/local/bin/python3 && log "python -> $PY"
  if [ -n "$PIP_DEPS" ]; then
    # shellcheck disable=SC2086  # word-splitting PIP_DEPS is intended
    python -m pip install -q --break-system-packages --root-user-action=ignore $PIP_DEPS >/tmp/pip.log 2>&1 \
      && log "pip deps ok" || log "WARN: pip deps failed (tail /tmp/pip.log)"
  fi
else
  log "WARN: python $PYVER not installed (tail /tmp/uv.log)"
fi

# Environment for login shells (the session inherits /etc/profile.d).
cat > "/etc/profile.d/$PROJECT.sh" <<'EOF'
# export TOOL_ROOT=/usr/share/mytool
EOF

# ── 4. Pre-cache large per-clone downloads OUTSIDE the repo (pinned URL + SHA-256). The SessionStart hook copies
#       the file into the fresh clone, so no session downloads it again. ─────────────────────────────────────────
CACHE_DIR="/opt/$PROJECT-cache"
mkdir -p "$CACHE_DIR"
# URL=<https://host/path/file.tar.xz>; SHA=<sha256>; F="$CACHE_DIR/$(basename "$URL")"
# curl -fsSL "$URL" -o "$F.part" && echo "$SHA  $F.part" | sha256sum -c --quiet \
#   && mv "$F.part" "$F" && log "cached $(basename "$F")" || { rm -f "$F.part"; log "WARN: not cached"; }

# ── 5. The USER-LEVEL SessionStart hook shim. With 2+ repos attached the session starts in /home/user (their
#       parent), so NO repo's .claude/settings.json loads and no repo hook fires (measured: "Found 0 total hooks").
#       This hook lives in the VM's ~/.claude/settings.json (part of the snapshot) and runs the repo's own hook
#       only when the project dir is NOT the repo. In the single-repo case the project hook already runs, and the
#       shim must not run it a second time. ──────────────────────────────────────────────────────────────────────
SHIM="/usr/local/bin/$PROJECT-session-start"
# Unquoted heredoc: $REPO_NAME/$HOOK_REL/$HOOK_CMD expand NOW; the escaped \$ ones expand when the shim runs.
cat > "$SHIM" <<EOF
#!/usr/bin/env bash
# User-level SessionStart shim installed by the cloud setup script.
for repo in "\${CLAUDE_PROJECT_DIR:-/home/user}/$REPO_NAME" "/home/user/$REPO_NAME"; do
  [ -f "\$repo/$HOOK_REL" ] || continue
  [ "\$(realpath "\${CLAUDE_PROJECT_DIR:-.}")" = "\$(realpath "\$repo")" ] && exit 0   # project hook runs instead
  exec $HOOK_CMD "\$repo/$HOOK_REL"
done
exit 0
EOF
chmod 755 "$SHIM"

# Merge, never overwrite: the platform may already have written keys to this file.
SHIM="$SHIM" python3 - <<'EOF' && log "user-level SessionStart hook installed" || log "WARN: hook NOT installed"
import json, os, pathlib
p = pathlib.Path(os.path.expanduser("~/.claude/settings.json"))
p.parent.mkdir(parents=True, exist_ok=True)
text = p.read_text(encoding="utf-8") if p.exists() else ""
s = json.loads(text) if text.strip() else {}
entries = s.setdefault("hooks", {}).setdefault("SessionStart", [])
cmd = os.environ["SHIM"]
if not any(h.get("command") == cmd for e in entries for h in e.get("hooks", [])):
    entries.append({"matcher": "startup|resume|clear|compact",
                    "hooks": [{"type": "command", "command": cmd, "timeout": 300}]})
p.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
EOF

# ── 6. Report the versions into the log, so a smoke session can verify them by reading $SETUP_LOG. ─────────────────
log "python: $(python --version 2>&1)"
# log "mytool: $(mytool --version 2>&1 | head -1)"
exit 0

# ── The repo side (SessionStart hook), for reference ─────────────────────────────────────────────────────────────
# In the hook, do the per-clone work only when CLAUDE_CODE_REMOTE=true, and never raise (report failures as context):
#   git submodule update --init --recursive --depth 1   # needs the submodule's repo ATTACHED to the session
#   cp "/opt/$PROJECT-cache/FILE" "$CLAUDE_PROJECT_DIR/IGNORED_DIR/"  &&  run the fetch script (it skips the download)
