#!/usr/bin/env python3
"""benchmark.py - reproducible motion-graphics benchmarks for comparing AI coding models / agents.

  benchmark.py list
  benchmark.py init agent-explainer ./bench/claude-run1     frozen spec + storyboard + BENCHMARK.md prompt (+ starter)
  benchmark.py run  ./bench/claude-run1 [--preview]         render every benchmark style, QC, determinism check, scorecard
  benchmark.py compare ./bench/run-a ./bench/run-b          side-by-side scorecards

Fairness: spec (duration, fps, format, seed, bpm, audio), scene timings and the style/motion set are frozen by the
benchmark definition (benchmarks/standard.json). The model under test only writes composition.html.
Scores are objective (render success, QC findings, timing adherence, required text, determinism, variety);
visual quality still needs a human (or model) review of out/*__compare.mp4 and the QC sheets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mslib  # noqa: E402

SUITE = mslib.SKILL / "benchmarks" / "standard.json"


def suite():
    return json.loads(SUITE.read_text())


def get(bid):
    for b in suite()["benchmarks"]:
        if b["id"] == bid:
            return b
    raise SystemExit(f"unknown benchmark {bid}; see: benchmark.py list")


def init(bid, d: Path):
    b = get(bid)
    d.mkdir(parents=True, exist_ok=True)
    s0, m0 = b["variants"][0]
    spec = {"name": bid, "title": bid, "brief": b["brief"], "template": b["template"], "style": s0, "motion": m0, "format": b["format"],
            "fps": b["fps"], "duration": b["duration"], "seed": b["seed"], "bpm": b["bpm"],
            "audio": {"music": "auto", "sfx": True, "file": None, "voiceover": None, "lufs": -14}, "vars": {},
            "variants": [{"style": s, "motion": m} for s, m in b["variants"]], "benchmark": {"id": bid, "suite_sha1": hashlib.sha1(json.dumps(b, sort_keys=True).encode()).hexdigest()}}
    (d / "spec.json").write_text(json.dumps(spec, indent=1))
    sb = [f"# Storyboard (frozen) - {bid}", "", f"Brief: {b['brief']}", "", "| scene id | start | end | purpose |", "|---|---|---|---|"]
    sb += [f"| {i} | {a:g} | {e:g} | {p} |" for i, a, e, p in b["scenes"]]
    sb += ["", "Required on-screen text: " + ", ".join(f"'{t}'" for t in b["required_text"])]
    (d / "storyboard.md").write_text("\n".join(sb) + "\n")
    rules = "\n".join(f"- {r}" for r in suite()["rules"])
    (d / "BENCHMARK.md").write_text(f"""# Motion Studio benchmark: {bid}

Give this file to the model under test, verbatim.

## Task
{b['brief']}

Use the Motion Studio skill. The project folder already contains spec.json and storyboard.md (frozen).
Write composition.html so that it follows the storyboard's scene ids and exact timings, then run:

    python3 <skill>/scripts/benchmark.py run {d}

## Rules
{rules}

## Styles it will be rendered in (same composition)
{chr(10).join(f'- {s} + {m} motion' for s, m in b['variants'])}
""")
    (d / "assets").mkdir(exist_ok=True)
    if not (d / "composition.html").exists():
        scenes = json.dumps([{"id": i, "start": a, "end": e, "purpose": p} for i, a, e, p in b["scenes"]])
        (d / "composition.html").write_text(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{bid}</title><link rel="stylesheet" href="/engine/ms.css"></head>
<body><script src="/__spec.js"></script><script src="/engine/ms.js"></script>
<script>
/* BENCHMARK STARTER - replace with the real design. Scene ids and timings are frozen: {scenes} */
MS.boot(C => {{
  const SC = {scenes};
  SC.forEach((sc, i) => {{
    C.scene(sc.id, sc.start, sc.end - sc.start, s => {{ s.bg('auto'); const t = s.text(sc.purpose, {{ size: 'h1', wrap: true, maxWidth: .8 }}); s.enter(t, .2); }});
    if (i) C.transition(SC[i - 1].id, sc.id, {{ type: 'auto' }});
  }});
}});
</script></body></html>
""")
    print(f"benchmark '{bid}' initialised in {d}\n  prompt for the model: {d / 'BENCHMARK.md'}")


def determinism(project: Path, spec, times=(0.5, None, None)):
    """Render the same frames in two fresh browser sessions and compare hashes."""
    from playwright.sync_api import sync_playwright
    import render
    res = mslib.resolve(spec)
    dur = res["duration"]
    ts = [0.5, dur * .5, dur - .25]
    hashes = []
    for _ in range(2):
        srv, url = mslib.serve(project, res)
        with sync_playwright() as pw:
            b, pg, _e = render.open_page(pw, url, res["width"], res["height"])
            hs = []
            for t in ts:
                pg.evaluate("t => window.__ms.render(t)", t)
                hs.append(hashlib.md5(pg.screenshot(type="png")).hexdigest())
            b.close()
        srv.shutdown()
        hashes.append(hs)
    return hashes[0] == hashes[1], ts


def run(d: Path, preview=False):
    spec = mslib.load_spec(d)
    bid = spec.get("benchmark", {}).get("id")
    b = get(bid) if bid else None
    variants = spec["variants"]
    t0 = time.time()
    cmd = [sys.executable, str(Path(__file__).parent / "render.py"), str(d), "--variants", ";".join(f"{v['style']}:{v['motion']}" for v in variants)]
    if preview:
        cmd.append("--preview")
    else:
        cmd.append("--benchmark")
    ok = subprocess.run(cmd).returncode == 0
    render_s = time.time() - t0
    det, ts = determinism(d, spec)
    out = d / "out"
    rows = []
    for v in variants:
        name = f"{spec['name']}__{mslib.variant_name(v['style'], v['motion'])}"
        qc = json.loads((out / f"{name}.qc.json").read_text()) if (out / f"{name}.qc.json").exists() else None
        meta = json.loads((out / f"{name}.meta.json").read_text()) if (out / f"{name}.meta.json").exists() else {}
        F = qc["findings"] if qc else []
        err = sum(f["severity"] == "error" for f in F)
        warn = sum(f["severity"] == "warn" for f in F)
        timing = None
        if b and meta:
            got = {s["id"]: (s["start"], s["end"]) for s in meta["scenes"]}
            miss = [i for i, a, e, _ in b["scenes"] if i not in got or abs(got[i][0] - a) > .05 or abs(got[i][1] - e) > .05]
            timing = 1 - len(miss) / len(b["scenes"])
        texts = " ".join(t.get("text", "") for t in meta.get("textList", [])).lower()
        req = [t for t in (b["required_text"] if b else []) if t.lower() not in texts]
        kinds = {tr["type"] for tr in meta.get("transitions", [])}
        score = 100 - 15 * err - 4 * warn - 20 * (1 - (timing if timing is not None else 1)) - 10 * len(req) - (10 if len(kinds) < 2 else 0) - (0 if det else 20)
        rows.append(dict(variant=f"{v['style']}+{v['motion']}", rendered=bool(qc), qc_errors=err, qc_warnings=warn, timing_adherence=timing,
                         missing_text=req, transition_types=len(kinds), lufs=(qc or {}).get("loudness", {}) and qc["loudness"].get("lufs"),
                         score=max(0, round(score)) if qc else 0))          # no render / no QC report = 0
    report = dict(benchmark=bid, project=str(d), render_ok=ok, render_seconds=round(render_s), deterministic=det, determinism_times=ts,
                  variants=rows, mean_score=round(sum(r["score"] for r in rows) / max(1, len(rows)), 1))
    (d / "benchmark-report.json").write_text(json.dumps(report, indent=1))
    md = [f"# Benchmark report - {bid}", "", f"render ok: {ok} · {report['render_seconds']} s · deterministic: {det} · mean score **{report['mean_score']}**", "",
          "| variant | score | QC errors | QC warnings | timing | missing text | transition types | LUFS |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['variant']} | {r['score']} | {r['qc_errors']} | {r['qc_warnings']} | {r['timing_adherence']} | {', '.join(r['missing_text']) or '-'} | {r['transition_types']} | {r['lufs']} |" for r in rows]
    md += ["", "Objective score only. Review out/*__compare.mp4 and out/*.qc-sheet.png for visual quality."]
    (d / "benchmark-report.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def compare(dirs):
    for d in dirs:
        r = json.loads((Path(d) / "benchmark-report.json").read_text())
        print(f"{d}: mean {r['mean_score']}  deterministic={r['deterministic']}  " + "  ".join(f"{v['variant']}={v['score']}" for v in r["variants"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("init"); p.add_argument("id"); p.add_argument("dir")
    p = sub.add_parser("run"); p.add_argument("dir"); p.add_argument("--preview", action="store_true")
    p = sub.add_parser("compare"); p.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    if a.cmd == "list":
        for b in suite()["benchmarks"]:
            print(f"{b['id']:18} {b['duration']:>4}s {b['format']:5} styles: " + ", ".join(f"{s}+{m}" for s, m in b["variants"]))
            print(f"{'':18} {b['brief']}")
    elif a.cmd == "init":
        init(a.id, Path(a.dir).resolve())
    elif a.cmd == "run":
        run(Path(a.dir).resolve(), a.preview)
    else:
        compare(a.dirs)


if __name__ == "__main__":
    main()
