# Building a citation checker

A citation is a claim: "clause **X** says **'...'**". A checker makes that claim mechanically true or false. It
takes about an hour to build for any standard you have as Markdown or plain text, and it catches the worst
citation failure there is: a real quote attached to the wrong clause number.

## What it must do

**`--check <clause> "<quote>"`.** Resolve the clause id to *that clause's own text*, then assert that the quote
occurs inside it. Exit non-zero otherwise. Only the clause's own region counts. If the quote appears elsewhere
in the document, the check still fails and should say where it does appear. That guarantee is the whole point.

**`--find "<quote>"`.** Report every clause whose own text contains the quote. Use it to repair a citation, or
to find a rule when you only remember its wording.

## Design points

1. **Segment the document by headings.** A clause runs from its heading to the next heading of *any* level. So
   the region for `4.2` excludes the text of `4.2.1`. That is correct: cite the deepest clause that holds the
   text. Keep an option to include subclauses if your standard puts rules under a parent heading.
2. **Recognize every clause-id shape the standard uses.** That means dotted decimals (`7.3.2`), annex forms
   (`A.4`, `Annex B`), and RFC-style `Section 3.1` or `3.1.` headings. Allow headings with no title: glossary
   entries are often a bare number with the term on the next line. A checker that can't resolve an id should
   say "unknown clause", never "quote not found". Those are different failures.
3. **Normalize both sides the same way.** Compare words only. Lowercase, turn punctuation and typographic quotes
   into spaces, collapse whitespace, and **re-join line-break hyphenation** (`imple-\nmentation` becomes
   `implementation`) before stripping punctuation. Also remove Markdown emphasis and escapes (`*`, `_`, `` ` ``,
   `\)`). Dashes, quote styles and line wrapping are typography, not content.
4. **Read the source text, not a derived index.** An extracted rule catalog or JSON index can drop clauses whose
   rules are plain prose, or renumber sub-items. A checker built on it gives confident wrong answers.
5. **Be honest about sub-rule numbering.** A best-effort "rule path" (such as `3) b)`) helps, but nested
   numbering styles vary. If the ordinal matters, read the printed rule.

## Reference implementation (Python, stdlib only)

```python
#!/usr/bin/env python3
"""cite.py - check that a quoted passage occurs in the named clause of a standard.

  cite.py SPEC.md --check 7.3.2 "the receiver MUST ignore"
  cite.py SPEC.md --find "the receiver MUST ignore"
"""
import argparse, re, sys

# Markdown heading or bare numbered line whose first token is a clause id:
#   "## 7.3.2 Title", "### A.4 Title", "## Annex B", "3.1.  Title" (RFC style)
HEADING = re.compile(
    r"^(?:#{1,6}\s+)?(?:Section\s+|Annex\s+)?"
    r"(?P<id>(?:\d+|[A-Z])(?:\.\d+)*)\.?(?=\s|$)(?P<title>.*)$")

def norm(text):
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)   # re-join hyphenation
    text = re.sub(r"\\(.)", r"\1", text)                  # markdown escapes
    text = re.sub(r"[^\w\s]|_", " ", text)                # punctuation, quotes, emphasis
    return re.sub(r"\s+", " ", text).strip().lower()

def segment(lines, headings_only_markdown):
    """Yield (clause_id, title, body_text) for each clause, body = up to next heading."""
    heads = []
    for i, line in enumerate(lines):
        if headings_only_markdown and not line.startswith("#"):
            continue
        m = HEADING.match(line.strip())
        if m and (line.startswith("#") or "." in m["id"]):   # bare "7" lines are too ambiguous
            heads.append((i, m["id"], m["title"].strip()))
    for k, (start, cid, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        yield cid, title, "\n".join(lines[start + 1:end])

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", nargs=2, metavar=("CLAUSE", "QUOTE"))
    g.add_argument("--find", metavar="QUOTE")
    ap.add_argument("--markdown-headings", action="store_true",
                    help="only '#' lines are headings (safer for Markdown sources)")
    ap.add_argument("--include-subclauses", action="store_true",
                    help="--check also searches clauses nested under CLAUSE")
    a = ap.parse_args()

    with open(a.spec, encoding="utf-8") as f:
        lines = f.read().splitlines()
    clauses = list(segment(lines, a.markdown_headings))
    quote = norm(a.check[1] if a.check else a.find)
    if not quote:
        sys.exit("empty quote")
    hits = [(cid, title) for cid, title, body in clauses if quote in norm(body)]

    if a.find:
        for cid, title in hits:
            print(f"{cid}  {title}")
        sys.exit(0 if hits else 1)

    want = a.check[0].removeprefix("§").removeprefix("Section ").strip()
    known = {cid for cid, _, _ in clauses}
    if want not in known:
        sys.exit(f"UNKNOWN CLAUSE {want}: no heading with that id (not a quote failure)")
    scope = [cid for cid in known
             if cid == want or (a.include_subclauses and cid.startswith(want + "."))]
    ok = [cid for cid, _ in hits if cid in scope]
    if ok:
        print(f"OK  {want}: quote found in {', '.join(sorted(ok))}")
        sys.exit(0)
    where = ", ".join(cid for cid, _ in hits) or "nowhere in the document"
    print(f"FAIL {want}: quote not in that clause; it occurs in: {where}")
    sys.exit(1)

if __name__ == "__main__":
    main()
```

## Using it well

- Run `--check` on **every** citation before it goes into a code comment, test, commit message or design doc.
  That includes citations copied from tickets or older docs. Those are the ones most likely to be wrong.
- On `FAIL`, the output tells you where the quote really lives. Fix the clause number and read *that* clause
  before continuing. The rule you meant may say something slightly different.
- A passing check proves the quote is in the clause. It does **not** prove the clause governs your question.
  The SKILL's "a real clause answering a different question" failure mode still applies.
- Make the check fail once on purpose (use a wrong clause number) before you trust its green.
- For a standard you only have as PDF, extract the text once (for example `pdftotext -layout`), commit the
  text, and check against that. Render the PDF page whenever a figure or table is what decides the question.
