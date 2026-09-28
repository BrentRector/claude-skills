#!/usr/bin/env python3
"""orient.py - ONE-CALL ORIENTATION for the source files an implementer is about to change.

Every wave, implementers re-derive the same facts about the same files: where the entry points are, which helper
already owns a rule, which tests exercise the file, what the last fix there changed. This prints all of it in one
call, derived fresh from the tree, the issue notes and git, so it never goes stale and there is nothing to maintain.

    python orient.py src/Parser/Lexer.cs
    python orient.py src/a.py src/b.py --notes docs/issues --tests tests --cite "RFC\\s?\\d+|§\\s?\\d+(?:\\.\\d+)+"

With a `.agent-fleet.json` at the repository root (see fleet_config.py) the flags come from it, and file paths may
be given relative to that root from anywhere inside the repository.

Per file it prints:
  OUTLINE   types and top-level functions/methods with line numbers (read the right 80 lines, not the whole file)
  CITES     spec/requirement references found in the file, by count (--cite is the pattern; off when omitted)
  TESTS     test files that name the file's main type/module, by hit count (the gate filter to start from)
  LEARNED   closed notes (--closed-status, default landed/done/closed/fixed/retired) that name the file, newest
            first, with the sentences they say ABOUT this file: code sites, mechanisms, traps. This is what earlier
            implementers learned, and nothing else carries it forward.
  OPEN      open notes that name the file, oldest first (the rest of its cluster; see fix_clusters.py)
  HISTORY   the last commits that touched it

Notes are Markdown files with front matter (`id:`, `status:`, `title:`), one per issue, in --notes. "Newest" is the
note id in natural order (BUG-9 < BUG-10 < BUG-100), so ids must be allocated in increasing order.
Supported outlines (by extension; other files get none): C#, Java, Kotlin, TypeScript/JavaScript, Python, Go, Rust,
and ANTLR .g4 (rules, modes and the members embedded in its action blocks).
"""
import argparse, collections, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fleet_config  # noqa: E402

_MODS = r"(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|override|virtual|async|" \
        r"unsafe|new|required|file|final|open|data|suspend|fun)\s+)*"
OUTLINE = {
    # C#: members are PascalCase by convention, which keeps locals and calls out of the outline.
    (".cs",): re.compile(r"^\s*" + _MODS + r"(class|record struct|record|struct|interface|enum|[\w<>\[\],.? ]+?)\s+"
                         r"([A-Z]\w*)\s*(?:<[^>]*>)?\s*(\(|:|\{|$|where\b|=>)"),
    (".java", ".kt"): re.compile(r"^\s*" + _MODS + r"(class|record|struct|interface|enum|object|[\w<>\[\],.? ]+?)\s+"
                                 r"([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*(\(|:|\{|$|where\b|=>)"),
    (".ts", ".tsx", ".js", ".jsx", ".mjs"): re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(class|interface|type|enum|function)\s+([A-Za-z_$][\w$]*)"),
    (".py",): re.compile(r"^(\s*)(class|def|async def)\s+([A-Za-z_]\w*)"),
    (".go",): re.compile(r"^(func|type)\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"),
    (".rs",): re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(fn|struct|enum|trait|impl|mod)\s+([A-Za-z_]\w*)"),
}
# ANTLR grammars: rules and modes at column 0, plus the target-language members of @members/@header blocks.
G4_RULE = re.compile(r"^(?:(fragment)\s+)?(mode\s+)?([A-Za-z_]\w*)\s*(?::|;|$)")
G4_NOT_RULES = {"grammar", "lexer", "parser", "options", "tokens", "channels", "import"}
C_FAMILY = (".cs", ".java", ".kt", ".g4")
TYPE_KINDS = ("class", "record", "record struct", "struct", "interface", "enum", "object")
KEYWORDS = {"if", "for", "foreach", "while", "switch", "catch", "using", "return", "new", "else", "lock"}
# Statement lines that look like declarations to a regex (`return Foo(x)`, `throw new Bar(`) in the C family.
STATEMENTS = ("using ", "namespace ", "package ", "import ", "return ", "if ", "else", "var ", "val ", "throw ",
              "await ", "yield ")
ALL_EXTS = {s for exts in OUTLINE for s in exts} | {".g4"}


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def natural(note_id):
    """Sort key: digit runs compare as numbers, so BUG-62 < BUG-485 < BUG-1534 (a string sort puts BUG-62 last)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", note_id or "")]


def outline(path, lines, limit=60):
    rx = OUTLINE[(".java", ".kt")] if path.suffix == ".g4" else \
        next((r for exts, r in OUTLINE.items() if path.suffix in exts), None)
    if rx is None:
        return ["  (no outline for this file type)"]
    out = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith(("//", "#", "*", "/*")):
            continue
        if path.suffix in C_FAMILY and s.startswith(STATEMENTS):
            continue
        g = G4_RULE.match(line) if path.suffix == ".g4" else None
        if g and g.group(3) not in G4_NOT_RULES:
            out.append(f"  {i:5}  {'fragment' if g.group(1) else 'mode' if g.group(2) else 'rule'} {g.group(3)}")
            continue
        m = rx.match(line)
        if not m:
            continue
        if path.suffix == ".py":
            out.append(f"  {i:5}  {m.group(1)}{m.group(2)} {m.group(3)}")
        elif path.suffix in C_FAMILY:
            kind, name = m.group(1).strip(), m.group(2)
            if name in KEYWORDS:
                continue
            if kind in TYPE_KINDS:
                out.append(f"  {i:5}  {kind} {name}")
            elif m.group(3) == "(" and len(line) - len(line.lstrip()) <= 8:
                out.append(f"  {i:5}    {name}(")
        else:
            out.append(f"  {i:5}  {m.group(1)} {m.group(2)}")
    return out[:limit] + ([f"  … {len(out) - limit} more members"] if len(out) > limit else [])


def cites(rx, lines, top=14, per=4):
    """The references in a file, by count. When --cite has a named group `key` (e.g. the clause number), matches are
    counted per key and each key lists its most-cited refinements (the rest of the match, e.g. a rule number):
    `§13.18.38.3×21 (SR2×4, SR3×4, …)`. Otherwise each distinct match is counted on its own."""
    whole, by_key, rest = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    for m in (m for l in lines for m in rx.finditer(l)):
        if "key" in rx.groupindex and m.group("key"):
            k = m.group("key")
            by_key[k] += 1
            tail = (m.group(0)[:m.start("key") - m.start()] + m.group(0)[m.end("key") - m.start():]).strip()
            if tail:
                rest[k][tail] += 1
        else:
            whole[m.group(0)] += 1
    if not by_key:
        return ", ".join(f"{k}×{n}" for k, n in whole.most_common(top))
    out = []
    for k, n in by_key.most_common(top):
        sub = rest[k].most_common(per)
        more = " …" if len(rest[k]) > per else ""
        out.append(f"{k}×{n}" + (" (" + ", ".join(f"{t}×{c}" for t, c in sub) + more + ")" if sub else ""))
    return ", ".join(out)


def fix_section(body):
    for head in ("## Landing", "## Fix", "**Fix.**", "## Retired", "## Resolution"):
        i = body.find(head)
        if i >= 0:
            return "\n".join(l for l in body[i:].split("\n\n## ", 1)[0].split("\n")[:9] if l.strip())
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--notes", default="", help="directory of issue notes (*.md with front matter)")
    ap.add_argument("--notes-glob", default="*.md", help="which files in --notes are notes (default *.md)")
    ap.add_argument("--tests", default="tests", help="test root (default: tests)")
    ap.add_argument("--test-ext", default="", help="test file extensions, comma-separated (default: all outlined)")
    ap.add_argument("--max-tests", type=int, default=8, help="test files to list (default 8)")
    ap.add_argument("--cite", default="", help="regex for spec/requirement references to count")
    ap.add_argument("--open-status", default="open")
    ap.add_argument("--closed-status", default="landed,done,closed,fixed,retired")
    ap.add_argument("--min-name", type=int, default=6,
                    help="shortest file/type name that ties a note to a file (default 6; shorter names over-match)")
    ap.add_argument("--landed", type=int, default=6, help="closed notes to show (default 6)")
    ap.add_argument("--commits", type=int, default=6, help="commits to show (default 6)")
    a, root = fleet_config.apply(ap, argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    base_dir = root or pathlib.Path.cwd()
    closed = {s.strip() for s in a.closed_status.split(",")}
    notes = []
    if a.notes:
        for p in pathlib.Path(a.notes).glob(a.notes_glob):
            t = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            notes.append((frontmatter(t), t))
    test_exts = {e.strip() for e in a.test_ext.split(",") if e.strip()} or ALL_EXTS
    tests = {}
    troot = pathlib.Path(a.tests)
    if troot.exists():
        for p in troot.rglob("*"):
            if p.suffix in test_exts and p.is_file() and not any(
                    x in p.parts for x in ("bin", "obj", "node_modules", ".git", "__pycache__")):
                tests[p] = p.read_text(encoding="utf-8", errors="replace")
    cite = re.compile(a.cite) if a.cite else None

    for f in a.files:
        path = pathlib.Path(f)
        if not path.exists() and root is not None and (root / f).exists():
            path = root / f                    # a root-relative path given from a subdirectory
        path = path.resolve()
        try:
            shown = path.relative_to(base_dir.resolve()).as_posix()
        except ValueError:
            shown = f
        if not path.exists():
            print(f"== {shown}: not found"); continue
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        stem = path.name[: -len(path.suffix)] if path.suffix else path.name   # Parser.Expressions
        base = stem.split(".")[0]                                            # Parser
        print(f"\n{'=' * 100}\n== {shown}  ({len(lines)} lines)")
        print("-- OUTLINE"); print("\n".join(outline(path, lines)))
        if cite:
            print("-- CITES: " + cites(cite, lines))
        hits = sorted(((t.count(base), p) for p, t in tests.items() if base in t),
                      key=lambda x: (x[0], x[1].as_posix()), reverse=True)[:a.max_tests]
        print(f"-- TESTS naming {base}: " + ", ".join(f"{p.name}({n})" for n, p in hits))
        # A note is tied to the file by a name long enough to be specific; once tied, its sentences naming the file
        # OR its type (however short) are what it says about the file.
        said_names = [n for n in dict.fromkeys((path.name, stem, base))]
        tie_names = [n for n in dict.fromkeys((shown, path.name, stem, base)) if len(n) >= a.min_name]
        done, open_ = [], []
        for fm, t in notes:
            if any(n in t for n in tie_names):
                (done if fm.get("status") in closed else open_ if fm.get("status") == a.open_status else []) \
                    .append((fm, t))
        if a.notes:
            print(f"-- LEARNED (closed notes naming the file, newest first: {len(done)})")
            for fm, t in sorted(done, key=lambda x: natural(x[0].get("id")), reverse=True)[:a.landed]:
                print(f"   {fm.get('id', '?')}: {fm.get('title', '')[:150]}")
                body = t.split("\n---\n", 1)[-1]
                said, seen = re.split(r"(?<=[.;])\s+|\n", fix_section(body) + "\n" + body), set()
                for s in (s.strip() for s in said):
                    if len(s) > 30 and any(n in s for n in said_names) and s not in seen:
                        seen.add(s)
                        print("      · " + s[:200])
                        if len(seen) >= 4:
                            break
            open_.sort(key=lambda x: natural(x[0].get("id")))
            print(f"-- OPEN notes naming the file ({len(open_)}): "
                  + ", ".join(fm.get("id", "?") for fm, _ in open_)[:600])
        log = subprocess.run(["git", "-C", str(base_dir), "log", f"-{a.commits}", "--format=%h %ad %s",
                              "--date=short", "--", str(path)],
                             capture_output=True, text=True, encoding="utf-8").stdout.strip()
        print("-- HISTORY\n" + "\n".join("   " + l[:150] for l in log.split("\n") if l))
    return 0


if __name__ == "__main__":
    sys.exit(main())
