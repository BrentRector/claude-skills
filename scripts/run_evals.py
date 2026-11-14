#!/usr/bin/env python3
"""Run the eval suite on a NAMED model and effort level, and record both in the result.

    python scripts/run_evals.py run --model claude-opus-5-5 --effort medium [--case GLOB] [--runs N] [-j N]
    python scripts/run_evals.py table <results-dir> [--out evals/baselines/<name>.md]
    python scripts/run_evals.py compare <before> <after>
    python scripts/run_evals.py merge <base-dir> <rerun-dir>... --out <name>   (merge --self-test checks it)

Why this wrapper exists. `claude plugin eval` (CLI 2.1.325) takes `--model` but has no effort flag, and it writes
no effort into its result. Its child sessions run with `--setting-sources user`, so a run started without `--model`
uses the operator's own default model, and every run uses the operator's own `effortLevel`: the same command measures
different things on different machines and days, and the result does not say which. This wrapper

  - requires a full model id (`claude-...`, never an alias, which resolves to a different model over time) and an
    effort level, and refuses to run without them;
  - passes `--model`, and sets the effort through CLAUDE_CODE_EFFORT_LEVEL in the children's environment (the CLI's
    effort resolution gives that variable precedence over every `effortLevel` setting); it refuses to run when the
    operator's user settings `env` sets that variable itself, because settings `env` overrides the process
    environment in the child;
  - keeps each run's trace long enough to read the model the child actually reported (its `system/init` event and the
    models in its usage), and fails when any run did not run on the requested model;
  - marks every run that hit its turn cap or timeout (`cutOff`), so a cut-off reads as a harness limit, not a skill
    failure;
  - writes `suite.model`, `suite.effort`, `suite.recordedBy` and the same model and effort on every case into
    `aggregate-result.json`, plus a compact `summary.md`.

`table` renders a results directory as the tracked baseline (a markdown table and a JSON sidecar). `compare` prints
the per-case delta change between two results (results directories, aggregate files or baseline JSON files) and
refuses to compare results whose model or effort differ, since such a difference measures the model, not the skill.

`merge` replaces whole cases of a result with complete re-runs (`run --case <name>`) of the same model, effort,
plugin version and skills/agents tree, refuses a replacement that still has a cut-off run, recomputes the
aggregates and records in `suite.merged` which runs replaced which (and how many of the replaced runs were cut off).
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL_ID = re.compile(r"^claude-[a-z0-9]+(?:-[a-z0-9]+)+$")
RECORDER = "scripts/run_evals.py"


def die(msg, code=2):
    print(f"run_evals: {msg}", file=sys.stderr)
    sys.exit(code)


def settings_env():
    """The `env` block of the operator's user settings, which every eval child loads (`--setting-sources user`)."""
    config = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")
    f = config / "settings.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("env", {}) or {}
    except json.JSONDecodeError as e:
        die(f"cannot read {f}: {e}")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def read_trace(path):
    """What the child session reported about itself: init model, models in its usage, how it ended."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    init_model, models, end = None, set(), None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            init_model = e.get("model")
        elif e.get("type") == "assistant":
            m = (e.get("message") or {}).get("model")
            if m and not m.startswith("<"):
                models.add(m)
        elif e.get("type") == "result":
            models |= set((e.get("modelUsage") or {}).keys())
            end = {"subtype": e.get("subtype"), "terminalReason": e.get("terminal_reason"), "numTurns": e.get("num_turns")}
    return {"initModel": init_model, "models": sorted(models), "end": end}


def cmd_run(a):
    if not MODEL_ID.match(a.model):
        die(f"--model must be a full model id such as claude-opus-5-5, not {a.model!r}: an alias resolves to a "
            "different model over time, so its result cannot be compared")
    env_settings = settings_env()
    if "CLAUDE_CODE_EFFORT_LEVEL" in env_settings:
        die("the user settings `env` sets CLAUDE_CODE_EFFORT_LEVEL="
            f"{env_settings['CLAUDE_CODE_EFFORT_LEVEL']!r}; it overrides the effort this run asks for in every child. "
            "Remove it from settings.json before measuring.")
    claude = shutil.which("claude") or die("claude is not on PATH")
    cli_version = subprocess.run([claude, "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    plugin_version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    head = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", "skills", "agents", "evals", ".claude-plugin")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out = ROOT / "evals" / "results" / f"{stamp}-{a.model}-{a.effort}"
    out.mkdir(parents=True)

    cmd = [claude, "plugin", "eval", ".", "--model", a.model, "--no-publish", "--trust-plugin", "--threshold", "0",
           "--keep-temp", "-j", str(a.concurrency), "--output-dir", str(out), "--report", str(out / "report.html")]
    if a.case:
        cmd += ["--case", a.case]
    if a.runs:
        cmd += ["--runs", str(a.runs)]
    if a.max_cost_usd:
        cmd += ["--max-cost-usd", str(a.max_cost_usd)]
    child_env = dict(os.environ, CLAUDE_CODE_EFFORT_LEVEL=a.effort)
    print(f"run_evals: {a.model} at effort {a.effort}, CLI {cli_version}, plugin {plugin_version}, head {head[:10]}"
          f"{' (dirty)' if dirty else ''} -> {out.relative_to(ROOT)}", flush=True)
    rc = subprocess.run(cmd, cwd=ROOT, env=child_env).returncode
    agg_path = out / "aggregate-result.json"
    if not agg_path.exists():
        die(f"claude plugin eval exited {rc} and wrote no aggregate-result.json", 1)
    agg = json.loads(agg_path.read_text(encoding="utf-8"))

    wrong, missing, cut, extra = [], [], [], set()
    temp_dirs = set()
    for case in agg["cases"]:
        case["model"], case["effort"] = a.model, a.effort
        for arm, runs in case["arms"].items():
            for i, r in enumerate(runs or []):
                tag = f"{case['name']} {arm}#{i + 1}"
                obs = read_trace(r.get("tracePath") or "")
                r["observed"] = obs
                if obs is None:
                    missing.append(tag)
                else:
                    if obs["initModel"] != a.model:
                        wrong.append(f"{tag}: ran on {obs['initModel']!r}")
                    extra |= set(obs["models"]) - {a.model}
                end = (obs or {}).get("end") or {}
                timed_out = "timed out" in str(r.get("error") or "")
                r["cutOff"] = ("max_turns" if "max_turns" in str(end.get("subtype")) else
                               "timeout" if timed_out else None)
                if r["cutOff"]:
                    cut.append(f"{tag}: {r['cutOff']} (turns {r.get('turns')}/{case['maxTurns']}, "
                               f"{r.get('durationSeconds')}s/{case['timeoutSeconds']}s)")
                tp = pathlib.Path(r.get("tracePath") or "")
                if tp.is_file():
                    # keep the trace with the result: it is the only record of what the run did
                    kept = out / "traces" / f"{case['name']}-{arm}-{i + 1}.jsonl"
                    kept.parent.mkdir(exist_ok=True)
                    shutil.copyfile(tp, kept)
                    r["tracePath"] = str(kept.relative_to(out))
                if tp.parent.parent.name.startswith("claude-eval-"):
                    temp_dirs.add(tp.parent.parent)
    agg["suite"].update({
        "model": a.model, "effort": a.effort, "effortSource": "CLAUDE_CODE_EFFORT_LEVEL",
        "recordedBy": RECORDER, "gitHead": head, "gitDirty": bool(dirty),
        "settingsEnvModelVars": {k: v for k, v in env_settings.items() if re.search("MODEL|EFFORT", k)},
        "modelsObservedBesidesRequested": sorted(extra),
        "verification": {"wrongModel": wrong, "traceMissing": missing, "cutOff": cut},
    })
    agg_path.write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    (out / "summary.md").write_text(render_table(agg, out.name), encoding="utf-8")
    print(render_table(agg, out.name))
    for label, items in (("ran on the wrong model", wrong), ("no trace, model unconfirmed", missing),
                         ("cut off by a harness limit", cut)):
        if items:
            print(f"run_evals: {len(items)} run(s) {label}:")
            for x in items:
                print("  -", x)
    if extra:
        print(f"run_evals: models observed besides {a.model} (subagents or helpers): {', '.join(sorted(extra))}; "
              f"user settings env: {agg['suite']['settingsEnvModelVars']}")
    if wrong or missing:
        die("verification failed: this result does not prove its model", 1)
    return rc


def load(path):
    p = pathlib.Path(path)
    if p.is_dir():
        p = p / "aggregate-result.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "cases" in d and isinstance(d["cases"], list):  # an aggregate-result.json
        if d["suite"].get("recordedBy") != RECORDER:
            die(f"{p} was not recorded by {RECORDER}, so its model and effort are unknown")
        return compact(d)
    return d  # a baseline JSON sidecar


def compact(agg):
    s = agg["suite"]
    return {
        "model": s["model"], "effort": s["effort"], "cliVersion": agg["claudeVersion"],
        "pluginVersion": next((p.get("version") for p in s["plugins"]), None), "gitHead": s["gitHead"],
        "gitDirty": s["gitDirty"], "startedAt": agg["startedAt"], "durationSeconds": agg["durationSeconds"],
        "costUsd": round(agg["costUsd"], 2), "partial": agg["partial"],
        "modelsObservedBesidesRequested": s.get("modelsObservedBesidesRequested", []),
        "cutOff": s.get("verification", {}).get("cutOff", []),
        "cases": {c["name"]: {"with": c["aggregates"]["score"], "without": c["aggregates"].get("scoreWithout"),
                              "delta": c["aggregates"].get("delta"), "runsPerArm": len(c["arms"]["with"]),
                              "fired": fired(c), "maxTurns": c["maxTurns"], "timeoutSeconds": c["timeoutSeconds"]}
                  for c in agg["cases"]},
    }


def fired(case):
    """How many WITH runs passed the with-only indicator (skill-fired / agent-dispatched), as "n/runs"."""
    runs = case["arms"]["with"]
    marks = [any(g["withOnly"] and g["passed"] for g in r["graders"]) for r in runs
             if any(g["withOnly"] for g in r["graders"])]
    return f"{sum(marks)}/{len(runs)}" if marks else "-"


def render_table(agg, label):
    c = compact(agg)
    f = lambda x: "-" if x is None else f"{x:.2f}"
    d = lambda x: "-" if x is None else f"{x:+.2f}"
    lines = [f"# Eval result: {c['model']} at effort {c['effort']}", "",
             f"- Model: `{c['model']}` (verified from every run's trace); effort: `{c['effort']}` "
             "(set through CLAUDE_CODE_EFFORT_LEVEL)",
             f"- CLI: {c['cliVersion']}; plugin: {c['pluginVersion']}; tree: `{c['gitHead'][:10]}`"
             f"{' (dirty)' if c['gitDirty'] else ''}",
             f"- Started {c['startedAt']}; {c['durationSeconds']} s; ${c['costUsd']} at list price as the CLI reports it"
             f"{'; PARTIAL' if c['partial'] else ''}; raw result `evals/results/{label}/` (git-ignored)",
             f"- Other models in the runs' usage: {', '.join(c['modelsObservedBesidesRequested']) or 'none'}",
             f"- Model settings in the operator's user settings `env`, which every child loads: "
             f"{', '.join(f'`{k}={v}`' for k, v in agg['suite'].get('settingsEnvModelVars', {}).items()) or 'none'}",
             f"- Runs cut off by a turn cap or timeout: {len(c['cutOff'])}"]
    lines += [f"  - {x}" for x in c["cutOff"]]
    if agg["suite"].get("droppedCases"):
        lines.append("- Measured in this run but removed from the suite, so not in this table: "
                     + ", ".join(f"`{n}`" for n in agg["suite"]["droppedCases"]))
    for mrec in agg["suite"].get("merged", []):
        if mrec.get("added"):
            lines.append(f"- Case `{mrec['case']}` added from its own run in `evals/results/{mrec['from']}/` (tree "
                         f"`{mrec['fromHead'][:10]}`, same skills tree)")
            continue
        lines.append(f"- Case `{mrec['case']}` replaced by its re-run in `evals/results/{mrec['from']}/` (tree "
                     f"`{mrec['fromHead'][:10]}`, limits {mrec['newLimits'][0]} turns / {mrec['newLimits'][1]} s; the "
                     f"replaced runs had {len(mrec['replacedRunsCutOff'])} cut off at {mrec['replacedLimits'][0]} turns / "
                     f"{mrec['replacedLimits'][1]} s)")
    lines.append("")
    lines += ["| Case | WITH | W/OUT | Δ | Runs/arm | Fired |", "|---|---|---|---|---|---|"]
    for name, v in c["cases"].items():
        lines.append(f"| `{name}` | {f(v['with'])} | {f(v['without'])} | {d(v['delta'])} | {v['runsPerArm']} "
                     f"| {v.get('fired', '-')} |")
    lines += ["", "Fired: WITH runs in which the case's skill loaded or its agent was dispatched (the with-only indicator)."]
    deltas = [v["delta"] for v in c["cases"].values() if v["delta"] is not None]
    if deltas:
        lines += ["", f"Mean Δ over {len(deltas)} cases: {sum(deltas) / len(deltas):+.2f}."]
    return "\n".join(lines) + "\n"


def cmd_table(a):
    p = pathlib.Path(a.results)
    agg_path = p / "aggregate-result.json" if p.is_dir() else p
    agg = json.loads(agg_path.read_text(encoding="utf-8"))
    if agg["suite"].get("recordedBy") != RECORDER:
        die(f"{agg_path} was not recorded by {RECORDER}, so its model and effort are unknown")
    if a.drop_removed:
        # a candidate case measured in this run and then removed from the suite (both arms passed) is not part of
        # the baseline; the table names it so the omission is visible
        gone = [c["name"] for c in agg["cases"] if not (ROOT / "evals" / c["name"]).is_dir()]
        agg["cases"] = [c for c in agg["cases"] if c["name"] not in gone]
        agg["suite"]["droppedCases"] = gone
        agg["suite"]["verification"]["cutOff"] = [x for x in agg["suite"]["verification"].get("cutOff", [])
                                                  if x.split(" ")[0] not in gone]
    text = render_table(agg, agg_path.parent.name)
    if a.out:
        out = pathlib.Path(a.out)
        out.write_text(text, encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(compact(agg), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out} and {out.with_suffix('.json')}")
    else:
        print(text, end="")


def cmd_compare(a):
    x, y = load(a.before), load(a.after)
    if (x["model"], x["effort"]) != (y["model"], y["effort"]):
        die(f"before is {x['model']}/{x['effort']}, after is {y['model']}/{y['effort']}: a difference between them "
            "measures the model or the effort, not the skill. Compare runs of one model at one effort.")
    print(f"{x['model']} at {x['effort']}: before {x['gitHead'][:10]} ({x['startedAt']}), "
          f"after {y['gitHead'][:10]} ({y['startedAt']})")
    print(f"{'CASE':46} {'Δ BEFORE':>9} {'Δ AFTER':>9} {'CHANGE':>8}")
    for name in sorted(set(x["cases"]) | set(y["cases"])):
        b, c = x["cases"].get(name, {}).get("delta"), y["cases"].get(name, {}).get("delta")
        ch = "" if b is None or c is None else f"{c - b:+.2f}"
        fmt = lambda v: "-" if v is None else f"{v:+.2f}"
        print(f"{name:46} {fmt(b):>9} {fmt(c):>9} {ch:>8}")


class MergeRefused(Exception):
    pass


def merge_results(base, base_label, replacements, tree_of, add_new=False):
    """Replace whole cases of `base` with the same cases from later runs of the same model, effort and skills.

    `replacements` is [(label, aggregate)], `tree_of(head)` the git tree id of skills/ and agents/ at a head. Each
    replacement case must be complete (no cut-off run). Returns the merged aggregate, with `suite.merged` recording
    which runs replaced which."""
    s = base["suite"]
    out = json.loads(json.dumps(base))
    merged = list(s.get("merged", []))
    for label, rep in replacements:
        r = rep["suite"]
        for key in ("model", "effort"):
            if r.get(key) != s.get(key):
                raise MergeRefused(f"{label}: {key} {r.get(key)!r} differs from the base's {s.get(key)!r}")
        rv = next((p.get("version") for p in r["plugins"]), None)
        bv = next((p.get("version") for p in s["plugins"]), None)
        if rv != bv:
            raise MergeRefused(f"{label}: plugin version {rv} differs from the base's {bv}")
        if tree_of(r["gitHead"]) != tree_of(s["gitHead"]):
            raise MergeRefused(f"{label}: skills/ or agents/ at {r['gitHead'][:10]} differ from the base's "
                               f"{s['gitHead'][:10]}, so the replacement measures different skills")
        for case in rep["cases"]:
            cut = [f"{arm}#{i + 1}" for arm, runs in case["arms"].items() for i, run in enumerate(runs or [])
                   if run.get("cutOff")]
            if cut:
                raise MergeRefused(f"{label}: {case['name']} has cut-off runs ({', '.join(cut)}); re-size and re-run it")
            idx = next((i for i, c in enumerate(out["cases"]) if c["name"] == case["name"]), None)
            if idx is None:
                if not add_new:
                    raise MergeRefused(f"{label}: {case['name']} is not a case of the base (pass --add-new for a new case)")
                merged.append({"case": case["name"], "from": label, "fromHead": r["gitHead"], "added": True,
                               "newLimits": [case["maxTurns"], case["timeoutSeconds"]]})
                out["cases"].append(case)
                continue
            old = out["cases"][idx]
            old_cut = [f"{arm}#{i + 1}" for arm, runs in old["arms"].items() for i, run in enumerate(runs or [])
                       if run.get("cutOff")]
            merged.append({"case": case["name"], "from": label, "fromHead": r["gitHead"], "replaced": base_label,
                           "replacedRunsCutOff": old_cut, "replacedLimits": [old["maxTurns"], old["timeoutSeconds"]],
                           "newLimits": [case["maxTurns"], case["timeoutSeconds"]],
                           "replacedAggregates": old["aggregates"]})
            out["cases"][idx] = case
        out["costUsd"] += rep["costUsd"]
        out["durationSeconds"] += rep["durationSeconds"]
        out["partial"] = out["partial"] or rep["partial"]
        out["suite"]["modelsObservedBesidesRequested"] = sorted(
            set(out["suite"].get("modelsObservedBesidesRequested", [])) | set(r.get("modelsObservedBesidesRequested", [])))
    cut = []
    for c in out["cases"]:
        for arm, runs in c["arms"].items():
            for i, run in enumerate(runs or []):
                if run.get("cutOff"):
                    cut.append(f"{c['name']} {arm}#{i + 1}: {run['cutOff']}")
    out["suite"]["verification"]["cutOff"] = cut
    out["suite"]["merged"] = merged
    sc = [c["aggregates"]["score"] for c in out["cases"]]
    ds = [c["aggregates"]["delta"] for c in out["cases"] if c["aggregates"].get("delta") is not None]
    out["aggregates"].update({"overallScore": sum(sc) / len(sc), "meanDelta": sum(ds) / len(ds) if ds else None,
                              "overallPassRate": sum(c["aggregates"]["passRate"] for c in out["cases"]) / len(sc)})
    return out


def cmd_merge(a):
    if a.self_test:
        return merge_self_test()
    def agg_of(p):
        p = pathlib.Path(p)
        f = p / "aggregate-result.json" if p.is_dir() else p
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["suite"].get("recordedBy") != RECORDER:
            die(f"{f} was not recorded by {RECORDER}")
        return f.parent.name, d
    if not a.base or not a.replacements or not a.out:
        die("merge needs a base, at least one replacement and --out")
    base_label, base = agg_of(a.base)
    tree_of = lambda h: git("rev-parse", f"{h}:skills") + " " + git("rev-parse", f"{h}:agents")
    try:
        out = merge_results(base, base_label, [agg_of(p) for p in a.replacements], tree_of, add_new=a.add_new)
    except MergeRefused as e:
        die(f"merge refused: {e}", 1)
    d = ROOT / "evals" / "results" / a.out
    d.mkdir(parents=True)
    (d / "aggregate-result.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    (d / "summary.md").write_text(render_table(out, d.name), encoding="utf-8")
    print(f"wrote {d.relative_to(ROOT)}; replaced: " + ", ".join(f"{m['case']} (from {m['from']})" for m in out["suite"]["merged"]))
    if out["suite"]["verification"]["cutOff"]:
        print("run_evals: still cut off (not a baseline yet): " + "; ".join(out["suite"]["verification"]["cutOff"]))
        return 1
    return 0


def merge_self_test():
    def run(score, cut=None):
        return {"score": score, "turns": 1, "durationSeconds": 1, "cutOff": cut, "error": None,
                "graders": [{"name": "g", "passed": score == 1, "withOnly": False}]}
    def case(name, w, wo, cut=None):
        return {"name": name, "maxTurns": 6, "timeoutSeconds": 240,
                "arms": {"with": [run(w, cut)], "without": [run(wo)]},
                "aggregates": {"score": w, "passRate": float(w == 1), "scoreWithout": wo, "delta": w - wo}}
    def agg(head, cases, model="m", effort="high"):
        return {"claudeVersion": "x", "startedAt": "t", "durationSeconds": 10, "costUsd": 1.0, "partial": False,
                "suite": {"model": model, "effort": effort, "gitHead": head, "gitDirty": False, "plugins": [{"version": "1"}],
                          "recordedBy": RECORDER, "verification": {"cutOff": []}, "modelsObservedBesidesRequested": []},
                "cases": cases, "aggregates": {}}
    trees = {"h1": "T", "h2": "T", "h3": "OTHER"}
    base = agg("h1", [case("a", 1, 0), case("b", 0, 0, cut="timeout")])
    base["suite"]["verification"]["cutOff"] = ["b with#1: timeout"]
    failures = []
    out = merge_results(base, "base", [("rep", agg("h2", [case("b", 1, 0)]))], trees.get)
    if out["suite"]["verification"]["cutOff"]:
        failures.append("the replaced cut-off run is still listed")
    m = out["suite"]["merged"]
    if not (len(m) == 1 and m[0]["case"] == "b" and m[0]["replacedRunsCutOff"] == ["with#1"] and m[0]["from"] == "rep"):
        failures.append(f"merge record wrong: {m}")
    if out["aggregates"]["meanDelta"] != 1.0 or out["costUsd"] != 2.0 or base["cases"][1]["aggregates"]["score"] != 0:
        failures.append("aggregates or cost not recomputed, or the base was modified")
    for label, rep in (("model", agg("h2", [case("b", 1, 0)], model="other")),
                       ("skills", agg("h3", [case("b", 1, 0)])),
                       ("cut-off", agg("h2", [case("b", 1, 0, cut="timeout")])),
                       ("unknown case", agg("h2", [case("z", 1, 0)]))):
        try:
            merge_results(base, "base", [("rep", rep)], trees.get)
            failures.append(f"a replacement with a different {label} was accepted")
        except MergeRefused:
            pass
    added = merge_results(base, "base", [("rep", agg("h2", [case("z", 1, 0)]))], trees.get, add_new=True)
    if [c["name"] for c in added["cases"]] != ["a", "b", "z"] or not added["suite"]["merged"][-1].get("added"):
        failures.append("--add-new did not append and record the new case")
    if failures:
        print("merge self-test FAILED:\n  - " + "\n  - ".join(failures))
        return 1
    print("merge self-test: OK (replacement recorded, cut-off cleared, aggregates recomputed; "
          "different model, skills tree, cut-off replacement and unknown case refused)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the suite on a named model and effort")
    r.add_argument("--model", required=True, help="full model id, e.g. claude-opus-5-5")
    r.add_argument("--effort", required=True, choices=EFFORTS)
    r.add_argument("--case", help="case name glob (claude plugin eval --case)")
    r.add_argument("--runs", type=int, help="runs per case and arm (default: each case's `runs`, 3)")
    r.add_argument("-j", "--concurrency", type=int, default=4)
    r.add_argument("--max-cost-usd", type=float)
    t = sub.add_parser("table", help="render a results directory as a baseline table")
    t.add_argument("results")
    t.add_argument("--out", help="write the table here and a JSON sidecar beside it")
    t.add_argument("--drop-removed", action="store_true",
                   help="leave out cases whose evals/<case>/ no longer exists, and name them in the table")
    c = sub.add_parser("compare", help="per-case delta change between two results of one model and effort")
    c.add_argument("before")
    c.add_argument("after")
    m = sub.add_parser("merge", help="replace cases of a result with complete re-runs of the same model, effort and skills")
    m.add_argument("base", nargs="?")
    m.add_argument("replacements", nargs="*")
    m.add_argument("--out", help="name of the merged results directory under evals/results/")
    m.add_argument("--self-test", action="store_true")
    m.add_argument("--add-new", action="store_true",
                   help="also add cases the base does not have (a new case measured alone on the same skills tree)")
    a = ap.parse_args()
    sys.exit({"run": cmd_run, "table": cmd_table, "compare": cmd_compare, "merge": cmd_merge}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
