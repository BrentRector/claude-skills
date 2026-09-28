#!/usr/bin/env python3
"""fix_clusters.py - group open defect notes by the SOURCE FILES their code sites name, so one implementer fixes
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
    python fix_clusters.py --notes docs/issues --src "src/App.*" --exclude-dir Generated --max 4 --json clusters.json
    python fix_clusters.py ... --harm "wrong_answer=8,crashes=4,rejects_valid_input=2,accepts_invalid_input=1"
    python fix_clusters.py ... --open-status open --kind defect --skip-flag blocked --skip-flag process_only

With a `.agent-fleet.json` at the repository root (see fleet_config.py) the flags come from it.

How it works:
1. Every source file under the --src roots (repeatable; globs allowed, so "src/App.*" leaves a legacy tree out)
   with an --ext extension is indexed by its stem ("Lexer"), and a dotted partial file ("Parser.Expressions.cs") by
   its full stem too; a bare type name resolves to the main file. --exclude-dir names directories never indexed
   (generated code is not a fix site).
2. Each open note is scanned for code sites that resolve to a REAL indexed file: paths and bare file names
   (`src/a/Lexer.cs`, `Lexer.cs#ReadNumber`, weight 3), `Type.Member` or `Type.Partial` (weight 2) and bare
   CamelCase type names that match a source file (weight 1). A path to a file that no longer exists is not a site.
3. A note's PRIMARY file is its heaviest site, ties broken toward the file FEWER notes name (the more specific site).
4. Notes sharing a primary file form a cluster. A cluster over --max splits into harm-ranked chunks. A singleton
   whose note also names another cluster's file as a secondary site is absorbed into it, up to --max; a singleton
   can absorb another singleton the same way (two one-note files that name each other are one pass, not two).
5. Clusters rank by summed harm, so filling slots top-down stays harm-first while each slot carries every
   co-located defect. Each cluster's "files" (in --json) are its primary file plus every file its notes name by
   path or Type.Member: the set the implementer orients on.

It writes nothing but the optional --json file: it is a VIEW of the notes, recomputed on every run, never a
second work list to maintain.
"""
import argparse, collections, glob, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fleet_config  # noqa: E402

ALWAYS_SKIPPED = ("bin", "obj", "node_modules", ".git", "__pycache__")


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).split("\n") if m else []):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def harm_weights(spec):
    """"flag=weight,flag=weight" -> {flag: weight}; raises ValueError naming the bad item."""
    out = {}
    for item in (p.strip() for p in spec.split(",")):
        if not item:
            continue
        k, sep, v = item.partition("=")
        if not sep or not k.strip() or not v.strip().lstrip("-").isdigit():
            raise ValueError(f"bad --harm item {item!r}: expected flag=integer, e.g. wrong_answer=8")
        out[k.strip()] = int(v)
    return out


def source_index(roots, exts, excluded, base_dir):
    """{stem-or-type: [path]}: the main file first for a bare type name; partial files also key on their full stem."""
    idx = collections.defaultdict(list)
    skip = set(ALWAYS_SKIPPED) | set(excluded)
    for ext in exts:
        for root in roots:
            for p in sorted(root.rglob(f"*{ext}")):
                if skip & set(p.relative_to(root).parts[:-1]):
                    continue
                try:
                    rel = p.relative_to(base_dir).as_posix()
                except ValueError:
                    rel = p.as_posix()
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
    for m in re.finditer(r"(?<![\w/.-])([\w./-]*?)([A-Za-z_]\w*(?:\.\w+)*?)(" + alt + r")\b", text):
        prefix, stem, ext = m.group(1), m.group(2), m.group(3)
        path = (prefix + stem + ext).lstrip("./")
        # a real indexed file, matched on a directory boundary (`Lexer.cs` is not `MyLexer.cs`); a bare name that
        # several files share resolves like a bare type name: the main file, else the first indexed
        hit = [r for r in dict.fromkeys(idx.get(stem, [])) if r == path or r.endswith("/" + path)]
        if hit:
            c[hit[0]] += 3
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)\b", text):
        partial = f"{m.group(1)}.{m.group(2)}"
        if partial in idx and idx[partial] and any(idx[partial][0].endswith(f"/{partial}{e}") for e in exts):
            c[idx[partial][0]] += 2              # Parser.Expressions -> that partial file
        elif m.group(1) in idx:
            c[idx[m.group(1)][0]] += 2           # Type.Member -> the type's main file
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b", text):
        if m.group(1) in idx and len(m.group(1)) > 6:
            c[idx[m.group(1)][0]] += 1
    return c


def cluster(notes, cap):
    popularity = collections.Counter(fl for n in notes for fl in n["sites"])
    groups = collections.defaultdict(list)
    for n in notes:
        if n["sites"]:
            groups[max(n["sites"], key=lambda fl: (n["sites"][fl], -popularity[fl], fl))].append(n)
    clusters = []
    for fl, ns in groups.items():
        ns.sort(key=lambda n: -n["harm"])
        clusters += [{"file": fl, "notes": ns[i:i + cap]} for i in range(0, len(ns), cap)]
    # Absorb singletons into a cluster whose file they also name, largest cluster first. A singleton that has
    # absorbed another is a cluster now; one that was absorbed is gone and absorbs nothing.
    singles = [c for c in clusters if len(c["notes"]) == 1]
    for c in sorted(clusters, key=lambda c: -len(c["notes"])):
        if not c["notes"] or len(c["notes"]) >= cap:
            continue
        for s in singles:
            if len(c["notes"]) >= cap:
                break
            if s is not c and len(s["notes"]) == 1 and c["file"] in s["notes"][0]["sites"]:
                c["notes"].append(s["notes"].pop())
    clusters = [c for c in clusters if c["notes"]]
    for c in clusters:
        c["harm"] = sum(n["harm"] for n in c["notes"])
        c["files"] = sorted({fl for n in c["notes"] for fl in n["sites"] if n["sites"][fl] >= 2} | {c["file"]})
    clusters.sort(key=lambda c: (-c["harm"], -len(c["notes"])))
    return clusters


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--notes", help="directory of issue notes (*.md with front matter)")
    ap.add_argument("--notes-glob", default="*.md", help="which files in --notes are notes (default *.md)")
    ap.add_argument("--src", action="append", default=[],
                    help="source root to resolve code sites against (repeatable; globs allowed)")
    ap.add_argument("--ext", default=".cs", help="source file extension(s), comma-separated (default .cs; e.g. .cs,.g4)")
    ap.add_argument("--exclude-dir", action="append", default=[],
                    help="directory name never indexed, e.g. Generated (repeatable; bin/obj/.git always are)")
    ap.add_argument("--max", type=int, default=5, help="cluster size cap (default 5)")
    ap.add_argument("--harm", default="wrong_answer=8,crashes=4,rejects_valid_input=2,accepts_invalid_input=1",
                    help="comma list of front-matter boolean flags and their weights")
    ap.add_argument("--open-status", default="open")
    ap.add_argument("--kind", default="", help="only notes with this kind: value (empty = any)")
    ap.add_argument("--skip-flag", action="append", default=["blocked"],
                    help="front-matter flags that exclude a note when true (repeatable)")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json")
    a, root = fleet_config.apply(ap, argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if not a.notes or not a.src:
        ap.error("--notes and --src are required (on the command line or in .agent-fleet.json)")
    try:
        weights = harm_weights(a.harm)
    except ValueError as e:
        ap.error(str(e))
    if a.max < 1:
        ap.error("--max must be at least 1")

    base_dir = (root or pathlib.Path.cwd()).resolve()
    roots = []
    for s in a.src:
        matched = [pathlib.Path(p).resolve() for p in sorted(glob.glob(s)) if pathlib.Path(p).is_dir()]
        if not matched:
            ap.error(f"--src {s!r} matches no directory")
        roots += matched
    exts = [e.strip() for e in a.ext.split(",") if e.strip()]
    idx = source_index(roots, exts, a.exclude_dir, base_dir)
    notes = []
    for p in sorted(pathlib.Path(a.notes).glob(a.notes_glob)):
        t = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        f = frontmatter(t)
        if f.get("status") != a.open_status or (a.kind and f.get("kind") != a.kind):
            continue
        if any(f.get(s) == "true" for s in a.skip_flag):
            continue
        notes.append({"id": f.get("id", p.stem), "area": f.get("area", ""),
                      "harm": sum(w for k, w in weights.items() if f.get(k) == "true"),
                      "title": f.get("title", "")[:140], "sites": sites(t, idx, exts)})

    unsited = [n for n in notes if not n["sites"]]
    clusters = cluster(notes, a.max)
    sizes = collections.Counter(len(c["notes"]) for c in clusters)
    print(f"{len(notes)} open notes -> {len(clusters)} clusters (cap {a.max}); sizes {dict(sorted(sizes.items()))}; "
          f"{len(unsited)} name no resolvable code site")
    for c in clusters[:a.top]:
        print(f"  harm {c['harm']:3} | {c['file']} | " + ", ".join(f"{n['id']}({n['harm']})" for n in c["notes"]))
    if unsited:
        print("  no code site: " + ", ".join(n["id"] for n in unsited[:30]) + (" …" if len(unsited) > 30 else ""))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "clusters": [{"file": c["file"], "harm": c["harm"], "files": c["files"],
                          "notes": [{k: n[k] for k in ("id", "area", "harm", "title")} for n in c["notes"]]}
                         for c in clusters],
            "unsited": [n["id"] for n in unsited]}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
