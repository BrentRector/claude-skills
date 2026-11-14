#!/usr/bin/env python3
"""Lint the skills repository without calling a model. Exits non-zero on any ERROR; warnings are listed, not fatal.

    python scripts/lint_skills.py [repo-root]
    python scripts/lint_skills.py --self-test

Every finding carries its rule tag. A rule today's tree passes is an ERROR, so it stays passed. A rule today's tree
does not pass yet is a WARNING (named in WARNING_RULES with the reason) and lists every violation, until the skills
are rewritten to meet it; then it moves to ERROR.

Rules:
  front-matter     Every skills/<dir>/SKILL.md has YAML front matter whose `name` equals the directory and a non-empty
                   `description`.
  manifest         `.claude-plugin/plugin.json` lists exactly the skill directories and agent files that exist, and its
                   version equals `.claude-plugin/marketplace.json`'s `metadata.version`.
  links            Every relative markdown link in a root or evals/*.md file, README, SKILL.md, references/**/*.md or
                   agents/*.md resolves to a file, and a `file.md#anchor` link names a heading in that file.
  references       Every `references/<file>` a SKILL.md names exists in some skill (a skill may cite another's).
  eval-anchors     For each evals/<case>/, the file-like tokens (`status_delta.py`) and ALL-CAPS tokens (`STATUS-AT`) in
                   its regex graders still appear in the covered skill's text (SKILL.md and references) or agent, or
                   in the scenario, so an edit that deletes what a case tests fails before a paid eval run.
  desc-length      A skill or agent `description` is at most 1,024 characters (the documented limit: ERROR), and a
                   WARNING above DESC_SOFT_CAP. Claude Code lists every description in each session within a budget
                   of 1 % of the context window at 4 characters per token (CLI 2.1.325: 8,000 characters on a
                   200k-token window); this plugin's 13 skills at 500 characters each would fill 81 % of it alone.
  desc-person      A description is written in the third person: no "I", "me", "my", "we", "our", "us", "you" or
                   "your" ("Use when ..." addresses the reader's situation and is allowed).
  outcome          A SKILL.md opens with its outcome: the first prose paragraph after the title (blockquotes, which
                   hold attributions, are skipped) comes before the first `##` heading, is at most OUTCOME_MAX_CHARS
                   characters (two or three sentences), states an outcome (it opens with a bold sentence or uses one
                   of OUTCOME_CLAIM: "so that", "the result", "ends with", "done when", ...) and says how it is
                   checked (one of OUTCOME_VERIFY_WORDS: verify, prove, evidence, check, ...). The check is
                   necessary, not sufficient: a paragraph can pass it and still not state an outcome.
  model-id         No model id or model family name (`claude-...`, Opus, Sonnet, Haiku, Fable, Mythos) outside the
                   two homes for them, the `model:` front-matter line of a role template and of a plugin agent
                   (`agents/*.md`), and MODEL_ID_ALLOWED; the README's changelog sections ("What's new in ...",
                   "Unreleased") are history and exempt.
  dead-path        A path written in backticks that names this repository (`skills/...`, `agents/...`, `evals/...`,
                   `.claude-plugin/...`, and in a skill's own files `references/...` and `templates/...`) exists.
                   Skipped: spans with placeholders (`<x>`, `*`, `{}`, `$`); paragraphs that attribute an upstream
                   source ("adapted from", "attribution"), whose paths are in the other repository; THIRD-PARTY
                   notices; and `scripts/...` inside a skill, which in a skill usually names the reader's project.
  learnings-quote  Each quotation in a LEARNINGS.md "Fix in the skills" bullet still occurs in the file its link cites
                   (whitespace, emphasis and quote marks ignored; "..." splits a quote into fragments). The finding
                   says whether the text moved to another file of the skill or is gone.
  case-yaml        No value in an eval case's front matter holds an unquoted ": " (the CLI's YAML parser rejects it
                   and the run skips the case).
  reachable        Every file under a skill's subdirectories (references/, templates/, scripts/, ...) is named,
                   directly or through a file it names, by that skill's SKILL.md: by its relative path, its file
                   name, or a directory path that contains it.
"""
import json
import pathlib
import re
import shutil
import sys
import tempfile

DESC_HARD_CAP = 1024
DESC_SOFT_CAP = 500
OUTCOME_MAX_CHARS = 600
OUTCOME_VERIFY_WORDS = r"\b(verif\w*|prov(?:e|es|ed|en|ing)|proof|evidence|confirm\w*|checks?|checked|witness\w*)\b"
OUTCOME_CLAIM = r"^\*\*[^*]+\*\*|\b(so that|outcome|the result|results? in|ends? with|done when|succeeds? when|achieves?|leaves?)\b"
ROLE_TEMPLATES = "skills/automating-agent-guardrails/templates/agents/"


def model_home(rel):
    """A file whose front-matter `model:` line is a home for a model alias: a role template or a plugin agent."""
    return rel.startswith(ROLE_TEMPLATES) or (rel.startswith("agents/") and rel.count("/") == 1
                                               and rel.endswith(".md") and rel != "agents/README.md")


MODEL_ID_ALLOWED = {
    # self-test fixtures of the checkers that read model fields: they must use the real shape
    "skills/automating-agent-guardrails/scripts/readiness_check.py": "self-test fixtures",
    "skills/automating-agent-guardrails/scripts/usage_report.py": "self-test fixtures",
    # the measurement harness: model ids are its parameters
    "scripts/run_evals.py": "eval harness", "scripts/lint_skills.py": "this rule's own patterns",
    "evals/": "eval harness and its baselines",
    # history, human-only
    "LEARNINGS.md": "history",
}
WARNING_RULES = {
    # rule: why it is not an error yet (today's tree violates it; the skills' rewrite fixes it)
    "outcome": "13 of 15 SKILL.md files open with method or history (2026-11-14); the 5.2 rewrite puts the outcome first",
    "model-id": "3 skill files name a model family (2026-11-14); the 5.2 rewrite moves them to tiers",
    "learnings-quote": "7 LEARNINGS quotes no longer match their cited file (2026-11-14); the LEARNINGS fix re-points them",
}
MODEL_WORD = re.compile(r"\bclaude-(?:opus|sonnet|haiku|fable|mythos)[\w.-]*|\b(?:opus|sonnet|haiku|fable|mythos)\b", re.I)
PERSON = re.compile(r"\b(I|I'm|I've|me|my|we|we're|our|us|you|you're|your)\b", re.I)
PLUGIN_DIRS = ("skills/", "agents/", "evals/", "scripts/", ".claude-plugin/", ".github/")
TEXT_SUFFIXES = {".md", ".py", ".js", ".ps1", ".sh", ".cs", ".json", ".yml", ".yaml", ".txt"}


def front_matter(text):
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
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


def body_of(text):
    m = re.match(r"---\r?\n.*?\r?\n---\r?\n", text, re.S)
    return text[m.end():] if m else text


def heading_slugs(path):
    slugs = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        hm = re.match(r"#{1,6}\s+(.*)$", line)
        if hm:
            slugs.add(re.sub(r"[^\w\- ]", "", hm.group(1).strip().lower()).replace(" ", "-"))
    return slugs


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[*`_\"'“”‘’]", "", s)).strip().lower()


def text_files(root):
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        # the plugin's own tree; anything else at the root (a local plans/ folder, say) is not published
        if (p.is_file() and p.suffix in TEXT_SUFFIXES and ("/" not in rel or rel.startswith(PLUGIN_DIRS))
                and not rel.startswith("evals/results/") and "__pycache__" not in p.parts):
            yield p, rel


def lint(root):
    findings = []  # (rule, message)

    def bad(rule, msg):
        findings.append((rule, msg))

    skills = sorted(p for p in (root / "skills").iterdir() if p.is_dir())

    # front-matter, desc-length, desc-person
    described = []
    for d in skills:
        f = d / "SKILL.md"
        if not f.exists():
            bad("front-matter", f"{d.name}: no SKILL.md")
            continue
        fm = front_matter(f.read_text(encoding="utf-8"))
        if fm is None:
            bad("front-matter", f"{d.name}: SKILL.md has no front matter")
            continue
        if fm.get("name") != d.name:
            bad("front-matter", f"{d.name}: front matter name is {fm.get('name')!r}")
        if not fm.get("description"):
            bad("front-matter", f"{d.name}: empty description")
        described.append((f"skills/{d.name}", fm.get("description", "")))
    for a in sorted((root / "agents").glob("*.md")):
        if a.name == "README.md":
            continue
        fm = front_matter(a.read_text(encoding="utf-8")) or {}
        described.append((f"agents/{a.name}", fm.get("description", "")))
    for who, desc in described:
        desc = desc.strip("\"'")
        if len(desc) > DESC_HARD_CAP:
            bad("desc-length", f"{who}: description is {len(desc)} characters, over the {DESC_HARD_CAP} limit")
        elif len(desc) > DESC_SOFT_CAP:
            bad("desc-length-soft", f"{who}: description is {len(desc)} characters, over the {DESC_SOFT_CAP} bar")
        words = sorted({w.lower() for w in PERSON.findall(desc)})
        if words:
            bad("desc-person", f"{who}: description is not in the third person ({', '.join(words)})")

    # manifest
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    listed = {pathlib.PurePosixPath(s).name for s in plugin.get("skills", [])}
    actual = {d.name for d in skills}
    for n in sorted(actual - listed):
        bad("manifest", f"plugin.json does not list skill {n}")
    for n in sorted(listed - actual):
        bad("manifest", f"plugin.json lists a skill that does not exist: {n}")
    agents_listed = {pathlib.PurePosixPath(s).name for s in plugin.get("agents", [])}
    agents_actual = {p.name for p in (root / "agents").glob("*.md") if p.name != "README.md"}
    for n in sorted(agents_actual - agents_listed):
        bad("manifest", f"plugin.json does not list agent {n}")
    for n in sorted(agents_listed - agents_actual):
        bad("manifest", f"plugin.json lists an agent that does not exist: {n}")
    if plugin.get("version") != market.get("metadata", {}).get("version"):
        bad("manifest", f"version mismatch: plugin.json {plugin.get('version')} vs marketplace.json "
                        f"{market.get('metadata', {}).get('version')}")

    # links
    link = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
    link_anchor = re.compile(r"\]\(([^)\s#]+\.md)#([^)\s]+)\)")
    docs = [*root.glob("*.md")]
    for d in skills:
        docs += [d / "SKILL.md", *sorted((d / "references").rglob("*.md")), *d.glob("README.md")]
    docs += list((root / "agents").glob("*.md")) + list((root / "evals").glob("*.md"))
    for f in sorted({p for p in docs if p.exists()}):
        text = f.read_text(encoding="utf-8")
        for m in link.finditer(text):
            t = m.group(1)
            if re.match(r"[a-z]+:", t):
                continue
            if not (f.parent / t).resolve().exists():
                bad("links", f"{f.relative_to(root).as_posix()}: broken link {t}")
        for m in link_anchor.finditer(text):
            t, anc = m.group(1), m.group(2)
            target = (f.parent / t).resolve()
            if target.exists() and anc not in heading_slugs(target):
                bad("links", f"{f.relative_to(root).as_posix()}: link {t}#{anc} points at a heading that is not in that file")

    # references
    for d in skills:
        f = d / "SKILL.md"
        if not f.exists():
            continue
        for m in sorted(set(re.findall(r"(?<![\w/-])references/([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", f.read_text(encoding="utf-8")))):
            if not any((s / "references" / m).exists() for s in skills):
                bad("references", f"{d.name}: SKILL.md names references/{m}, which no skill contains")

    # eval-anchors
    def anchors(pattern):
        toks = set(re.findall(r"[A-Za-z0-9_]+(?:\\?\.[a-z]{1,3})\b", pattern))
        toks = {t.replace("\\", "") for t in toks if re.search(r"\.(py|cs|js|md|json|sh|ps1)$", t.replace("\\", ""))}
        toks |= set(re.findall(r"\b[A-Z][A-Z0-9]+(?:[-_][A-Z0-9]+)+\b", pattern))
        return toks

    def text_of(case_name):
        for d in sorted(skills, key=lambda p: -len(p.name)):
            if case_name == d.name or case_name.startswith(d.name + "-"):
                # running a reference's own script leaves bytecode beside it; bytecode is not reference text
                return d.name, "\n".join(p.read_text(encoding="utf-8") for p in [d / "SKILL.md", *sorted((d / "references").rglob("*"))]
                                         if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
        if case_name.startswith("agent-"):
            a = root / "agents" / (case_name[len("agent-"):] + ".md")
            if a.exists():
                return a.name, a.read_text(encoding="utf-8")
        return None, None

    eval_dirs = sorted(p for p in (root / "evals").iterdir() if p.is_dir() and p.name not in ("results", "baselines"))
    for case in eval_dirs:  # results/ is gitignored run output; baselines/ holds measurements, not cases
        owner, body = text_of(case.name)
        if body is None:
            bad("eval-anchors", f"evals/{case.name}: cannot tell which skill or agent it covers")
            continue
        scenario = (case / "prompt.md").read_text(encoding="utf-8") if (case / "prompt.md").exists() else ""
        for g in sorted((case / "graders").glob("*.md")):
            fm = g.read_text(encoding="utf-8")
            pm = re.search(r"^pattern:\s*'(.*)'\s*$", fm, re.M) or re.search(r'^pattern:\s*"(.*)"\s*$', fm, re.M)
            if not pm or "type: regex" not in fm:
                continue
            for tok in sorted(anchors(pm.group(1))):
                # a token the scenario itself introduces is the case's own answer vocabulary, not something the skill teaches
                if tok not in body and tok not in scenario:
                    bad("eval-anchors", f"evals/{case.name}/{g.name}: grader names {tok!r}, which {owner} no longer contains")

    # case-yaml: the CLI parses a case's front matter as YAML, where an unquoted value holding ": " is an error
    # that drops the case from the run with no score (2026-11-14: three new cases lost from a full run)
    for case in eval_dirs:
        pf = case / "prompt.md"
        m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", pf.read_text(encoding="utf-8"), re.S) if pf.exists() else None
        for line in (m.group(1).splitlines() if m else []):
            km = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
            if km and km.group(2) and km.group(2)[0] not in "\"'[|>" and ": " in km.group(2):
                bad("case-yaml", f"evals/{case.name}/prompt.md: `{km.group(1)}` holds an unquoted \": \", which YAML "
                                 "rejects; quote the value")

    # outcome
    for d in skills:
        f = d / "SKILL.md"
        if not f.exists():
            continue
        body = body_of(f.read_text(encoding="utf-8"))
        para, seen_heading = None, False
        for block in re.split(r"\n\s*\n", body):
            lines = [l for l in block.strip().splitlines() if l.strip()]
            if not lines:
                continue
            if lines[0].startswith("## ") or lines[0].startswith("### "):
                seen_heading = True
                break
            lines = [l for l in lines if not l.startswith("# ")]
            if not lines or all(l.startswith(">") for l in lines):
                continue
            para = " ".join(lines)
            break
        if para is None or seen_heading:
            bad("outcome", f"{d.name}: no prose paragraph before the first section heading")
        elif len(para) > OUTCOME_MAX_CHARS:
            bad("outcome", f"{d.name}: the opening paragraph is {len(para)} characters (over {OUTCOME_MAX_CHARS}): "
                           f"{para[:70]!r}...")
        elif not re.search(OUTCOME_CLAIM, para, re.I):
            bad("outcome", f"{d.name}: the opening paragraph states no outcome: {para[:70]!r}...")
        elif not re.search(OUTCOME_VERIFY_WORDS, para, re.I):
            bad("outcome", f"{d.name}: the opening paragraph does not say how its outcome is checked: {para[:70]!r}...")

    # model-id
    for p, rel in text_files(root):
        if any(rel == k or (k.endswith("/") and rel.startswith(k)) for k in MODEL_ID_ALLOWED):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        in_fm = model_home(rel) and text.startswith("---")
        fm_end = text.find("\n---", 3) if in_fm else -1
        history = False
        offset = 0
        for i, line in enumerate(text.splitlines(), 1):
            if rel == "README.md" and line.startswith("## "):
                history = line.startswith(("## What's new in", "## Unreleased"))  # the changelog is history
            pos, offset = offset, offset + len(line) + 1
            if history:
                continue
            if in_fm and pos < fm_end and re.match(r"model:\s", line):
                continue  # a home: a role template's or a plugin agent's model line
            for m in MODEL_WORD.finditer(line):
                bad("model-id", f"{rel}:{i}: names a model ({m.group(0)!r}) outside the role templates' front matter")

    # dead-path
    span = re.compile(r"`([^`\n]+)`")
    repo_rooted = ("skills/", "agents/", "evals/", ".claude-plugin/")
    for p, rel in text_files(root):
        if p.name.startswith("THIRD-PARTY") or not (rel.startswith(("skills/", "agents/", "evals/")) or "/" not in rel):
            continue
        if rel.startswith("evals/") and rel.count("/") > 1:
            continue  # case files: scenarios name the user's paths, not this repository's
        skill = root / "skills" / rel.split("/")[1] if rel.startswith("skills/") else None
        text = p.read_text(encoding="utf-8", errors="replace")
        for block in re.split(r"\n\s*\n", text):
            if re.search(r"adapted from|attribution", block, re.I):
                continue
            for m in span.finditer(block):
                s = m.group(1).strip()
                if any(c in s for c in "<>*{}$"):
                    continue
                pm = re.match(r"^(?:\./)?((?:skills|agents|evals|\.claude-plugin|references|templates)/[A-Za-z0-9_./-]*)", s)
                if not pm:
                    continue
                path = pm.group(1).rstrip(".,:;)")
                if path.startswith(repo_rooted):
                    cands = [root / path]
                elif skill is not None:
                    cands = [skill / path, *(d / path for d in skills)]
                else:
                    continue
                if not any(c.exists() for c in cands):
                    line = text[:text.find(block)].count("\n") + block[:m.start()].count("\n") + 1
                    bad("dead-path", f"{rel}:{line}: `{s}` names a path that does not exist")

    # learnings-quote
    lf = root / "LEARNINGS.md"
    if lf.exists():
        lt = lf.read_text(encoding="utf-8")
        refs = dict(re.findall(r"^\[([^\]]+)\]:\s*(\S+)", lt, re.M))
        quote_after_link = re.compile(r"\[([^\]]+)\](?:\(([^)\s]+)\)|\[([^\]]+)\])((?:(?!\]\(|\]\[).){0,40}?)[\"“]([^\"”]+)[\"”]", re.S)
        for m in re.finditer(r"^- \*\*Fix in the skills:\*\*(.*?)(?=^- \*\*|^#|\Z)", lt, re.M | re.S):
            line = lt[:m.start()].count("\n") + 1
            for lm in quote_after_link.finditer(m.group(1)):
                target = (lm.group(2) or refs.get(lm.group(3), "")).split("#")[0]
                quote = re.sub(r"\s+", " ", lm.group(5))
                cited = root / target
                if not cited.is_file():
                    continue  # a broken link is the links rule's finding
                frags = [norm(x).strip(" .,;:") for x in re.split(r"\.\.\.|…", quote) if x.strip()]
                if all(f in norm(cited.read_text(encoding="utf-8")) for f in frags):
                    continue
                skill_dir = cited.parent if cited.name == "SKILL.md" else next((d for d in skills if d in cited.parents), None)
                moved = [q.relative_to(root).as_posix() for q in sorted((skill_dir or cited.parent).rglob("*.md"))
                         if all(f in norm(q.read_text(encoding="utf-8")) for f in frags)] if skill_dir else []
                where = f"it is now in {', '.join(moved)}" if moved else "no file of that skill contains it"
                bad("learnings-quote", f"LEARNINGS.md:{line}: quote \"{quote}\" is not in {target}; {where}")

    # reachable
    for d in skills:
        start = d / "SKILL.md"
        if not start.exists():
            continue
        files = [p for p in d.rglob("*") if p.is_file() and p.parent != d and "__pycache__" not in p.parts and p.suffix != ".pyc"]
        rel = {p: p.relative_to(d).as_posix() for p in files}
        seen, frontier = {start}, [start]
        while frontier:
            f = frontier.pop()
            if f.suffix not in TEXT_SUFFIXES:
                continue
            txt = f.read_text(encoding="utf-8", errors="replace")
            for p, r in rel.items():
                if p in seen:
                    continue
                dirs = ["/".join(r.split("/")[:k]) + "/" for k in range(2, r.count("/") + 1)]
                if r in txt or p.name in txt or any(x in txt for x in dirs):
                    seen.add(p)
                    frontier.append(p)
        for p in files:
            if p not in seen:
                bad("reachable", f"skills/{d.name}/{rel[p]}: nothing reachable from SKILL.md names it")

    return findings, len(skills), len(eval_dirs)


def severity(rule):
    return "warning" if rule in WARNING_RULES or rule.endswith("-soft") else "error"


def report(root):
    findings, n_skills, n_cases = lint(root)
    errors = [(r, m) for r, m in findings if severity(r) == "error"]
    warnings = [(r, m) for r, m in findings if severity(r) == "warning"]
    if warnings:
        counts = {}
        for r, _ in warnings:
            counts[r] = counts.get(r, 0) + 1
        print(f"lint_skills: {len(warnings)} warning(s): " + ", ".join(f"{r} {n}" for r, n in sorted(counts.items())))
        for r, m in warnings:
            print(f"  ~ [{r}] {m}")
    if errors:
        print(f"lint_skills: {len(errors)} error(s)")
        for r, m in errors:
            print(f"  - [{r}] {m}")
        return 1
    print(f"lint_skills: OK ({n_skills} skills, {n_cases} eval cases)")
    return 0


# --- self-test: a minimal clean tree, then one planted violation per rule ---------------------------------------

FIXTURE = {
    ".claude-plugin/plugin.json": json.dumps({"name": "t", "version": "1.0.0", "skills": ["./skills/alpha", "./skills/automating-agent-guardrails"],
                                              "agents": ["./agents/checker.md"]}),
    ".claude-plugin/marketplace.json": json.dumps({"metadata": {"version": "1.0.0"}}),
    "README.md": "# T\n\n## Unreleased\n\n- Measured on Opus.\n\n## Skills\n\nSee [alpha](skills/alpha/SKILL.md).\n",
    "LEARNINGS.md": ("# Learnings\n\n### C1. Example\n- **Problem:** x.\n- **Fix in the skills:** "
                     "[alpha](skills/alpha/SKILL.md#rules) \"Check the staged tree\".\n- **Evidence:** y.\n"),
    "agents/checker.md": "---\nname: checker\ndescription: Use when a change needs checking.\nmodel: opus\n---\nBody.\n",
    "skills/alpha/SKILL.md": ("---\nname: alpha\ndescription: Use when a commit is about to be made.\n---\n\n# Alpha\n\n"
                              "**Nothing unreviewed is committed**, and the staged diff proves it.\n\n## Rules\n\n"
                              "- Check the staged tree. See [the guide](references/guide.md).\n"),
    "skills/alpha/references/guide.md": "# Guide\n\nRun `helper.py` from `skills/alpha/scripts/`.\n",
    "skills/alpha/scripts/helper.py": "print('ok')\n",
    "skills/automating-agent-guardrails/SKILL.md": ("---\nname: automating-agent-guardrails\ndescription: Use when agent "
                                                   "rules keep getting broken.\n---\n\n# Guardrails\n\n**Rules become "
                                                   "hooks**, and the readiness check proves it.\n\n## Roles\n\n"
                                                   "Copy `templates/agents/worker.md`.\n"),
    "skills/automating-agent-guardrails/templates/agents/worker.md": "---\nname: worker\nmodel: opus\neffort: medium\n---\nA worker.\n",
    "evals/README.md": "# Evals\n",
    "evals/alpha-staged/prompt.md": "---\nname: alpha-staged\n---\nCommit this.\n",
    "evals/alpha-staged/graders/g.md": "---\ntype: regex\ntarget: last_message\npattern: 'staged'\n---\n",
}

PLANTS = {
    # rule -> {path: (old, new) or new content}
    "desc-length": {"skills/alpha/SKILL.md": ("a commit is about to be made.", "x" * 1030 + ".")},
    "desc-length-soft": {"skills/alpha/SKILL.md": ("a commit is about to be made.", "x" * 600 + ".")},
    "desc-person": {"agents/checker.md": ("Use when a change needs checking.", "I check your change.")},
    "outcome": {"skills/alpha/SKILL.md": ("and the staged diff proves it.", "always.")},
    "model-id": {"skills/alpha/references/guide.md": ("Run `helper.py`", "Run Sonnet with `helper.py`")},
    "model-id/in-a-template-body": {"skills/automating-agent-guardrails/templates/agents/worker.md":
                                    ("A worker.", "A worker on opus.")},
    "model-id/in-an-agent-body": {"agents/checker.md": ("Body.", "Body.\nmodel: sonnet\n")},
    "model-id/readme-after-changelog": {"README.md": ("See [alpha]", "Mythos. See [alpha]")},
    "model-id/agents-readme": {"agents/README.md": "---\nmodel: opus\n---\n# Agents\n"},
    "outcome/no-claim": {"skills/alpha/SKILL.md": ("**Nothing unreviewed is committed**, and the staged diff proves it.",
                                                   "A commit can be checked in many ways.")},
    "dead-path": {"skills/alpha/references/guide.md": ("`skills/alpha/scripts/`", "`skills/alpha/tools/`")},
    "learnings-quote": {"LEARNINGS.md": ("Check the staged tree", "Check the index")},
    "reachable": {"skills/alpha/references/orphan.md": "# Orphan\n"},
    "links": {"README.md": ("skills/alpha/SKILL.md", "skills/alpha/MISSING.md")},
    "eval-anchors": {"evals/alpha-staged/graders/g.md": ("'staged'", "'STAGED-OK'")},
    "case-yaml": {"evals/alpha-staged/prompt.md": ("name: alpha-staged", "name: alpha-staged\ndescription: Cause: unquoted")},
}


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp) / "clean"
        for rel, content in FIXTURE.items():
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            (base / rel).write_text(content, encoding="utf-8")
        clean, _, _ = lint(base)
        if clean:
            failures.append(f"clean fixture has findings: {clean}")
        for rule, edits in PLANTS.items():
            tree = pathlib.Path(tmp) / rule.replace("/", "-")
            shutil.copytree(base, tree)
            for rel, edit in edits.items():
                f = tree / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(edit, tuple):
                    old = f.read_text(encoding="utf-8")
                    assert edit[0] in old, (rule, rel, edit[0])
                    f.write_text(old.replace(edit[0], edit[1]), encoding="utf-8")
                else:
                    f.write_text(edit, encoding="utf-8")
            got = {r for r, _ in lint(tree)[0]}
            plant, rule = rule, rule.split("/")[0]
            if rule not in got:
                failures.append(f"planted {plant} violation not reported (got {sorted(got) or 'nothing'})")
            else:
                print(f"self-test: planted {plant} -> reported as {rule}, {severity(rule)}")
    if failures:
        print("self-test FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"self-test: OK ({len(PLANTS)} planted violations, each reported; clean fixture has none)")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    sys.exit(report(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()))
