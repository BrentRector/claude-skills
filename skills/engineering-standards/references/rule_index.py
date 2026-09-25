#!/usr/bin/env python3
"""Rule index for structural ("drift") tests: one generated view of every rule the test suite enforces, and a per-file
query that answers "which rules govern the file I am about to edit?" BEFORE the edit, not after a red gate.

    python rule_index.py --tests "tests/**/*DriftTests.cs"                 # regenerate the index (default RULES.md)
    python rule_index.py --tests "tests/**/test_*invariant*.py" --check    # CI: exit 1 if stale or a test states no rule
    python rule_index.py --tests "tests/**/*DriftTests.cs" src/foo/Bar.cs  # the rules that govern these files

The rule's single home stays the test that enforces it: its doc comment (C# `/// <summary>`, a Python class/module
docstring, a JS/TS `/** ... */` block before the first describe/class). This script only DERIVES the index and the query
from the tests, so there is never a second copy of a rule to drift.

A file is governed SPECIFICALLY by a test when the test names that file or a directory at least --depth segments deep
above it (as a repo-relative string literal, or as path segments passed to a helper named with --path-helper), or when
the test's rule text names the file's basename. A test that scans only a whole top-level tree above it is listed
separately as a TREE-WIDE SWEEP.

Options:
  --tests GLOB          repo-relative glob of the structural tests (repeatable)
  --root DIR            repository root (default: the git top level, else the current directory)
  --out FILE            index path, repo-relative (default RULES.md)
  --depth N             segments a scanned path needs to count as specific (default 3)
  --path-helper REGEX   a call whose quoted string arguments are path segments, with a capture group for the base
                        directory it maps to, e.g. 'Paths\\.(src|tests|docs)\\(' (repeatable; optional)
  --check               do not write; exit 1 when the index is stale or any test states no rule
"""
import argparse
import glob
import pathlib
import re
import subprocess
import sys

DOC_PATTERNS = [
    # C#: the first XML <summary>, which may close on the same line as its text
    re.compile(r"///\s*<summary>(.*?)</summary>", re.S),
    # Python: a class or module docstring
    re.compile(r'(?:^|\n)\s*(?:class\s+\w+[^:]*:\s*)?("""|\'\'\')(.*?)\1', re.S),
    # JS/TS/Java/Kotlin/Go-style block comment before the first describe/class/test/func
    re.compile(r"/\*\*(.*?)\*/\s*(?:export\s+)?(?:describe|class|test|func|public|internal|object)\b", re.S),
]
XML_REF = re.compile(r'<(?:see|seealso)\s+(?:cref|langword|href)="(?:[A-Z]:)?([^"]+)"\s*/>')
XML_NAME = re.compile(r'<(?:paramref|typeparamref)\s+name="([^"]+)"\s*/>')
TAG = re.compile(r"<[^>]+>")


def repo_root(arg):
    if arg:
        return pathlib.Path(arg).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return pathlib.Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return pathlib.Path.cwd().resolve()


def rule_of(text):
    for pat in DOC_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        body = m.group(m.lastindex)
        body = re.sub(r"(?m)^\s*(///|\*|#)\s?", " ", body)
        body = XML_REF.sub(lambda c: c.group(1).split("(")[0].split(".")[-1], body)
        body = XML_NAME.sub(lambda c: c.group(1), body)
        body = TAG.sub("", body).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            continue
        cut = re.search(r"(?<=[.!?])\s", body[60:])
        body = body[: 60 + cut.start()] if cut else body
        return body[:400] + ("…" if len(body) > 400 else "")
    return ""


def paths_of(text, top_dirs, helpers):
    seen = []
    literal = re.compile(r'["\']((?:' + "|".join(map(re.escape, top_dirs)) + r')/[^"\'\s{}*]+)["\']') if top_dirs else None
    for h in helpers:
        for m in re.finditer(h + r"([^()]*)\)", text):
            # the helper's captured name is the directory it maps to; helper names are conventionally the directory
            # name in another case (Src -> src), so compare lower-cased
            base = m.group(1).lower() if m.re.groups >= 2 else ""
            args = m.group(m.re.groups)
            segs = re.findall(r'["\']([^"\']+)["\']', args)
            p = "/".join(([base] if base else []) + segs).strip("/")
            if p and p not in seen:
                seen.append(p)
    if literal:
        for lit in literal.findall(text):
            lit = lit.rstrip("/.,;:")
            if lit not in seen:
                seen.append(lit)
    return seen


def index(root, globs, helpers):
    top_dirs = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")] + [".github"]
    files = sorted({pathlib.Path(p).resolve() for g in globs for p in glob.glob(str(root / g), recursive=True)})
    rows = []
    for f in files:
        parts = set(f.relative_to(root).parts)
        if parts & {"bin", "obj", "node_modules", "__pycache__", "dist", "build"}:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        rows.append({"test": f.stem, "file": f.relative_to(root).as_posix(), "rule": rule_of(text),
                     "paths": paths_of(text, top_dirs, helpers)})
    return rows


def render(rows, generator):
    out = ["# Structural rules — generated index", "",
           f"<!-- GENERATED by {generator} — do not edit by hand; CI fails when it is stale. -->", "",
           "Every structural test enforces one rule, and that rule's single home is the test's doc comment. This page is",
           "derived from them. **Before editing a file, ask which rules govern it** (run the generator with the file path).",
           "", f"{len(rows)} rule tests.", "", "| Test | Rule | Scans |", "|---|---|---|"]
    for r in rows:
        rule = r["rule"].replace("|", "\\|") or "⚠ no doc comment — the rule is unwritten"
        scans = ", ".join(f"`{p}`" for p in r["paths"][:6]) + (" …" if len(r["paths"]) > 6 else "")
        out.append(f"| [{r['test']}]({r['file']}) | {rule} | {scans or '—'} |")
    return "\n".join(out) + "\n"


def governing(root, rows, target, depth):
    t = pathlib.Path(target)
    t = (t if t.is_absolute() else pathlib.Path.cwd() / t).resolve()
    try:
        rel = t.relative_to(root).as_posix()
    except ValueError:
        rel = pathlib.PurePosixPath(target).as_posix()
    base, stem = pathlib.PurePosixPath(rel).name, pathlib.PurePosixPath(rel).stem
    specific, sweeps = [], []
    for r in rows:
        under = [p for p in r["paths"] if rel == p or rel.startswith(p.rstrip("/") + "/")]
        deep = any(p == rel or len(p.split("/")) >= depth for p in under)
        named = len(stem) > 3 and re.search(r"\b" + re.escape(stem) + r"\b", r["rule"]) is not None
        if deep or named or base == pathlib.PurePosixPath(r["file"]).name:
            specific.append(r)
        elif under:
            sweeps.append(r)
    return rel, specific, sweeps


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--tests", action="append", required=True)
    ap.add_argument("--root")
    ap.add_argument("--out", default="RULES.md")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--path-helper", action="append", default=[])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = repo_root(a.root)
    rows = index(root, a.tests, a.path_helper)
    text = render(rows, "rule_index.py")
    out = root / a.out
    if a.targets:
        for target in a.targets:
            rel, specific, sweeps = governing(root, rows, target, a.depth)
            print(f"== {rel}: {len(specific)} specific rule(s)")
            for r in specific:
                print(f"  {r['test']}  ({r['file']})\n    {r['rule'] or '(no doc comment — read the test)'}")
            if sweeps:
                print(f"  + {len(sweeps)} tree-wide sweep(s) also scan it: " + ", ".join(r["test"] for r in sweeps))
        return 0
    if a.check:
        if not rows:
            print("no rule tests matched --tests: the index would be empty (a filter that matched nothing is a red)")
            return 1
        stale = (out.read_text(encoding="utf-8") if out.exists() else "") != text
        unwritten = [r["test"] for r in rows if not r["rule"]]
        if stale:
            print(f"{a.out} is STALE — regenerate it ({len(rows)} rule tests)")
        if unwritten:
            print(f"{len(unwritten)} rule test(s) state no rule — add a doc comment: {', '.join(unwritten)}")
        if stale or unwritten:
            return 1
        print(f"{a.out} current — {len(rows)} rule tests, every one with its rule")
        return 0
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {a.out} — {len(rows)} rule tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
