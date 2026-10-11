#!/usr/bin/env python3
"""devlog.py — keep a development log as ONE FILE PER ENTRY, numbered at landing, with the newest-first view rendered.

The layout: a directory (default `devlog/`) holding
  pending-<slug>.md   an entry written on a branch, not yet numbered. First line:  ## Entry pending — Title
  NNNN-<slug>.md      a stamped entry.                                  First line:  ## Entry N — YYYY-MM-DD HH:MM TZ — Title
  README.md           optional preamble (the ordering note); never an entry.
Each landing adds exactly one entry file, so two pull requests in a merge queue never touch the same file; the number is
stamped when the branch is ENQUEUED (after its final rebase), so number order is landing order. The single newest-first
document is a VIEW: `render` prints it, and it is never committed.

Subcommands:
  new      write the branch's entry as pending-<slug>.md (no number, no time yet).
             devlog.py new --title "Retry lock removed" --body-file entry.md
             devlog.py new --body-file entry.md          (the file's first line is the title)
  next     print the next free number: newest stamped number + 1, over the directory and, with --base REF, over the
           entries already on that ref (the default branch), so a number in use there is never reused.
  stamp    number the pending entry and stamp its time from the clock: renames pending-<slug>.md to NNNN-<slug>.md and
           completes its header. Run by the enqueue step after the final rebase, before the pull request opens.
             devlog.py stamp --base origin/main          (or --number N from the project's allocator)
  check    validate every entry: file names, headers, timestamps, unique numbers, no carriage return, and no pending
           file (unless --allow-pending). With --base REF it also checks the LANDING: the branch adds at least one
           (with --one: exactly one) stamped entry, adds no pending one, changes or deletes no existing entry (a
           correction is a new entry), and uses no number already on REF. CI runs it on the pull request and on the
           merge group; the enqueue step runs it before it opens the pull request.
  render   print the newest-first view (README.md first). --since N, --out FILE (written LF).
  search   print the entries matching a regular expression ("have we tried this before?").
  migrate  ONE-TIME: split a single newest-first log file into entry files, content-faithfully, LF, verified by
           reading every file back. Then delete the old file (and any insert tool) in the same landing.
             devlog.py migrate --from history.md

Settings come from flags, else `.devlog.json` at the git root or the current directory
({"log": "devlog", "check_from": 1, "base": "origin/main", "width": 4}), else those defaults. Standard library only;
`git` is needed only for --base. `--self-test` exercises every branch.

Why the details:
  * One file per entry: entries inserted at the top of one shared file collide in a merge queue, and every collision
    bounces a pull request.
  * The number is stamped at enqueue, not by the implementer: implementers working in parallel cannot know the landing
    order, and a number taken from a stale snapshot collides.
  * The time is read here, from the clock. Agents asked to "stamp the time" estimate it, and estimates were caught
    wrong twice in one day.
  * Files are written LF. A log whose line endings differ by OS made a Windows gate and a Linux gate test different
    bytes, and once needed a byte-splicing insert tool.
"""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, tempfile

DASH = "—"
SEP = r"\s+[—-]\s+"
STAMP_RE = r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) ([A-Za-z][A-Za-z0-9_+\-:]*|[+-]\d{2}:?\d{2})"
STAMPED_NAME = re.compile(r"^(\d{3,})-([a-z0-9][a-z0-9-]*)\.md$")
PENDING_NAME = re.compile(r"^pending-([a-z0-9][a-z0-9-]*)\.md$")
STAMPED_HDR = re.compile(r"^## Entry (\d+)" + SEP + STAMP_RE + SEP + r"(\S.*)$")
STAMPED_NUM = re.compile(r"^## Entry (\d+)\b")
PENDING_HDR = re.compile(r"^## Entry pending" + SEP + r"(\S.*)$")
SOURCE_HDR = re.compile(r"(?m)^## Entry (\d+)\b[^\n]*")
EXEMPT = {"readme.md", "index.md"}
DEFAULTS = {"log": "devlog", "check_from": 0, "base": "origin/main", "width": 4}
SKELETON = ("**Context.** Why this change, and what state things were in.\n\n"
            "**Tried.** What was done, the alternatives considered, and why this one.\n\n"
            "**Result.** What happened, with the numbers.\n\n"
            "**Lesson.** What the next person (or agent) should know.\n\n"
            "**Next.** What follows from this.\n")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- clock

def tz_abbrev(name, offset):
    """A short zone name. Windows reports 'Pacific Daylight Time'; the log wants 'PDT'."""
    if name and " " not in name.strip() and len(name) <= 6:
        return name.strip()
    if name and " " in name.strip():
        initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", name))
        if 2 <= len(initials) <= 5:
            return initials.upper()
    secs = int(offset.total_seconds()) if offset is not None else 0
    sign = "+" if secs >= 0 else "-"
    secs = abs(secs)
    return f"{sign}{secs // 3600:02d}:{secs % 3600 // 60:02d}"


def now_stamp(utc=False, clock=None):
    t = clock() if clock else datetime.datetime.now(datetime.timezone.utc)
    if utc:
        t = t.astimezone(datetime.timezone.utc)
        return t.strftime("%Y-%m-%d %H:%M") + " UTC"
    t = t.astimezone()
    return t.strftime("%Y-%m-%d %H:%M") + " " + tz_abbrev(t.tzname(), t.utcoffset())


def valid_stamp(date, time):
    try:
        datetime.datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- config and git

def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def find_config(start):
    here = pathlib.Path(start).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True,
                             text=True).stdout.strip()
    except OSError:
        top = ""
    for d in ([pathlib.Path(top)] if top else []) + [here]:
        cfg = d / ".devlog.json"
        if cfg.is_file():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            unknown = set(data) - set(DEFAULTS)
            if unknown:
                raise Refused(f"{cfg}: unknown key(s) {sorted(unknown)}")
            return d, {**DEFAULTS, **data}
    return here, dict(DEFAULTS)


def resolve(arg, cwd="."):
    root, cfg = find_config(cwd)
    path = pathlib.Path(arg) if arg else root / cfg["log"]
    return path, cfg


def need_dir(path):
    if path.is_file():
        raise Refused(f"{path} is a single-file log; split it once with `devlog.py migrate --from {path}`")
    if not path.is_dir():
        raise Refused(f"no log directory at {path}")


# ---------------------------------------------------------------- entries

def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:60].rstrip("-")) or "entry"


def first_line(text):
    lines = text.lstrip("﻿").split("\n", 1)
    return lines[0].rstrip("\r")


def stamped(path):
    """[(number, file)] for every stamped entry file in the directory."""
    out = []
    for f in sorted(path.iterdir()):
        m = STAMPED_NAME.match(f.name)
        if m and f.is_file():
            out.append((int(m.group(1)), f))
    return out


def pending(path):
    return sorted(f for f in path.iterdir() if PENDING_NAME.match(f.name) and f.is_file())


def numbers_at(path, base):
    """Entry numbers present in the log directory on a git ref (the default branch)."""
    top = pathlib.Path(git(path, "rev-parse", "--show-toplevel").strip())
    rel = path.resolve().relative_to(top.resolve()).as_posix()
    names = git(top, "ls-tree", "--name-only", base, rel + "/").split("\n")
    return {int(m.group(1)) for n in names if (m := STAMPED_NAME.match(n.rsplit("/", 1)[-1]))}


def next_number(path, base=None):
    nums = {n for n, _ in stamped(path)} | (numbers_at(path, base) if base else set())
    return max(nums, default=0) + 1


def new_entry(path, title, body):
    f = path / f"pending-{slugify(title)}.md"
    if f.exists():
        raise Refused(f"refused: {f.name} already exists; one entry per landing (edit it, or choose another title)")
    f.write_bytes(f"## Entry pending {DASH} {title}\n\n{body.strip()}\n".replace("\r\n", "\n").encode("utf-8"))
    return f


def stamp(path, number=None, base=None, file=None, width=4, utc=False, clock=None):
    if file:
        f = pathlib.Path(file)
        if not f.is_absolute() and not f.exists():
            f = path / file
    else:
        ps = pending(path)
        if len(ps) != 1:
            raise Refused(f"refused: {len(ps)} pending entries in {path} (a landing carries exactly one; name it with --file)")
        f = ps[0]
    m = PENDING_NAME.match(f.name)
    if not m:
        raise Refused(f"refused: {f.name} is not a pending entry")
    text = f.read_bytes().decode("utf-8").replace("\r\n", "\n")
    hm = PENDING_HDR.match(first_line(text))
    if not hm:
        raise Refused(f"refused: {f.name}'s first line is not '## Entry pending {DASH} Title'")
    used = {n for n, _ in stamped(path)} | (numbers_at(path, base) if base else set())
    n = number if number is not None else max(used, default=0) + 1
    if n in used:
        raise Refused(f"refused: entry number {n} is already in use" + (f" (here or on {base})" if base else ""))
    when = now_stamp(utc, clock)
    rest = text.split("\n", 1)[1] if "\n" in text else "\n"
    out = path / f"{str(n).zfill(width)}-{m.group(1)}.md"
    out.write_bytes((f"## Entry {n} {DASH} {when} {DASH} {hm.group(1)}\n" + rest).encode("utf-8"))
    f.unlink()
    return n, when, out


# ---------------------------------------------------------------- check

def check_dir(path, since=0, allow_pending=False):
    problems = []
    seen = {}
    for f in sorted(path.iterdir()):
        if not f.is_file() or f.suffix != ".md" or f.name.lower() in EXEMPT:
            continue
        data = f.read_bytes()
        if b"\r" in data:
            problems.append(f"{f.name}: contains a carriage return (entry files are LF)")
        text = data.decode("utf-8", "replace")
        if PENDING_NAME.match(f.name):
            if not allow_pending:
                problems.append(f"{f.name}: a pending entry; the enqueue step stamps it (`devlog.py stamp`)")
            if not PENDING_HDR.match(first_line(text)):
                problems.append(f"{f.name}: first line is not '## Entry pending {DASH} Title'")
            continue
        m = STAMPED_NAME.match(f.name)
        if not m:
            problems.append(f"{f.name}: not named NNNN-slug.md or pending-slug.md")
            continue
        n = int(m.group(1))
        if n < since:
            continue
        if n in seen:
            problems.append(f"{f.name}: number {n} also used by {seen[n]}")
        seen[n] = f.name
        line = first_line(text)
        hn = STAMPED_NUM.match(line)
        if not hn:
            problems.append(f"{f.name}: first line is not '## Entry {n} {DASH} ...'")
        elif int(hn.group(1)) != n:
            problems.append(f"{f.name}: header says {hn.group(1)}, file name says {n}")
        else:
            full = STAMPED_HDR.match(line)
            if not full:
                problems.append(f"{f.name}: header is not '## Entry N {DASH} YYYY-MM-DD HH:MM TZ {DASH} Title'")
            elif not valid_stamp(full.group(2), full.group(3)):
                problems.append(f"{f.name}: timestamp '{full.group(2)} {full.group(3)}' does not parse")
    return problems, len(seen)


def check_landing(path, base, one=False):
    """The landing rules over `base...HEAD`: what the pull request (or merge group) does to the log."""
    top = pathlib.Path(git(path, "rev-parse", "--show-toplevel").strip())
    rel = path.resolve().relative_to(top.resolve()).as_posix()
    problems, added = [], []
    for line in git(top, "diff", "--name-status", "--no-renames", f"{base}...HEAD", "--", rel + "/").splitlines():
        status, name = line.split("\t", 1)
        leaf = name.rsplit("/", 1)[-1]
        if leaf.lower() in EXEMPT:
            continue
        if status == "A" and PENDING_NAME.match(leaf):
            problems.append(f"{leaf}: added but not stamped (the enqueue step runs `devlog.py stamp`)")
        elif status == "A" and STAMPED_NAME.match(leaf):
            added.append(int(STAMPED_NAME.match(leaf).group(1)))
        elif status in ("M", "D") and (STAMPED_NAME.match(leaf) or PENDING_NAME.match(leaf)):
            problems.append(f"{leaf}: an existing entry is {'changed' if status == 'M' else 'deleted'}; a correction is a NEW entry")
        elif status == "A":
            problems.append(f"{leaf}: not named NNNN-slug.md")
    if not added:
        problems.append(f"this landing adds no stamped entry to {rel}/ (one entry per landing)")
    elif one and len(added) > 1:
        problems.append(f"this landing adds {len(added)} entries ({sorted(added)}); a landing carries exactly one")
    taken = numbers_at(path, base) & set(added)
    for n in sorted(taken):
        problems.append(f"entry number {n} is already used on {base}; re-stamp with `devlog.py stamp --base {base}`")
    return problems, added


# ---------------------------------------------------------------- render and search

def ordered(path, since=0):
    """Stamped entries, newest first."""
    return [(n, f) for n, f in sorted(stamped(path), key=lambda e: (-e[0], e[1].name)) if n >= since]


def render(path, since=0):
    parts = []
    readme = next((f for f in path.iterdir() if f.name.lower() == "readme.md"), None)
    if readme:
        parts.append(readme.read_bytes().decode("utf-8").replace("\r\n", "\n").rstrip("\n"))
    parts += [f.read_bytes().decode("utf-8").replace("\r\n", "\n").rstrip("\n") for _, f in ordered(path, since)]
    return "\n\n".join(parts) + "\n"


def search(path, pattern, ignore_case=False, full=False, out=sys.stdout):
    rx = re.compile(pattern, re.I if ignore_case else 0)
    hits = 0
    for _, f in ordered(path) + [(None, p) for p in pending(path)]:
        lines = f.read_bytes().decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
        matched = [ln for ln in lines[1:] if rx.search(ln)]
        if not matched and not rx.search(lines[0]):
            continue
        hits += 1
        out.write(f"{f.name}: {lines[0]}\n")
        if full:
            out.write("\n".join(lines[1:]).rstrip() + "\n\n")
        else:
            for ln in matched:
                out.write("    " + ln.strip()[:200] + "\n")
    return hits


# ---------------------------------------------------------------- migrate (one time)

def migrate(source, path, width=4):
    """Split a single newest-first log into entry files; verify by reading every file back."""
    source = pathlib.Path(source)
    if not source.is_file():
        raise Refused(f"no single-file log at {source}")
    path.mkdir(parents=True, exist_ok=True)
    if stamped(path) or pending(path):
        raise Refused(f"refused: {path} already holds entry files; migrate runs once, into an empty directory")
    text = source.read_bytes().decode("utf-8").lstrip("﻿").replace("\r\n", "\n")
    ms = list(SOURCE_HDR.finditer(text))
    if not ms:
        raise Refused(f"refused: no '## Entry N' header in {source}")
    preamble = text[:ms[0].start()].rstrip("\n")
    blocks = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        blocks.append((int(m.group(1)), text[m.start():end].rstrip("\n") + "\n"))
    written = []
    for n, block in blocks:
        head = re.sub(r"^## Entry \d+\s*[—:.-]*\s*", "", block.split("\n", 1)[0])
        head = re.sub(r"^" + STAMP_RE + r"\s*[—-]*\s*", "", head)
        base = f"{str(n).zfill(width)}-{slugify(head)}"
        f, k = path / f"{base}.md", 2
        while f.exists():
            f, k = path / f"{base}-{k}.md", k + 1
        f.write_bytes(block.encode("utf-8"))
        written.append((f, block))
    if preamble:
        (path / "README.md").write_bytes((preamble + "\n").encode("utf-8"))
    # Verify: every file reads back as its source entry (blank lines between entries are not content; the
    # rendered view puts exactly one between entries).
    for f, block in written:
        if f.read_bytes().decode("utf-8") != block:
            raise Refused(f"verification failed: {f.name} does not read back as the source entry")
    return len(written), bool(preamble)


# ---------------------------------------------------------------- CLI

def read_body(args):
    title = args.title
    if args.body_file:
        text = pathlib.Path(args.body_file).read_text(encoding="utf-8-sig")
    elif not sys.stdin.isatty() and args.stdin:
        text = sys.stdin.read()
    else:
        text = ""
    if not title:
        lines = text.lstrip().split("\n", 1)
        title = re.sub(r"^#+\s*", "", lines[0]).strip()
        text = lines[1] if len(lines) > 1 else ""
    if not title:
        raise Refused("refused: no title (pass --title, or put it on the first line of --body-file)")
    return title, (text.strip() or SKELETON)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--log", help="the log directory (default from .devlog.json, else devlog/)")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("new", help="write the branch's pending entry")
    p.add_argument("--title")
    p.add_argument("--body-file")
    p.add_argument("--stdin", action="store_true", help="read the body from stdin")
    x = sub.add_parser("next", help="print the next free entry number")
    x.add_argument("--base", help="also count the entries on this ref (the default branch)")
    s = sub.add_parser("stamp", help="number and time-stamp the pending entry (the enqueue step)")
    s.add_argument("--number", type=int, help="the number allocated by the project (default: next free)")
    s.add_argument("--base", help="never reuse a number present on this ref")
    s.add_argument("--file", help="the pending file, when there is more than one")
    s.add_argument("--utc", action="store_true", help="stamp in UTC instead of local time")
    c = sub.add_parser("check", help="validate the entries; with --base, the landing too")
    c.add_argument("--from", dest="since", type=int, help="check only entries numbered N and later")
    c.add_argument("--base", help="check the landing over BASE...HEAD")
    c.add_argument("--one", action="store_true", help="with --base: exactly one new entry (a single pull request)")
    c.add_argument("--allow-pending", action="store_true", help="a pending entry is not a problem (work in progress)")
    r = sub.add_parser("render", help="print the newest-first view")
    r.add_argument("--since", type=int, default=0)
    r.add_argument("--out")
    q = sub.add_parser("search", help="print entries matching a regex")
    q.add_argument("pattern")
    q.add_argument("-i", action="store_true", help="ignore case")
    q.add_argument("--full", action="store_true", help="print whole entries")
    g = sub.add_parser("migrate", help="ONE-TIME: split a single-file log into entry files")
    g.add_argument("--from", dest="source", required=True)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.cmd:
        ap.print_help()
        return 2
    try:
        path, cfg = resolve(args.log)
        width = int(cfg["width"])
        if args.cmd == "migrate":
            count, pre = migrate(args.source, path, width)
            print(f"migrated {count} entries into {path}" + (" (preamble kept as README.md)" if pre else "") +
                  f"; now delete {args.source} in the same landing")
            return 0
        if args.cmd == "new":
            path.mkdir(parents=True, exist_ok=True)
            title, body = read_body(args)
            print(f"wrote {new_entry(path, title, body)} (numbered at enqueue by `devlog.py stamp`)")
            return 0
        need_dir(path)
        if args.cmd == "next":
            print(next_number(path, args.base))
            return 0
        if args.cmd == "stamp":
            n, when, out = stamp(path, args.number, args.base, args.file, width, args.utc)
            print(f"stamped entry {n} ({when}) as {out}")
            return 0
        if args.cmd == "check":
            since = args.since if args.since is not None else int(cfg["check_from"])
            problems, count = check_dir(path, since, args.allow_pending)
            if args.base:
                more, added = check_landing(path, args.base, args.one)
                problems += more
            for pr in problems:
                print("FAIL  " + pr)
            print(f"{count} entries, {len(problems)} problem(s)" + (f" (checked from {since})" if since else "") +
                  (f"; this landing adds {sorted(added)}" if args.base else ""))
            return 1 if problems else 0
        if args.cmd == "render":
            text = render(path, args.since)
            if args.out:
                pathlib.Path(args.out).write_bytes(text.encode("utf-8"))
                print(f"rendered {len(ordered(path, args.since))} entries to {args.out}")
            else:
                sys.stdout.write(text)
            return 0
        if args.cmd == "search":
            hits = search(path, args.pattern, args.i, args.full)
            print(f"-- {hits} matching entr{'y' if hits == 1 else 'ies'}")
            return 0 if hits else 1
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 3
    return 2


# ---------------------------------------------------------------- self-test

def self_test():
    ok = True

    def expect(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("ok      " if cond else "FAIL    ") + name)

    def refused(fn):
        try:
            fn()
        except Refused:
            return True
        return False

    class Sink:
        def __init__(self):
            self.text = ""

        def write(self, s):
            self.text += s

    fixed = lambda: datetime.datetime(2026, 3, 4, 17, 5, tzinfo=datetime.timezone(datetime.timedelta(hours=-8), "PST"))
    expect("tz: Windows long name abbreviated", tz_abbrev("Pacific Daylight Time", None) == "PDT")
    expect("tz: short name kept", tz_abbrev("CEST", None) == "CEST")
    expect("tz: no name falls back to the offset", tz_abbrev("", datetime.timedelta(hours=5, minutes=30)) == "+05:30")
    expect("tz: negative offset", tz_abbrev(None, datetime.timedelta(hours=-3)) == "-03:00")
    expect("clock: --utc", now_stamp(True, fixed) == "2026-03-05 01:05 UTC")
    expect("stamp: bad time rejected", not valid_stamp("2026-02-30", "10:00"))

    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)

        # --- migrate a CRLF single-file log (with an ordering note quoting the header, and an undated early entry)
        src = d / "history.md"
        src.write_bytes(("# Log\r\n\r\n> **Ordering: newest first.** Headers look like\r\n"
                         "> `## Entry NNN — YYYY-MM-DD HH:MM TZ — Title`.\r\n\r\n"
                         "## Entry 3 — 2026-03-03 10:00 PST — Retry lock\r\n\r\nbody three retry lock\r\n\r\n"
                         "## Entry 2 — 2026-03-02 09:00 PST — Second\r\n\r\nbody two\r\n\r\n\r\n"
                         "## Entry 1: undated early entry\r\n\r\nbody one\r\n").encode("utf-8"))
        log = d / "devlog"
        count, pre = migrate(src, log)
        names = sorted(f.name for f in log.iterdir())
        expect("migrate: one file per entry plus the preamble", count == 3 and pre and
               names == ["0001-undated-early-entry.md", "0002-second.md", "0003-retry-lock.md", "README.md"])
        expect("migrate: entry content kept, LF", (log / "0003-retry-lock.md").read_bytes() ==
               "## Entry 3 — 2026-03-03 10:00 PST — Retry lock\n\nbody three retry lock\n".encode("utf-8"))
        expect("migrate: the ordering note is the README, not an entry", b"Ordering" in (log / "README.md").read_bytes())
        expect("migrate: runs once (refused into a directory with entries)", refused(lambda: migrate(src, log)))
        expect("migrate: a file without entries refused", refused(lambda: migrate(log / "README.md", d / "x")))
        expect("check: migrated log passes from 2 (entry 1 predates the rules)", check_dir(log, since=2)[0] == [])
        expect("check: the undated early entry is flagged without --from",
               any("0001" in p for p in check_dir(log)[0]))

        # --- new, next, stamp
        f = new_entry(log, "Shared temp dir, not the lock!", "real cause")
        expect("new: pending file, no number", f.name == "pending-shared-temp-dir-not-the-lock.md" and
               f.read_bytes().startswith("## Entry pending — Shared temp dir, not the lock!\n".encode("utf-8")))
        expect("new: second entry with the same title refused", refused(lambda: new_entry(log, "Shared temp dir, not the lock!", "x")))
        expect("check: a pending entry is a problem", any("pending" in p for p in check_dir(log, 2)[0]))
        expect("check: --allow-pending accepts it", check_dir(log, 2, allow_pending=True)[0] == [])
        expect("next: newest + 1", next_number(log) == 4)
        expect("stamp: a number in use refused", refused(lambda: stamp(log, number=3, clock=fixed)))
        n, when, out = stamp(log, utc=True, clock=fixed)
        expect("stamp: number, clock time, renamed", n == 4 and out.name == "0004-shared-temp-dir-not-the-lock.md"
               and out.read_bytes().startswith("## Entry 4 — 2026-03-05 01:05 UTC — Shared temp dir, not the lock!\n".encode("utf-8"))
               and not f.exists())
        expect("stamp: body kept", out.read_bytes().endswith(b"\n\nreal cause\n"))
        expect("stamp: nothing pending refused", refused(lambda: stamp(log, clock=fixed)))
        new_entry(log, "A", "a"); new_entry(log, "B", "b")
        expect("stamp: two pending refused without --file", refused(lambda: stamp(log, clock=fixed)))
        expect("stamp: --file picks one", stamp(log, file="pending-a.md", number=9, clock=fixed)[0] == 9)
        (log / "pending-b.md").unlink()
        expect("check: clean after stamping", check_dir(log, 2)[0] == [])

        # --- check catches what a landing must not carry
        bad = d / "bad"
        bad.mkdir()
        (bad / "0005-a.md").write_bytes(("## Entry 5 — 2026-03-01 10:00 PST — A\n").encode("utf-8"))
        (bad / "0005-b.md").write_bytes(("## Entry 5 — 2026-03-01 10:00 PST — B\n").encode("utf-8"))
        (bad / "0006-c.md").write_bytes(("## Entry 7 — 2026-03-01 10:00 PST — C\n").encode("utf-8"))
        (bad / "0008-d.md").write_bytes(("## Entry 8 — 2026-13-01 10:00 PST — D\n").encode("utf-8"))
        (bad / "0009-e.md").write_bytes("## Entry 9 — 2026-03-01 10:00 PST — E\r\n".encode("utf-8"))
        (bad / "0010-f.md").write_bytes(("## Entry 10 — no stamp\n").encode("utf-8"))
        (bad / "notes.md").write_bytes(("stray").encode("utf-8"))
        (bad / "README.md").write_bytes(("preamble").encode("utf-8"))
        text = "\n".join(check_dir(bad)[0])
        expect("check: duplicate number", "number 5 also used" in text)
        expect("check: header/file-name mismatch", "header says 7" in text)
        expect("check: bad timestamp", "2026-13-01" in text)
        expect("check: carriage return", "0009-e.md: contains a carriage return" in text)
        expect("check: header without a stamp", "0010-f.md: header is not" in text)
        expect("check: stray file flagged, README exempt", "notes.md" in text and "README" not in text)

        # --- render and search
        view = render(log, since=0)
        expect("render: preamble first, then newest first",
               view.index("Ordering") < view.index("## Entry 9") < view.index("## Entry 4") < view.index("## Entry 1:"))
        expect("render: --since", "## Entry 2 " not in render(log, since=3))
        sink = Sink()
        expect("search: finds by body text", search(log, "retry LOCK", True, out=sink) == 1 and "0003" in sink.text)
        expect("search: no match returns 0", search(log, "nothing-like-this", out=Sink()) == 0)

        # --- the landing check against a base ref (git)
        repo = d / "repo"
        repo.mkdir()
        run = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, check=True, text=True)
        run("init", "-q", "-b", "main"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        run("config", "core.autocrlf", "false")
        rl = repo / "devlog"
        rl.mkdir()
        (rl / "0001-start.md").write_bytes(("## Entry 1 — 2026-03-01 09:00 PST — Start\n\nx\n").encode("utf-8"))
        run("add", "-A"); run("commit", "-qm", "start")
        run("checkout", "-qb", "fix")
        (repo / "code.txt").write_bytes(("fix").encode("utf-8"))
        run("add", "-A"); run("commit", "-qm", "checkpoint, no entry")
        cwd = os.getcwd()
        try:
            os.chdir(repo)
            expect("landing: no entry is a problem", any("adds no stamped entry" in p for p in check_landing(rl, "main")[0]))
            new_entry(rl, "The fix", "why")
            run("add", "-A"); run("commit", "-qm", "entry")
            expect("landing: a pending entry is a problem", any("not stamped" in p for p in check_landing(rl, "main")[0]))
            run("checkout", "-q", "main")
            (rl / "0002-other.md").write_bytes(("## Entry 2 — 2026-03-02 09:00 PST — Other\n").encode("utf-8"))
            run("add", "-A"); run("commit", "-qm", "another landing took 2")
            run("checkout", "-q", "fix"); run("rebase", "-q", "main")
            expect("next --base: counts the default branch", next_number(rl, "main") == 3)
            expect("stamp --base: a number on the default branch refused",
                   refused(lambda: stamp(rl, number=2, base="main", clock=fixed)))
            n2, _, _ = stamp(rl, base="main", clock=fixed)
            run("add", "-A"); run("commit", "-qm", "stamp")
            problems, added = check_landing(rl, "main", one=True)
            expect("landing: one stamped entry passes", problems == [] and added == [n2] and n2 == 3)
            (rl / "0001-start.md").write_bytes(("## Entry 1 — 2026-03-01 09:00 PST — Start\n\nrewritten\n").encode("utf-8"))
            new_entry(rl, "Second", "x"); stamp(rl, number=4, clock=fixed)
            run("add", "-A"); run("commit", "-qm", "edit old, add second")
            text = "\n".join(check_landing(rl, "main", one=True)[0])
            expect("landing: an edited old entry is a problem", "0001-start.md: an existing entry is changed" in text)
            expect("landing: --one refuses two entries", "adds 2 entries" in text)
            expect("cli: check --base exits 1 on problems", main(["--log", str(rl), "check", "--base", "main"]) == 1)
        finally:
            os.chdir(cwd)

        # --- config and CLI
        cfgdir = d / "proj"
        cfgdir.mkdir()
        (cfgdir / ".devlog.json").write_bytes(('{"log": "history", "check_from": 3}').encode("utf-8"))
        p, cfg = resolve(None, cfgdir)
        expect("config: .devlog.json names the log", p.name == "history" and cfg["check_from"] == 3 and cfg["width"] == 4)
        expect("config: --log overrides", resolve("x", cfgdir)[0] == pathlib.Path("x"))
        (cfgdir / ".devlog.json").write_bytes(('{"logg": "x"}').encode("utf-8"))
        expect("config: unknown key refused", refused(lambda: resolve(None, cfgdir)))
        expect("a single-file log is pointed at migrate", refused(lambda: need_dir(src)))

        class A:
            pass
        a = A(); a.title = None; a.body_file = str(d / "entry.md"); a.stdin = False
        (d / "entry.md").write_bytes(("# The title\n\nThe body.\n").encode("utf-8"))
        expect("body: first line of --body-file is the title", read_body(a) == ("The title", "The body."))
        a.title = "Given"; (d / "entry.md").write_bytes(("").encode("utf-8"))
        expect("body: empty body gets the skeleton", read_body(a) == ("Given", SKELETON))
        a.title = None
        expect("body: no title refused", refused(lambda: read_body(a)))
        try:
            os.chdir(d)
            expect("cli: check exits 0 on a clean log", main(["--log", str(log), "check", "--from", "2"]) == 0)
            expect("cli: check exits 1 on problems", main(["--log", str(bad), "check"]) == 1)
            expect("cli: search exits 1 with no hit", main(["--log", str(log), "search", "zzzz"]) == 1)
            expect("cli: refused stamp exits 3", main(["--log", str(log), "stamp"]) == 3)
            expect("cli: missing log exits 3", main(["--log", str(d / "none"), "check"]) == 3)
            expect("cli: new exits 0", main(["--log", str(log), "new", "--title", "Via CLI"]) == 0)
            expect("cli: next exits 0", main(["--log", str(log), "next"]) == 0)
            expect("cli: render --out writes LF", main(["--log", str(log), "render", "--out", str(d / "v.md")]) == 0
                   and b"\r" not in (d / "v.md").read_bytes())
            expect("cli: no subcommand prints help", main([]) == 2)
        finally:
            os.chdir(cwd)
    print("=== SELF-TEST: " + ("GREEN" if ok else "RED") + " ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
