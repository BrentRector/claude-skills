#!/usr/bin/env python3
"""orient.py — ONE-CALL ORIENTATION for the source files an implementer is about to change.

Every wave, implementers re-derive the same facts about the same files: where the entry points are, which helper
already owns a rule, which tests exercise the file, what the last fix there changed. This prints all of it in one
call, derived fresh from the tree, the issue notes and git, so it never goes stale and there is nothing to maintain.

    python orient.py src/Parser/Lexer.cs
    python orient.py src/a.py src/b.py --notes docs/issues --tests tests --cite "RFC\\s?\\d+|§\\s?\\d+(?:\\.\\d+)+"

Per file it prints:
  OUTLINE   types and top-level functions/methods with line numbers (read the right 80 lines, not the whole file)
  CITES     spec/requirement references found in the file, by count (--cite is the pattern; off when omitted)
  TESTS     test files that name the file's main type/module, by hit count (the gate filter to start from)
  LEARNED   closed notes (--closed-status, default landed/done/closed/fixed) that name the file, newest first, with
            the sentences they say ABOUT this file: code sites, mechanisms, traps. This is what earlier
            implementers learned, and nothing else carries it forward.
  OPEN      open notes that name the file (the rest of its cluster; see fix_clusters.py)
  HISTORY   the last commits that touched it

Notes are Markdown files with front matter (`id:`, `status:`, `title:`), one per issue, in --notes.
Supported outlines: C#, Java, Kotlin, TypeScript/JavaScript, Python, Go, Rust (by extension; others get none).
"""
import argparse, collections, pathlib, re, subprocess, sys

OUTLINE = {
    (".cs", ".java", ".kt"): re.compile(
        r"^\s*(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|override|virtual|"
        r"async|final|open|data|suspend|fun)\s+)*(class|record|struct|interface|enum|object|[\w<>\[\],.? ]+?)\s+"
        r"([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*(\(|:|\{|$|where\b|=>)"),
    (".ts", ".tsx", ".js", ".jsx", ".mjs"): re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(class|interface|type|enum|function)\s+([A-Za-z_$][\w$]*)"),
    (".py",): re.compile(r"^(\s*)(class|def|async def)\s+([A-Za-z_]\w*)"),
    (".go",): re.compile(r"^(func|type)\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"),
    (".rs",): re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(fn|struct|enum|trait|impl|mod)\s+([A-Za-z_]\w*)"),
}
KEYWORDS = {"if", "for", "foreach", "while", "switch", "catch", "using", "return", "new", "else", "lock"}


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def outline(path, lines, limit=60):
    rx = next((r for exts, r in OUTLINE.items() if path.suffix in exts), None)
    if rx is None:
        return ["  (no outline for this file type)"]
    out = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith(("//", "#", "*", "/*")):
            continue
        m = rx.match(line)
        if not m:
            continue
        if path.suffix == ".py":
            out.append(f"  {i:5}  {m.group(1)}{m.group(2)} {m.group(3)}")
        elif path.suffix in (".cs", ".java", ".kt"):
            kind, name = m.group(1).strip(), m.group(2)
            if name in KEYWORDS:
                continue
            if kind in ("class", "record", "struct", "interface", "enum", "object"):
                out.append(f"  {i:5}  {kind} {name}")
            elif m.group(3) == "(" and len(line) - len(line.lstrip()) <= 8:
                out.append(f"  {i:5}    {name}(")
        else:
            out.append(f"  {i:5}  {m.group(1)} {m.group(2)}")
    return out[:limit] + ([f"  … {len(out) - limit} more"] if len(out) > limit else [])


def fix_section(body):
    for head in ("## Landing", "## Fix", "## Resolution", "**Fix.**", "## Retired"):
        i = body.find(head)
        if i >= 0:
            return body[i:].split("\n\n## ", 1)[0]
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--notes", default="", help="directory of issue notes (*.md with front matter)")
    ap.add_argument("--tests", default="tests", help="test root (default: tests)")
    ap.add_argument("--cite", default="", help="regex for spec/requirement references to count")
    ap.add_argument("--open-status", default="open")
    ap.add_argument("--closed-status", default="landed,done,closed,fixed,retired")
    ap.add_argument("--landed", type=int, default=6)
    ap.add_argument("--commits", type=int, default=6)
    a = ap.parse_args()
    closed = set(s.strip() for s in a.closed_status.split(","))
    notes = []
    if a.notes:
        for p in pathlib.Path(a.notes).glob("*.md"):
            t = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            notes.append((frontmatter(t), t))
    tests = {}
    troot = pathlib.Path(a.tests)
    if troot.exists():
        for p in troot.rglob("*"):
            if p.is_file() and p.suffix in {s for exts in OUTLINE for s in exts} and not any(
                    x in p.parts for x in ("bin", "obj", "node_modules", ".git", "__pycache__")):
                tests[p] = p.read_text(encoding="utf-8", errors="replace")
    cite = re.compile(a.cite) if a.cite else None

    for f in a.files:
        path = pathlib.Path(f)
        if not path.exists():
            print(f"== {f}: not found"); continue
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        base = path.name.split(".")[0]
        print(f"\n{'=' * 100}\n== {f}  ({len(lines)} lines)")
        print("-- OUTLINE"); print("\n".join(outline(path, lines)))
        if cite:
            c = collections.Counter(m.group(0) for l in lines for m in cite.finditer(l))
            print("-- CITES: " + ", ".join(f"{k}×{n}" for k, n in c.most_common(14)))
        hits = sorted(((t.count(base), p) for p, t in tests.items() if base in t), key=lambda x: -x[0])[:8]
        print(f"-- TESTS naming {base}: " + ", ".join(f"{p.name}({n})" for n, p in hits))
        names = [n for n in (f, path.name, base) if len(n) > 5]
        done, open_ = [], []
        for fm, t in notes:
            if any(n in t for n in names):
                (done if fm.get("status") in closed else open_ if fm.get("status") == a.open_status else []) \
                    .append((fm, t))
        if a.notes:
            print(f"-- LEARNED (closed notes naming the file: {len(done)})")
            for fm, t in sorted(done, key=lambda x: x[0].get("id", ""), reverse=True)[:a.landed]:
                print(f"   {fm.get('id', '?')}: {fm.get('title', '')[:140]}")
                body = t.split("\n---\n", 1)[-1]
                said, seen = re.split(r"(?<=[.;])\s+|\n", fix_section(body) + "\n" + body), set()
                for s in (s.strip() for s in said):
                    if len(s) > 30 and any(n in s for n in names) and s not in seen:
                        seen.add(s)
                        print("      · " + s[:200])
                        if len(seen) >= 4:
                            break
            print(f"-- OPEN notes naming the file ({len(open_)}): " + ", ".join(fm.get("id", "?") for fm, _ in open_)[:600])
        log = subprocess.run(["git", "log", f"-{a.commits}", "--format=%h %ad %s", "--date=short", "--", f],
                             capture_output=True, text=True, encoding="utf-8").stdout.strip()
        print("-- HISTORY\n" + "\n".join("   " + l[:150] for l in log.split("\n") if l))
    return 0


if __name__ == "__main__":
    sys.exit(main())
