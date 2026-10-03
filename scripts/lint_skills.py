#!/usr/bin/env python3
"""Lint the skills repository without calling a model. Exits non-zero on any finding.

    python scripts/lint_skills.py [repo-root]

Checks:
  1. Every skills/<dir>/SKILL.md has YAML front matter whose `name` equals the directory and a non-empty `description`.
  2. `.claude-plugin/plugin.json` lists exactly the skill directories and agent files that exist, and its version equals
     `.claude-plugin/marketplace.json`'s `metadata.version`.
  3. Every relative markdown link in a README, SKILL.md or references/*.md resolves to a file (anchors are not checked).
  4. Every `references/<file>` a SKILL.md names exists inside that skill.
  5. Eval anchoring: for each evals/<case>/ the file-like tokens (`status_delta.py`) and ALL-CAPS tokens (`STATUS-AT`) written
     into its regex graders must still appear in the text of the skill (SKILL.md and references) or agent the case covers,
     so an edit that deletes the thing a case tests fails here, before a paid eval run.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
problems = []


def bad(msg):
    problems.append(msg)


def front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out, key = {}, None
    for line in m.group(1).splitlines():
        km = re.match(r"([A-Za-z_-]+):\s*(.*)$", line)
        if km and not line.startswith(" "):
            key = km.group(1)
            out[key] = km.group(2).strip()
        elif key and line.startswith(" "):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
for d in skills:
    f = d / "SKILL.md"
    if not f.exists():
        bad(f"{d.name}: no SKILL.md")
        continue
    fm = front_matter(f.read_text(encoding="utf-8"))
    if fm is None:
        bad(f"{d.name}: SKILL.md has no front matter")
        continue
    if fm.get("name") != d.name:
        bad(f"{d.name}: front matter name is {fm.get('name')!r}")
    if not fm.get("description"):
        bad(f"{d.name}: empty description")

plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
listed = {pathlib.PurePosixPath(s).name for s in plugin.get("skills", [])}
actual = {d.name for d in skills}
for n in sorted(actual - listed):
    bad(f"plugin.json does not list skill {n}")
for n in sorted(listed - actual):
    bad(f"plugin.json lists a skill that does not exist: {n}")
agents_listed = {pathlib.PurePosixPath(s).name for s in plugin.get("agents", [])}
agents_actual = {p.name for p in (ROOT / "agents").glob("*.md") if p.name != "README.md"}
for n in sorted(agents_actual - agents_listed):
    bad(f"plugin.json does not list agent {n}")
for n in sorted(agents_listed - agents_actual):
    bad(f"plugin.json lists an agent that does not exist: {n}")
if plugin.get("version") != market.get("metadata", {}).get("version"):
    bad(f"version mismatch: plugin.json {plugin.get('version')} vs marketplace.json {market.get('metadata', {}).get('version')}")

LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
docs = [ROOT / "README.md", *ROOT.glob("*.md")]
for d in skills:
    docs += [d / "SKILL.md", *sorted((d / "references").rglob("*.md")), *d.glob("README.md")]
docs += list((ROOT / "agents").glob("*.md")) + list((ROOT / "evals").glob("*.md"))
def heading_slugs(path):
    slugs = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        hm = re.match(r"#{1,6}\s+(.*)$", line)
        if hm:
            slugs.add(re.sub(r"[^\w\- ]", "", hm.group(1).strip().lower()).replace(" ", "-"))
    return slugs


LINK_ANCHOR = re.compile(r"\]\(([^)\s#]+\.md)#([^)\s]+)\)")
for f in {p for p in docs if p.exists()}:
    text = f.read_text(encoding="utf-8")
    for m in LINK.finditer(text):
        t = m.group(1)
        if re.match(r"[a-z]+:", t):
            continue
        if not (f.parent / t).resolve().exists():
            bad(f"{f.relative_to(ROOT)}: broken link {t}")
    for m in LINK_ANCHOR.finditer(text):
        t, anc = m.group(1), m.group(2)
        target = (f.parent / t).resolve()
        if target.exists() and anc not in heading_slugs(target):
            bad(f"{f.relative_to(ROOT)}: link {t}#{anc} points at a heading that is not in that file")

for d in skills:
    f = d / "SKILL.md"
    if not f.exists():
        continue
    for m in set(re.findall(r"(?<![\w/-])references/([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", f.read_text(encoding="utf-8"))):
        # a skill may name another skill's reference ("from spec-oracle (references/x.md there)"), so any skill may hold it
        if not any((s / "references" / m).exists() for s in skills):
            bad(f"{d.name}: SKILL.md names references/{m}, which no skill contains")


def anchors(pattern):
    toks = set(re.findall(r"[A-Za-z0-9_]+(?:\\?\.[a-z]{1,3})\b", pattern))
    toks = {t.replace("\\", "") for t in toks if re.search(r"\.(py|cs|js|md|json|sh|ps1)$", t.replace("\\", ""))}
    toks |= set(re.findall(r"\b[A-Z][A-Z0-9]+(?:[-_][A-Z0-9]+)+\b", pattern))
    return toks


def text_of(case_name):
    for d in sorted(skills, key=lambda p: -len(p.name)):
        if case_name == d.name or case_name.startswith(d.name + "-"):
            return d.name, "\n".join(p.read_text(encoding="utf-8") for p in [d / "SKILL.md", *sorted((d / "references").rglob("*")) ] if p.is_file())
    if case_name.startswith("agent-"):
        a = ROOT / "agents" / (case_name[len("agent-"):] + ".md")
        if a.exists():
            return a.name, a.read_text(encoding="utf-8")
    return None, None


for case in sorted(p for p in (ROOT / "evals").iterdir() if p.is_dir() and p.name != "results"):  # results/ is gitignored run output
    owner, body = text_of(case.name)
    if body is None:
        bad(f"evals/{case.name}: cannot tell which skill or agent it covers")
        continue
    for g in sorted((case / "graders").glob("*.md")):
        fm = g.read_text(encoding="utf-8")
        pm = re.search(r"^pattern:\s*'(.*)'\s*$", fm, re.M) or re.search(r'^pattern:\s*"(.*)"\s*$', fm, re.M)
        if not pm or "type: regex" not in fm:
            continue
        scenario = (case / "prompt.md").read_text(encoding="utf-8") if (case / "prompt.md").exists() else ""
        for tok in sorted(anchors(pm.group(1))):
            # a token the scenario itself introduces is the case's own answer vocabulary, not something the skill teaches
            if tok not in body and tok not in scenario:
                bad(f"evals/{case.name}/{g.name}: grader names {tok!r}, which {owner} no longer contains")

if problems:
    print(f"lint_skills: {len(problems)} finding(s)")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print(f"lint_skills: OK ({len(skills)} skills, {len(list((ROOT / 'evals').iterdir()))} eval entries)")
