#!/usr/bin/env python3
"""plan.py - turn a natural-language video brief into a Motion Studio plan (and optionally a runnable project).

  plan.py "Create a 20 second cyberpunk product ad for an AI coding tool with cinematic motion"
  plan.py "<brief>" --scaffold ./videos/ai-ad          write spec.json + storyboard.md + composition.html (renders as-is)
  plan.py "<brief>" --json
  plan.py --list styles|motion|templates|formats       plan.py --show cyberpunk | cinematic | product-ad

The brief is split into three independent layers - VISUAL STYLE (look), MOTION LANGUAGE (how things move) and
VIDEO TYPE (template: structure/beats) - plus format, duration, fps, audio and mode (single / multi / transform /
benchmark).  Missing pieces get sensible defaults, which the plan lists explicitly so they can be overridden.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mslib  # noqa: E402

AMBIG_STYLE_MOTION = {"cinematic", "organic", "glitch", "glitchy", "minimal", "calm", "energetic", "mechanical", "stop motion", "stop-motion"}
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def phrase_re(p):
    return re.compile(r"(?<![a-z0-9])" + re.escape(p).replace(r"\ ", r"[\s-]+") + r"(?![a-z0-9])")


def find(text, table):
    """Longest-match alias search. table: id -> [aliases]. Returns [(id, alias, span)] in text order, non-overlapping."""
    cands = []
    for i, al in table.items():
        for a in al:
            for m in phrase_re(mslib.norm(a)).finditer(text):
                cands.append((m.start(), -(m.end() - m.start()), i, a, m.span()))
    cands.sort()
    out, used = [], []
    for st, _, i, a, sp in sorted(cands, key=lambda c: (c[1], c[0])):
        if any(not (sp[1] <= u0 or sp[0] >= u1) for u0, u1 in used):
            continue
        used.append(sp)
        out.append((i, a, sp))
    out.sort(key=lambda x: x[2][0])
    seen, res = set(), []
    for i, a, sp in out:
        if i not in seen:
            seen.add(i)
            res.append((i, a, sp))
    return res


def plan(brief: str) -> dict:
    text = mslib.norm(brief)
    S, M, T, FM = mslib.styles(), mslib.motions(), mslib.templates(), mslib.formats()
    notes, defaults = [], []
    # --- mode
    mode = "single"
    mcount = re.search(r"\b(\d+|two|three|four|five|six)\s+(?:different\s+)?(?:visual\s+)?(styles|versions|variations|looks)\b", text)
    if mcount or re.search(r"\bsame video in\b|\bmultiple styles\b|\bmulti[- ]version", text):
        mode = "multi"
    if re.search(r"\b(make|convert|turn|transform|restyle)\s+(this|the|my|it|that)\b.*\b(more|into|to|feel|look|style)\b", text) or re.search(r"\bmore cinematic\b|\bfeel more\b", text):
        mode = "transform" if mode == "single" else mode
        notes.append("transform mode: edit the existing project's spec (style/motion) and only the scenes that need new assets; without an existing project this builds a new one")
    if re.search(r"\bbenchmark\b", text):
        mode = "benchmark"
    # --- templates (video type)
    tt = find(text, {i: t["aliases"] + [t["name"].lower()] for i, t in T.items()})
    # --- motion: explicit "X motion" first
    mot_table = {i: m["aliases"] for i, m in M.items()}
    motions = []
    for i, a, sp in find(text, mot_table):
        after = text[sp[1]:sp[1] + 14]
        explicit = bool(re.match(r"\s*(motion|movement|animation|timing|feel|pacing|energy)\b", after)) or a not in AMBIG_STYLE_MOTION
        motions.append((i, a, sp, explicit))
    # --- styles
    sty_table = {i: s["aliases"] + [s["name"].lower()] for i, s in S.items()}
    styles = find(text, sty_table)
    exp_mot = [sp for (_, _, sp, ex) in motions if ex]
    styles = [x for x in styles if not any(not (x[2][1] <= m0 or x[2][0] >= m1) for m0, m1 in exp_mot)]
    tpl_spans = [sp for (_, _, sp) in tt]
    on_tpl = [x for x in styles if any(not (x[2][1] <= t0 or x[2][0] >= t1) for t0, t1 in tpl_spans)]
    if len(styles) > len(on_tpl):                      # a template word ("documentary", "trailer") is not a style when a real style is named
        styles = [x for x in styles if x not in on_tpl]
    if not styles:                                     # weak aliases ("ai", "tech", "cinematic", "dark") only when nothing else matched
        styles = [x for x in find(text, {i: s.get("weak_aliases", []) for i, s in S.items()}) if not any(not (x[2][1] <= m0 or x[2][0] >= m1) for m0, m1 in exp_mot)][:1]
    # remove style hits that are really template words ("infographic" both) - keep style if also template (they coexist)
    # resolve style/motion ambiguity ("cinematic", "glitch", "organic", "calm"...)
    mot_spans = {sp for (_, _, sp, ex) in motions if ex}
    styles = [x for x in styles if x[2] not in mot_spans]
    amb_styles = [x for x in styles if x[1] in AMBIG_STYLE_MOTION]
    firm_styles = [x for x in styles if x[1] not in AMBIG_STYLE_MOTION]
    final_motions = [(i, a) for (i, a, sp, ex) in motions if ex]
    for (i, a, sp) in amb_styles:
        mot_twin = next((m for m in motions if m[2] == sp), None)
        if firm_styles and mot_twin and not any(m[0] == mot_twin[0] for m in final_motions):
            final_motions.append((mot_twin[0], mot_twin[1]))          # "cyberpunk ... cinematic" -> cinematic is motion
        else:
            firm_styles.append((i, a, sp))
    # ambiguous motion words that had no style twin
    for (i, a, sp, ex) in motions:
        if not ex and not any(sp == st[2] for st in styles) and not any(m[0] == i for m in final_motions):
            final_motions.append((i, a))
    firm_styles.sort(key=lambda x: x[2][0])
    style_ids = [x[0] for x in firm_styles]
    motion_ids = list(dict.fromkeys(m[0] for m in final_motions))
    # "infographic" is both a style and a template: fine.
    # --- template choice
    template = tt[0][0] if tt else None
    if not template:
        if re.search(r"\b(explain|explaining|how (does|do|it)|what is|why)\b", text):
            template = "explainer"
        elif re.search(r"\b(product|app|tool|launch|brand|startup|saas)\b", text):
            template = "product-ad"
        elif re.search(r"\blogo\b", text):
            template = "logo-reveal"
        else:
            template = "kinetic-typography" if re.search(r"\b(quote|words|text|typography|message)\b", text) else "explainer"
        defaults.append(f"video type -> {template} (inferred)")
    tpl = T[template]
    # --- format
    fmt = None
    for k, f in FM["formats"].items():
        if any(phrase_re(mslib.norm(a)).search(text) for a in f["aliases"]):
            fmt = k
            break
    m = re.search(r"\b(\d{3,4})\s*[x×]\s*(\d{3,4})\b", text)
    custom = (int(m.group(1)), int(m.group(2))) if m else None
    if not fmt and not custom:
        fmt = tpl["default_format"]
        defaults.append(f"format -> {fmt} (template default)")
    # --- duration
    dur = None
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:-|\s)?(s|sec|secs|second|seconds)\b", text)
    if m:
        dur = float(m.group(1))
    m2 = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:-|\s)?(m|min|mins|minute|minutes)\b", text)
    if m2:
        dur = float(m2.group(1)) * 60
    if not dur:
        dur = tpl["default_duration"]
        defaults.append(f"duration -> {dur:g}s (template default)")
    # --- style / motion defaults
    if not style_ids:
        style_ids = [tpl["default_style"]]
        defaults.append(f"style -> {style_ids[0]} (template default; say a style to change it)")
    if not motion_ids:
        motion_ids = [S[style_ids[0]]["motion_default"]] if S[style_ids[0]]["motion_default"] != "smooth" else [tpl["default_motion"]]
        defaults.append(f"motion -> {motion_ids[0]} (style/template default)")
    if len(style_ids) > 3:
        notes.append("more than 3 styles named - using the first 3 as primary/secondary/accent (multi mode needs 'in N styles')")
    # --- audio
    music = "auto"
    if re.search(r"\b(no music|without music|silent|no audio|mute)\b", text):
        music = "none"
    vo = bool(re.search(r"\b(voice ?over|narration|narrated|narrator|voiced)\b", text)) and not re.search(r"\bno (voice ?over|narration)\b", text)
    if vo:
        notes.append("voice-over requested: no TTS engine is bundled - put a recorded VO file in the project and set spec.audio.voiceover (captions are generated either way)")
    fps = 24 if (S[style_ids[0]]["family"] == "cinematic" and "cinematic" in motion_ids) else 30
    if "stop-motion" in motion_ids or style_ids[0] in ("stop-motion",):
        fps = 24
    # --- multi-version picks
    variants = []
    if mode in ("multi", "benchmark"):
        n = int(mcount.group(1)) if mcount and mcount.group(1).isdigit() else NUM.get(mcount.group(1), 3) if mcount else 3
        listed = style_ids[:]
        if len(listed) < n:
            pool = ["minimal", "cyberpunk", "vhs", "anime", "luxury", "infographic", "paper-cutout", "blueprint", "retro-futurism", "comic-book", "documentary", "gradient-abstract"]
            fams = {S[x]["family"] for x in listed}
            for p in pool:
                if len(listed) >= n:
                    break
                if p not in listed and S[p]["family"] not in fams:
                    listed.append(p)
                    fams.add(S[p]["family"])
        for sid in listed[:n]:
            variants.append({"style": sid, "motion": motion_ids[0] if len(motion_ids) == 1 and mode != "benchmark" else S[sid]["motion_default"]})
        style_ids = [variants[0]["style"]]
    subject = re.sub(r"\b\d+\s*[:x]\s*\d+\b", " ", text)
    subject = re.sub(r"\b(create|make|generate|produce|render|build|design|a|an|the|video|animation|motion graphics?|in|with|style|motion|about|for|of|second|seconds|sec|s|\d+)\b", " ", subject)
    for x in firm_styles:
        subject = subject.replace(x[1], " ")
    subject = re.sub(r"\b\d+\s*:\s*\d+\b|\b(vertical|horizontal|square|portrait|landscape|widescreen|" + "|".join(map(re.escape, mslib.motions())) + r")\b", " ", subject)
    subject = re.sub(r"\s*,(\s*,)+", ",", re.sub(r"\s+", " ", subject)).strip(" ,.-:")[:80]
    return dict(brief=brief, mode=mode, template=template, style=style_ids, motion=motion_ids, format=fmt, custom_size=custom,
                duration=dur, fps=fps, music=music, voiceover=vo, variants=variants, subject=subject, defaults=defaults, notes=notes)


def beats_timed(tpl, dur):
    t, out = 0.0, []
    for b in tpl["beats"]:
        d = round(b["share"] * dur, 2)
        out.append(dict(b, start=round(t, 2), end=round(t + d, 2)))
        t += d
    out[-1]["end"] = dur
    return out


def describe(p):
    S, M, T = mslib.styles(), mslib.motions(), mslib.templates()
    st, mo, tp = mslib.blend_styles(p["style"]), mslib.blend_motions(p["motion"]), T[p["template"]]
    size = p["custom_size"] or (mslib.formats()["formats"][p["format"]]["width"], mslib.formats()["formats"][p["format"]]["height"])
    L = [f"# Motion plan  ({p['mode']} mode)", "",
         f"- **video type** : {tp['name']} (`{p['template']}`) - {tp['purpose']}",
         f"- **visual style**: {' + '.join(S[s]['name'] for s in p['style'])} (`{'+'.join(p['style'])}`)" + ("  - primary owns type/layout/texture, secondary brings palette & mood" if len(p['style']) > 1 else ""),
         f"- **motion**     : {' + '.join(M[m]['name'] for m in p['motion'])} (`{'+'.join(p['motion'])}`)" + ("  - primary owns easing/timing, secondary adds its signature channels" if len(p['motion']) > 1 else ""),
         f"- **format**     : {p['format'] or 'custom'} {size[0]}x{size[1]} @ {p['fps']} fps, {p['duration']:g}s",
         f"- **audio**      : music={p['music']} ({st['sound']['music']} @ {st['sound']['bpm']} bpm), sfx on cues" + (", voice-over: needs a recorded file" if p["voiceover"] else ""),
         f"- **subject**    : {p['subject'] or '(from brief)'}"]
    if p["variants"]:
        L.append("- **variants**   : " + "; ".join(f"{v['style']}:{v['motion']}" for v in p["variants"]) + "  (same script, scenes, timing)")
    if p["defaults"]:
        L.append("- defaults applied: " + "; ".join(p["defaults"]))
    for n in p["notes"]:
        L.append(f"- NOTE: {n}")
    L += ["", f"## Style brief - {st['name'] if '+' not in st['id'] else st['id']}", st["description"],
          f"- palette: bg {st['palette']['bg']}, fg {st['palette']['fg']}, accents {st['palette']['accent']} {st['palette']['accent2']} {st['palette']['accent3']}",
          f"- type: display {st['fonts']['display']}, body {st['fonts']['body']}, case {st['type']['case']}, tracking {st['type']['tracking']}",
          f"- texture: {', '.join(st['texture']) or 'none'}; background: {st['background']}; camera: {st['camera']}",
          f"- assets: {', '.join(st['assets'])}", f"- do: {'; '.join(st['do'])}", f"- avoid: {'; '.join(st['dont'])}",
          f"- transitions: prefer {', '.join(st['transitions']['prefer'])}; avoid {', '.join(st['transitions']['avoid'])}", "",
          f"## Motion brief - {mo['name'] if '+' not in mo['id'] else mo['id']}", mo["description"],
          f"- ease: enter {mo['ease']['enter']}, exit {mo['ease']['exit']}, move {mo['ease']['move']}, emphasis {mo['ease']['emphasis']}",
          f"- durations: enter {mo['dur']['enter']}s, exit {mo['dur']['exit']}s, hold >= {mo['dur']['hold']}s; avg shot {mo['pacing']['avg_shot']}s (min {mo['pacing']['min_shot']}s)",
          f"- signature: glitch {mo['glitch']}, jitter {mo['jitter']}, stepped {mo['step_fps'] or 'no'} fps, camera push {mo['camera']['push']}, shake {mo['camera']['shake']}",
          f"- principles: {'; '.join(mo['principles'])}", "",
          f"## Beat structure - {tp['name']} ({tp['pacing']})"]
    for b in beats_timed(tp, p["duration"]):
        L.append(f"- {b['start']:5.2f}-{b['end']:5.2f}s **{b['id']}** (energy {b['energy']}) {b['purpose']} | visual: {b['visual']} | camera: {b['camera']} | type: {b['typography']} | out: {b['transition']} | audio: {b['audio']}")
    L += ["", "Next: write the storyboard (reference/storyboard.md), then build composition.html (reference/engine-api.md)."]
    return "\n".join(L)


# ------------------------------------------------------------------ scaffold
STARTER = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title><link rel="stylesheet" href="/engine/ms.css"></head>
<body>
<script src="/__spec.js"></script>
<script src="/engine/ms.js"></script>
<script>
/* {title} - generated starter. Replace each scene with the storyboard's real design (reference/engine-api.md).
   Every visual decision reads theme/motion tokens, so --style/--motion variants keep working. */
MS.boot(C => {{
  const V = C.vars, beats = {beats};
  beats.forEach((b, i) => {{
    C.scene(b.id, b.start, b.end - b.start, s => {{
      s.bg(i % 2 ? 'auto' : 'radial');
      const head = s.text(V.headlines && V.headlines[i] || b.purpose, {{ size: i === 0 ? 'display' : 'h1', y: .45, wrap: true, maxWidth: .85, split: 'words' }});
      s.anim(head, 'wordReveal', .15);
      const sub = s.text(b.id.toUpperCase(), {{ size: 'caption', font: 'mono', y: .8, color: 'var(--accent)', tracking: .3 }});
      s.enter(sub, .5);
      if (i < beats.length - 1) s.exit(head, b.end - b.start - .45, {{ dur: .3 }});
      s.push();
    }}, {{ energy: b.energy, purpose: b.purpose }});
    if (i) C.transition(beats[i - 1].id, b.id, {{ type: 'auto', intent: beats[i - 1].intent }});
  }});
}});
</script>
</body></html>
"""


def scaffold(p, outdir: Path, name=None):
    outdir.mkdir(parents=True, exist_ok=True)
    T = mslib.templates()
    tp = T[p["template"]]
    beats = beats_timed(tp, p["duration"])
    spec = {"name": name or outdir.name, "title": p["subject"] or outdir.name, "brief": p["brief"], "template": p["template"],
            "style": "+".join(p["style"]), "motion": "+".join(p["motion"]), "format": p["format"] or "custom", "fps": p["fps"], "duration": p["duration"], "seed": 1234,
            "audio": {"music": p["music"], "sfx": True, "file": None, "voiceover": None, "lufs": -14},
            "vars": {"headlines": [b["purpose"] for b in beats]}, "variants": p["variants"]}
    if p["custom_size"]:
        spec["width"], spec["height"] = p["custom_size"]
    (outdir / "spec.json").write_text(json.dumps(spec, indent=1))
    sb = [f"# Storyboard - {spec['title']}", "", f"Brief: {p['brief']}", "",
          f"Type {p['template']} · style {spec['style']} · motion {spec['motion']} · {spec['format']} · {p['duration']:g}s @ {p['fps']} fps", "",
          "Concept (one paragraph, the visual idea / metaphor): TODO", ""]
    for i, b in enumerate(beats, 1):
        sb += [f"## Scene {i:02d} - {b['id']}", f"{b['start']:.2f}-{b['end']:.2f}s", "",
               f"Purpose: {b['purpose']}", f"Visual: {b['visual']}", f"Camera: {b['camera']}", f"Animation: {b['animation']}",
               f"Typography: {b['typography']}", f"Transition out: {b['transition']}", f"Audio: {b['audio']}", ""]
    (outdir / "storyboard.md").write_text("\n".join(sb))
    js_beats = json.dumps([{k: b[k] for k in ("id", "start", "end", "purpose", "energy", "intent")} for b in beats])
    (outdir / "composition.html").write_text(STARTER.format(title=spec["title"], beats=js_beats))
    (outdir / "assets").mkdir(exist_ok=True)
    return spec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--scaffold")
    ap.add_argument("--name")
    ap.add_argument("--list", choices=["styles", "motion", "templates", "formats"])
    ap.add_argument("--show")
    a = ap.parse_args()
    if a.list:
        if a.list == "styles":
            fam = {}
            for s in mslib.styles().values():
                fam.setdefault(s["family"], []).append(f"{s['id']}")
            for f, ids in fam.items():
                print(f"{f:13s} " + ", ".join(ids))
        elif a.list == "motion":
            for m in mslib.motions().values():
                print(f"{m['id']:12s} {m['description']}")
        elif a.list == "templates":
            for t in mslib.templates().values():
                print(f"{t['id']:19s} {t['default_duration']:>3}s {t['default_format']:5s} {t['purpose']}")
        else:
            for k, f in mslib.formats()["formats"].items():
                print(f"{k:5s} {f['width']}x{f['height']}  {f['layout']}")
        return
    if a.show:
        for reg in (mslib.styles(), mslib.motions(), mslib.templates()):
            if a.show in reg:
                d = {k: v for k, v in reg[a.show].items() if not k.startswith("_")}
                print(json.dumps(d, indent=1))
                return
        sys.exit(f"unknown id {a.show}")
    if not a.brief:
        ap.error("brief required")
    p = plan(a.brief)
    if a.json:
        print(json.dumps(p, indent=1))
    else:
        print(describe(p))
    if a.scaffold:
        spec = scaffold(p, Path(a.scaffold), a.name)
        print(f"\nscaffolded {a.scaffold}: spec.json, storyboard.md, composition.html  ->  python3 {Path(__file__).parent}/render.py {a.scaffold} --stills")


if __name__ == "__main__":
    main()
