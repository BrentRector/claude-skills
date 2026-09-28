"""fleet_config.py - the optional per-repository configuration shared by orient.py, fix_clusters.py and status_delta.py.

A repository that uses these scripts puts its settings in ONE file at its root, so no call site repeats them:

    .agent-fleet.json
    {
      "notes": "docs/issues",            # directory of issue notes (orient, fix_clusters)
      "notes_glob": "*.md",              # which files in it are notes
      "tests": "tests",                  # test root (orient)
      "test_ext": ".cs",                 # which test files to search (orient; default: every outlined language)
      "cite": "RFC\\s?\\d+",             # spec-reference regex to count (orient)
      "open_status": "open",
      "closed_status": "landed,done",    # statuses whose notes carry LEARNED text (orient)
      "min_name": 7,                     # shortest file/type name that ties a note to a file (orient)
      "src": ["src/App.*"],              # source roots, globs allowed (fix_clusters)
      "ext": ".cs,.g4",                  # source extensions (fix_clusters)
      "exclude_dir": ["Generated"],      # directory names never indexed (fix_clusters)
      "harm": "wrong_answer=8,crashes=4",
      "kind": "defect",
      "skip_flag": ["blocked"],
      "base": "origin/main",             # fallback base for an unstamped STATUS.md (status_delta)
      "exclude": [".local-settings.json"]  # paths left out of the uncommitted list (status_delta)
    }

(JSON has no comments; the ones above are for this docstring.) The file is found by walking up from the current
directory, stopping at the repository root. `--config <file>` names one explicitly; `--no-config` ignores it.
Explicit flags always win. Path-valued keys are relative to the file's directory. A key no script accepts is an
error, so a typo cannot silently fall back to a default.
"""
import json
import pathlib

NAME = ".agent-fleet.json"
PATH_KEYS = {"notes", "tests", "src"}
# Every key any of the three scripts accepts. A config key outside this set is refused.
KNOWN = {"notes", "notes_glob", "tests", "test_ext", "cite", "open_status", "closed_status", "min_name", "landed",
         "commits", "max_tests", "src", "ext", "exclude_dir", "harm", "kind", "skip_flag", "max", "top", "base",
         "exclude"}


def find(start=None):
    d = pathlib.Path(start or pathlib.Path.cwd()).resolve()
    for p in (d, *d.parents):
        if (p / NAME).is_file():
            return p / NAME
        if (p / ".git").exists():
            return None
    return None


def load(path):
    path = pathlib.Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: the top level must be an object")
    unknown = sorted(set(data) - KNOWN)
    if unknown:
        raise ValueError(f"{path}: unknown key(s) {unknown}; known: {sorted(KNOWN)}")
    root = path.parent
    out = {}
    for k, v in data.items():
        if k in PATH_KEYS:
            v = [str(root / x) for x in v] if isinstance(v, list) else str(root / v)
        out[k] = v
    return root, out


def apply(ap, argv=None):
    """Parse argv with the config's values as defaults. Returns (args, root): root is the config file's directory
    (the repository root) or None when no config is in use."""
    ap.add_argument("--config", help=f"configuration file (default: the nearest {NAME} up to the repository root)")
    ap.add_argument("--no-config", action="store_true", help=f"ignore any {NAME}")
    pre, _ = ap.parse_known_args(argv)
    path = None if pre.no_config else (pre.config or find())
    if not path:
        return ap.parse_args(argv), None
    try:
        root, cfg = load(path)
    except (OSError, ValueError) as e:
        ap.error(str(e))
    actions = {a.dest: a for a in ap._actions}
    ap.set_defaults(**{k: v for k, v in cfg.items() if k in actions})
    args = ap.parse_args(argv)
    # A repeatable flag given on the command line REPLACES the configured list rather than appending to it.
    for k, v in cfg.items():
        a = actions.get(k)
        if a is not None and a.__class__.__name__ == "_AppendAction" and isinstance(v, list):
            got = getattr(args, k)
            if len(got) > len(v) and got[:len(v)] == v:
                setattr(args, k, got[len(v):])
    return args, root
