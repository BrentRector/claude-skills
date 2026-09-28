#!/usr/bin/env python3
"""devlog.py — write, check and search a development log that agents keep as the project's memory.

Two layouts are supported, and the script tells them apart by what `--log` names:

  a FILE     one Markdown file, NEWEST ENTRY FIRST. Each entry starts at a line
                 ## Entry NNN — YYYY-MM-DD HH:MM TZ — Title
             Anything above the first entry (a title, an ordering note) is preamble and is never touched.
  a DIRECTORY  one file per entry, named NNNN-YYYY-MM-DD-slug.md, whose first line is
                 # NNNN — YYYY-MM-DD HH:MM TZ — Title

Subcommands:

  new     add the next entry. Its number is the newest number + 1, its time comes from the system clock (never from
          the caller), and a single-file log keeps its own line endings (CRLF stays CRLF). It refuses a number that
          is not top + 1 or that already exists.
            devlog.py new --title "Retry lock removed" --body-file entry.md
            devlog.py new --body-file entry.md          (the file's first line is the title)
            devlog.py new --title "..."                 (writes a Context / Tried / Result / Lesson / Next skeleton)
  check   validate the numbering (unique; descending in a single file), the header format and every timestamp.
          --from N checks only entries numbered N and later, for logs whose early entries predate the rules.
  search  print the entries matching a regular expression, with their headers ("have we tried this before?").
            devlog.py search -i "retry (lock|timer)"

The log path comes from --log, else from `.devlog.json` ({"log": "DEVLOG.md", "check_from": 512}) at the git
root or the current directory, else DEVLOG.md. Standard library only. `--self-test` exercises every branch.

Why the details:
  * The insertion point is the first LINE-START `## Entry <digits>`. A search for the plain text `## Entry ` finds the
    format example quoted in the ordering note first and splices the entry into the middle of the note.
  * The file is read and written as BYTES. A text-mode rewrite of a CRLF log converts every line and turns a
    50-line entry into a whole-file diff.
  * The timestamp is read here, from the clock. Agents asked to "stamp the time" estimate it, and estimates were
    caught wrong twice in one day.
"""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, tempfile

DASH = "—"
SEP = r"\s+[—-]\s+"
STAMP_RE = r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) ([A-Za-z][A-Za-z0-9_+\-:]*|[+-]\d{2}:?\d{2})"
FILE_HDR = re.compile(rb"(?m)^## Entry (\d+)\b[^\r\n]*")
FILE_HDR_FULL = re.compile(r"^## Entry (\d+)" + SEP + STAMP_RE + SEP + r"(\S.*)$")
DIR_NAME = re.compile(r"^(\d{3,})-(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]*)\.md$")
DIR_HDR_FULL = re.compile(r"^# (\d+)" + SEP + STAMP_RE + SEP + r"(\S.*)$")
DIR_HDR_NUM = re.compile(r"^# (\d+)\b")
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
        return t.strftime("%Y-%m-%d %H:%M") + " UTC", t
    t = t.astimezone()
    return t.strftime("%Y-%m-%d %H:%M") + " " + tz_abbrev(t.tzname(), t.utcoffset()), t


def valid_stamp(date, time):
    try:
        datetime.datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- config

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
            unknown = set(data) - {"log", "check_from"}
            if unknown:
                raise Refused(f"{cfg}: unknown key(s) {sorted(unknown)}")
            return d, data
    return None, {}


def resolve_log(arg, cwd="."):
    root, cfg = find_config(cwd)
    if arg:
        return pathlib.Path(arg), cfg
    if "log" in cfg:
        return root / cfg["log"], cfg
    return pathlib.Path(cwd) / "DEVLOG.md", cfg


# ---------------------------------------------------------------- single-file layout

def eol_of(data):
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    return b"\r\n" if crlf > lf else b"\n"


def file_entries(data):
    """[(number, start, end, header_text)] in file order."""
    ms = list(FILE_HDR.finditer(data))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(data)
        out.append((int(m.group(1)), m.start(), end, m.group(0).decode("utf-8", "replace")))
    return out


def next_number(existing_numbers, top, requested):
    want = top + 1
    if requested is not None and requested != want:
        raise Refused(f"refused: the newest entry is {top}, so the next is {want}, not {requested}")
    if want in existing_numbers:
        raise Refused(f"refused: entry {want} already exists (the log is out of order; run `check`)")
    return want


def new_in_file(path, title, body, number=None, utc=False, clock=None):
    data = path.read_bytes() if path.exists() else b""
    entries = file_entries(data)
    top = entries[0][0] if entries else 0
    n = next_number({e[0] for e in entries}, top, number)
    stamp, _ = now_stamp(utc, clock)
    text = f"## Entry {n} {DASH} {stamp} {DASH} {title}\n\n{body.strip()}\n\n"
    eol = eol_of(data) if data else b"\n"
    block = text.replace("\r\n", "\n").encode("utf-8").replace(b"\n", eol)
    if entries:
        at = entries[0][1]
        out = data[:at] + block + data[at:]
    else:
        sep = b"" if not data or data.endswith(eol + eol) else (eol if data.endswith(eol) else eol + eol)
        out = data + sep + block
    path.write_bytes(out)
    return n, stamp


# ---------------------------------------------------------------- directory layout

def dir_entries(path):
    out = []
    for f in sorted(path.iterdir()):
        m = DIR_NAME.match(f.name)
        if m:
            out.append((int(m.group(1)), f, m))
    return out


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:60].rstrip("-")) or "entry"


def new_in_dir(path, title, body, number=None, utc=False, clock=None):
    entries = dir_entries(path)
    nums = [e[0] for e in entries]
    top = max(nums) if nums else 0
    n = next_number(set(nums), top, number)
    stamp, t = now_stamp(utc, clock)
    width = max([4] + [len(e[2].group(1)) for e in entries])
    num = str(n).zfill(width)
    eol = eol_of(max(entries, key=lambda e: e[0])[1].read_bytes()) if entries else b"\n"
    f = path / f"{num}-{t.strftime('%Y-%m-%d')}-{slugify(title)}.md"
    text = f"# {num} {DASH} {stamp} {DASH} {title}\n\n{body.strip()}\n"
    f.write_bytes(text.replace("\r\n", "\n").encode("utf-8").replace(b"\n", eol))
    return n, stamp, f


# ---------------------------------------------------------------- check

def check(path, since=0):
    problems = []
    if path.is_dir():
        entries = dir_entries(path)
        seen = {}
        for n, f, m in entries:
            if n < since:
                continue
            if n in seen:
                problems.append(f"{f.name}: number {n} also used by {seen[n]}")
            seen[n] = f.name
            if not valid_stamp(m.group(2), "00:00"):
                problems.append(f"{f.name}: the date in the file name does not parse")
            first = f.read_bytes().decode("utf-8", "replace").lstrip("﻿").splitlines()[:1]
            first = first[0] if first else ""
            hm = DIR_HDR_NUM.match(first)
            if not hm:
                problems.append(f"{f.name}: first line is not '# {m.group(1)} {DASH} ...'")
            elif int(hm.group(1)) != n:
                problems.append(f"{f.name}: header says {hm.group(1)}, file name says {n}")
            else:
                full = DIR_HDR_FULL.match(first)
                if not full:
                    problems.append(f"{f.name}: header is not '# NNNN {DASH} YYYY-MM-DD HH:MM TZ {DASH} Title'")
                elif not valid_stamp(full.group(2), full.group(3)):
                    problems.append(f"{f.name}: timestamp '{full.group(2)} {full.group(3)}' does not parse")
        for f in path.iterdir():
            if f.suffix == ".md" and not DIR_NAME.match(f.name) and f.name.lower() not in ("readme.md", "index.md"):
                problems.append(f"{f.name}: not named NNNN-YYYY-MM-DD-slug.md")
        return problems, len(entries)
    entries = file_entries(path.read_bytes())
    prev = None
    seen = set()
    for n, _, _, hdr in entries:
        if n < since:
            prev = n
            continue
        if n in seen:
            problems.append(f"Entry {n}: duplicate number")
        elif prev is not None and n >= prev and prev >= since:
            problems.append(f"Entry {n}: not descending (follows {prev}); newest entries go at the top")
        seen.add(n)
        prev = n
        full = FILE_HDR_FULL.match(hdr.rstrip("\r"))
        if not full:
            problems.append(f"Entry {n}: header is not '## Entry NNN {DASH} YYYY-MM-DD HH:MM TZ {DASH} Title'")
        elif not valid_stamp(full.group(2), full.group(3)):
            problems.append(f"Entry {n}: timestamp '{full.group(2)} {full.group(3)}' does not parse")
    return problems, len(entries)


# ---------------------------------------------------------------- search

def search(path, pattern, ignore_case=False, full=False, out=sys.stdout):
    rx = re.compile(pattern, re.I if ignore_case else 0)
    if path.is_dir():
        items = [(f.name, f.read_bytes().decode("utf-8", "replace")) for _, f, _ in
                 sorted(dir_entries(path), key=lambda e: -e[0])]
    else:
        data = path.read_bytes()
        items = [(None, data[s:e].decode("utf-8", "replace")) for _, s, e, _ in file_entries(data)]
    hits = 0
    for name, text in items:
        lines = text.replace("\r\n", "\n").split("\n")
        matched = [ln for ln in lines[1:] if rx.search(ln)]
        if not matched and not rx.search(lines[0]):
            continue
        hits += 1
        out.write((f"{name}: " if name else "") + lines[0] + "\n")
        if full:
            out.write("\n".join(lines[1:]).rstrip() + "\n\n")
        else:
            for ln in matched:
                out.write("    " + ln.strip()[:200] + "\n")
    return hits


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
    ap.add_argument("--log", help="the log file, or the directory of entry files")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("new", help="add the next entry")
    p.add_argument("--title")
    p.add_argument("--body-file")
    p.add_argument("--stdin", action="store_true", help="read the body from stdin")
    p.add_argument("--number", type=int, help="assert the number you expect (refused unless it is top + 1)")
    p.add_argument("--utc", action="store_true", help="stamp in UTC instead of local time")
    c = sub.add_parser("check", help="validate numbering, headers and timestamps")
    c.add_argument("--from", dest="since", type=int, help="check only entries numbered N and later")
    s = sub.add_parser("search", help="print entries matching a regex")
    s.add_argument("pattern")
    s.add_argument("-i", action="store_true", help="ignore case")
    s.add_argument("--full", action="store_true", help="print whole entries")
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
        path, cfg = resolve_log(args.log)
        if args.cmd == "new":
            title, body = read_body(args)
            if path.is_dir():
                n, stamp, f = new_in_dir(path, title, body, args.number, args.utc)
                print(f"added entry {n} ({stamp}) as {f}")
            else:
                n, stamp = new_in_file(path, title, body, args.number, args.utc)
                print(f"added entry {n} ({stamp}) at the top of {path}")
            return 0
        if not path.exists():
            raise Refused(f"no log at {path}")
        if args.cmd == "check":
            since = args.since if args.since is not None else int(cfg.get("check_from", 0))
            problems, count = check(path, since)
            for pr in problems:
                print("FAIL  " + pr)
            print(f"{count} entries, {len(problems)} problem(s)" + (f" (checked from {since})" if since else ""))
            return 1 if problems else 0
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

    fixed = lambda: datetime.datetime(2026, 3, 4, 17, 5, tzinfo=datetime.timezone(datetime.timedelta(hours=-8), "PST"))
    note = ("# Log\r\n\r\n> **Ordering: newest first.** Headers look like\r\n"
            "> `## Entry NNN — YYYY-MM-DD HH:MM TZ — Title`.\r\n\r\n"
            "## Entry 2 — 2026-03-03 10:00 PST — Second\r\n\r\nbody two retry lock\r\n\r\n"
            "## Entry 1 — 2026-03-02 09:00 PST — First\r\n\r\nbody one\r\n")

    expect("tz: Windows long name abbreviated", tz_abbrev("Pacific Daylight Time", None) == "PDT")
    expect("tz: short name kept", tz_abbrev("CEST", None) == "CEST")
    expect("tz: no name falls back to the offset",
           tz_abbrev("", datetime.timedelta(hours=5, minutes=30)) == "+05:30")
    expect("tz: negative offset", tz_abbrev(None, datetime.timedelta(hours=-3)) == "-03:00")
    expect("clock: stamp comes from the clock", now_stamp(False, fixed)[0].startswith("2026-03-0"))
    expect("clock: --utc", now_stamp(True, fixed)[0] == "2026-03-05 01:05 UTC")
    expect("stamp: bad time rejected", not valid_stamp("2026-02-30", "10:00"))

    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        log = d / "DEVLOG.md"
        log.write_bytes(note.encode("utf-8"))
        before = log.read_bytes()
        n, _ = new_in_file(log, "Third", "tried x\nresult y", utc=True, clock=fixed)
        after = log.read_bytes()
        expect("file/new: number is top + 1", n == 3)
        expect("file/new: inserted above the newest entry, not inside the ordering note",
               after.index(b"## Entry 3") < after.index(b"## Entry 2") and
               after.index(b"## Entry 3") > after.index(b"Title`."))
        expect("file/new: CRLF preserved (no bare LF)", after.count(b"\n") == after.count(b"\r\n"))
        expect("file/new: additions only", after.replace(after[after.index(b"## Entry 3"):
                                                         after.index(b"## Entry 2")], b"") == before)
        expect("file/new: header carries the clock stamp",
               b"## Entry 3 \xe2\x80\x94 2026-03-05 01:05 UTC \xe2\x80\x94 Third" in after)
        expect("file/new: --number other than top + 1 refused",
               refused(lambda: new_in_file(log, "x", "y", number=3, clock=fixed)))
        expect("file/new: matching --number accepted", new_in_file(log, "Fourth", "z", number=4, clock=fixed)[0] == 4)
        problems, count = check(log)
        expect("check: clean log passes", problems == [] and count == 4)
        hits = []

        class Sink:
            def write(self, s):
                hits.append(s)
        expect("search: finds an entry by body text", search(log, "retry LOCK", True, out=Sink()) == 1
               and "## Entry 2" in hits[0])
        expect("search: --full prints the body", search(log, "First", full=True, out=Sink()) == 1)
        expect("search: no match returns 0", search(log, "nothing-like-this", out=Sink()) == 0)

        lf = d / "lf.md"
        lf.write_bytes(b"# Log\n\n## Entry 7 \xe2\x80\x94 2026-03-01 08:00 PST \xe2\x80\x94 Seven\n\nbody\n")
        new_in_file(lf, "Eight", "b", clock=fixed)
        expect("file/new: LF log stays LF", b"\r\n" not in lf.read_bytes())
        empty = d / "empty.md"
        empty.write_bytes(b"# Log\n\n> newest first\n")
        expect("file/new: first entry of an empty log is 1", new_in_file(empty, "One", "b", clock=fixed)[0] == 1)
        expect("file/new: appended after the preamble", empty.read_bytes().index(b"## Entry 1") > 10)
        missing = d / "new.md"
        expect("file/new: a missing file is created", new_in_file(missing, "One", "b", clock=fixed)[0] == 1)

        bad = d / "bad.md"
        bad.write_bytes(("## Entry 5 — 2026-03-01 10:00 PST — A\n\n"
                         "## Entry 6 — 2026-13-01 10:00 PST — B\n\n"
                         "## Entry 6 - 2026-03-01 10:00 PST - C\n\n"
                         "## Entry 4 — no stamp here\n\n"
                         "## Entry 2: undated early entry\n").encode("utf-8"))
        problems, _ = check(bad)
        text = "\n".join(problems)
        expect("check: ascending order flagged", "Entry 6: not descending" in text)
        expect("check: bad timestamp flagged", "2026-13-01" in text)
        expect("check: duplicate number flagged", "Entry 6: duplicate" in text)
        expect("check: ASCII dash separator accepted", not any("Entry 6: header" in p for p in problems))
        expect("check: header without a stamp flagged", "Entry 4: header is not" in text)
        expect("check: --from skips older entries", not any("Entry 2" in p for p in check(bad, since=4)[0]))
        dup = d / "dup.md"
        dup.write_bytes(("## Entry 3 — 2026-03-01 10:00 PST — A\n\n"
                         "## Entry 4 — 2026-03-01 10:00 PST — B\n").encode("utf-8"))
        expect("file/new: refused when top + 1 already exists (out-of-order log)",
               refused(lambda: new_in_file(dup, "x", "y", clock=fixed)))

        ed = d / "devlog"
        ed.mkdir()
        (ed / "0001-2026-03-01-start.md").write_bytes(b"# 0001 \xe2\x80\x94 2026-03-01 09:00 PST \xe2\x80\x94 Start\r\n\r\nx\r\n")
        (ed / "0002-2026-03-02-retry-lock.md").write_bytes(b"# 0002 \xe2\x80\x94 2026-03-02 09:00 PST \xe2\x80\x94 Retry lock\r\n\r\nlock added\r\n")
        (ed / "README.md").write_text("index")
        n, stamp, f = new_in_dir(ed, "Shared temp dir, not the lock!", "real cause", clock=fixed)
        expect("dir/new: number is top + 1, zero-padded", n == 3 and f.name.startswith("0003-2026-03-0"))
        expect("dir/new: slug from the title", f.name.endswith("-shared-temp-dir-not-the-lock.md"))
        expect("dir/new: line endings follow the newest file", b"\r\n" in f.read_bytes()
               and f.read_bytes().count(b"\n") == f.read_bytes().count(b"\r\n"))
        expect("dir/new: --number other than top + 1 refused",
               refused(lambda: new_in_dir(ed, "x", "y", number=9, clock=fixed)))
        problems, count = check(ed)
        expect("dir/check: clean directory passes", problems == [] and count == 3)
        expect("dir/search: finds by body", search(ed, "lock", out=Sink()) >= 1)
        (ed / "0003-2026-03-05-dup.md").write_text("# 0004 — 2026-03-05 09:00 PST — Dup\n", encoding="utf-8")
        (ed / "0005-2026-02-31-bad-date.md").write_text("# 0005 — 2026-03-05 25:00 PST — Bad\n", encoding="utf-8")
        (ed / "0006-2026-03-06-bare.md").write_text("# 0006 — Undated\n", encoding="utf-8")
        (ed / "0007-2026-03-06-nohdr.md").write_text("no header\n", encoding="utf-8")
        (ed / "notes.md").write_text("stray", encoding="utf-8")
        text = "\n".join(check(ed)[0])
        expect("dir/check: duplicate number flagged", "number 3 also used" in text)
        expect("dir/check: header/file-name mismatch flagged", "header says 0004" in text)
        expect("dir/check: bad file-name date flagged", "date in the file name" in text)
        expect("dir/check: bad header time flagged", "'2026-03-05 25:00' does not parse" in text)
        expect("dir/check: header without stamp flagged", "0006-2026-03-06-bare.md: header is not" in text)
        expect("dir/check: missing header flagged", "0007-2026-03-06-nohdr.md: first line" in text)
        expect("dir/check: stray file flagged, README exempt", "notes.md" in text and "README" not in text)

        cfgdir = d / "proj"
        cfgdir.mkdir()
        (cfgdir / ".devlog.json").write_text('{"log": "history.md", "check_from": 3}', encoding="utf-8")
        p, cfg = resolve_log(None, cfgdir)
        expect("config: .devlog.json names the log", p.name == "history.md" and cfg["check_from"] == 3)
        expect("config: --log overrides", resolve_log("x.md", cfgdir)[0] == pathlib.Path("x.md"))
        (cfgdir / ".devlog.json").write_text('{"logg": "x"}', encoding="utf-8")
        expect("config: unknown key refused", refused(lambda: resolve_log(None, cfgdir)))
        bare = d / "bare"
        bare.mkdir()
        expect("config: default is DEVLOG.md", resolve_log(None, bare)[0].name == "DEVLOG.md")

        class A:
            pass
        a = A(); a.title = None; a.body_file = str(d / "entry.md"); a.stdin = False
        (d / "entry.md").write_text("# The title\n\nThe body.\n", encoding="utf-8")
        expect("body: first line of --body-file is the title", read_body(a) == ("The title", "The body."))
        a.title = "Given"; (d / "entry.md").write_text("", encoding="utf-8")
        expect("body: empty body gets the skeleton", read_body(a) == ("Given", SKELETON))
        a.title = None
        expect("body: no title refused", refused(lambda: read_body(a)))
        cwd = os.getcwd()
        try:
            os.chdir(d)
            expect("cli: check exits 0 on a clean log", main(["--log", str(log), "check"]) == 0)
            expect("cli: check exits 1 on problems", main(["--log", str(bad), "check"]) == 1)
            expect("cli: search exits 1 with no hit", main(["--log", str(log), "search", "zzzz"]) == 1)
            expect("cli: refused new exits 3", main(["--log", str(log), "new", "--title", "x", "--number", "99"]) == 3)
            expect("cli: missing log exits 3", main(["--log", str(d / "none.md"), "check"]) == 3)
            expect("cli: new exits 0", main(["--log", str(log), "new", "--title", "Via CLI"]) == 0)
            expect("cli: no subcommand prints help", main([]) == 2)
        finally:
            os.chdir(cwd)
    print("=== SELF-TEST: " + ("GREEN" if ok else "RED") + " ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
