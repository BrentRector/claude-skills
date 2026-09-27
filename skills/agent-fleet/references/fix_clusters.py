#!/usr/bin/env python3
"""fix_clusters.py — group open defect notes by the SOURCE FILES their code sites name, so one implementer fixes
every defect in one file (or one small set of related files) in ONE pass: one orientation, one build, one gate.

The input is a directory of issue notes, one Markdown file per item, each starting with YAML-style front matter:

    ---
    id: BUG-123
    status: open
    kind: defect
    wrong_answer: true
    crashes: false
    ---
    ...prose that names code sites: src/Parser/Lexer.cs, Lexer.ReadNumber, TokenBuffer ...

Usage:
    python fix_clusters.py --notes docs/issues --src src --ext .cs,.g4   # several extensions: grammars are code sites too
    python fix_clusters.py --notes docs/issues --src src --ext .py --max 4 --json clusters.json
    python fix_clusters.py ... --harm "wrong_answer=8,crashes=4,rejects_valid_input=2,accepts_invalid_input=1"
    python fix_clusters.py ... --open-status open --kind defect --skip-flag blocked

How it works:
1. Every source file under --src with an --ext extension is indexed by its stem ("Lexer"), and a dotted partial
   file ("Parser.Expressions.cs") by its full stem too; a bare type name resolves to the main file.
2. Each open note is scanned for code sites: explicit paths (weight 3), `Type.Member` or `Type.Partial` (weight 2)
   and bare CamelCase type names that match a source file (weight 1).
3. A note's PRIMARY file is its heaviest site, ties broken toward the file FEWER notes name (the more specific site).
4. Notes sharing a primary file form a cluster. A cluster over --max splits into harm-ranked chunks. A singleton
   whose note also names another cluster's file as a secondary site is absorbed into it, up to --max.
5. Clusters rank by summed harm, so filling slots top-down stays harm-first while each slot carries every
   co-located defect.

It writes nothing but the optional --json file: it is a VIEW of the notes, recomputed on every run, never a
second work list to maintain.
"""
import argparse, collections, json, pathlib, re, sys


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def source_index(src, exts, root):
    idx = collections.defaultdict(list)
    for ext, p in ((e, p) for e in exts for p in src.rglob(f"*{e}")):
        rel = p.relative_to(root).as_posix()
        if any(part in ("bin", "obj", "node_modules", ".git", "__pycache__") for part in p.parts):
            continue
        stem = p.name[: -len(ext)]
        base = stem.split(".")[0]
        if stem == base:
            idx[base].insert(0, rel)
        else:
            idx[stem].append(rel)
            idx[base].append(rel)
    return idx


def sites(text, idx, exts):
    """Code sites a note names. Paths and BARE file names both count (`src/a/Lexer.cs`, `Lexer.cs#ReadNumber`):
    notes often name their site in prose that way, and missing the bare form left half of one campaign's
    'unsited' notes unclusterable although they named their file."""
    c = collections.Counter()
    alt = "|".join(re.escape(e) for e in exts)
    for m in re.finditer(r"[\w./-]+(?:" + alt + r")\b", text):
        path = m.group(0).lstrip("./")
        for cands in idx.values():
            for rel in cands:
                if rel.endswith(path) or path.endswith(rel):
                    c[rel] += 3
                    break
            else:
                continue
            break
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)\b", text):
        partial = f"{m.group(1)}.{m.group(2)}"
        if partial in idx and idx[partial] and any(idx[partial][0].endswith(f"/{partial}{e}") for e in exts):
            c[idx[partial][0]] += 2
        elif m.group(1) in idx:
            c[idx[m.group(1)][0]] += 2
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b", text):
        if m.group(1) in idx and len(m.group(1)) > 6:
            c[idx[m.group(1)][0]] += 1
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--notes", required=True, help="directory of issue notes (*.md with front matter)")
    ap.add_argument("--src", required=True, help="source root to resolve code sites against")
    ap.add_argument("--ext", default=".cs", help="source file extension(s), comma-separated (default .cs; e.g. .cs,.g4)")
    ap.add_argument("--max", type=int, default=5, help="cluster size cap (default 5)")
    ap.add_argument("--harm", default="wrong_answer=8,crashes=4,rejects_valid_input=2,accepts_invalid_input=1",
                    help="comma list of front-matter boolean flags and their weights")
    ap.add_argument("--open-status", default="open")
    ap.add_argument("--kind", default="", help="only notes with this kind: value (empty = any)")
    ap.add_argument("--skip-flag", action="append", default=["blocked"],
                    help="front-matter flags that exclude a note when true (repeatable)")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json")
    a = ap.parse_args()

    root = pathlib.Path.cwd()
    src = pathlib.Path(a.src).resolve()
    exts = [e.strip() for e in a.ext.split(",") if e.strip()]
    idx = source_index(src, exts, root if src.is_relative_to(root) else src)
    weights = {k.strip(): int(v) for k, v in (p.split("=") for p in a.harm.split(",") if p)}
    notes = []
    for p in sorted(pathlib.Path(a.notes).glob("*.md")):
        t = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        f = frontmatter(t)
        if f.get("status") != a.open_status or (a.kind and f.get("kind") != a.kind):
            continue
        if any(f.get(s) == "true" for s in a.skip_flag):
            continue
        notes.append({"id": f.get("id", p.stem), "harm": sum(w for k, w in weights.items() if f.get(k) == "true"),
                      "title": f.get("title", "")[:140], "sites": sites(t, idx, exts)})

    popularity = collections.Counter(fl for n in notes for fl in n["sites"])
    unsited = [n for n in notes if not n["sites"]]
    groups = collections.defaultdict(list)
    for n in notes:
        if n["sites"]:
            groups[max(n["sites"], key=lambda fl: (n["sites"][fl], -popularity[fl], fl))].append(n)
    clusters = []
    for fl, ns in groups.items():
        ns.sort(key=lambda n: -n["harm"])
        clusters += [{"file": fl, "notes": ns[i:i + a.max]} for i in range(0, len(ns), a.max)]
    singles = [c for c in clusters if len(c["notes"]) == 1]
    for c in sorted(clusters, key=lambda c: -len(c["notes"])):
        if len(c["notes"]) < 2:
            continue
        for s in singles:
            if len(c["notes"]) >= a.max:
                break
            if s["notes"] and c["file"] in s["notes"][0]["sites"]:
                c["notes"].append(s["notes"].pop())
    clusters = [c for c in clusters if c["notes"]]
    for c in clusters:
        c["harm"] = sum(n["harm"] for n in c["notes"])
    clusters.sort(key=lambda c: (-c["harm"], -len(c["notes"])))

    sizes = collections.Counter(len(c["notes"]) for c in clusters)
    print(f"{len(notes)} open notes -> {len(clusters)} clusters (cap {a.max}); sizes {dict(sorted(sizes.items()))}; "
          f"{len(unsited)} name no resolvable code site")
    for c in clusters[:a.top]:
        print(f"  harm {c['harm']:3} | {c['file']} | " + ", ".join(f"{n['id']}({n['harm']})" for n in c["notes"]))
    if unsited:
        print("  no code site: " + ", ".join(n["id"] for n in unsited[:30]) + (" …" if len(unsited) > 30 else ""))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "clusters": [{"file": c["file"], "harm": c["harm"],
                          "notes": [{k: n[k] for k in ("id", "harm", "title")} for n in c["notes"]]} for c in clusters],
            "unsited": [n["id"] for n in unsited]}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
