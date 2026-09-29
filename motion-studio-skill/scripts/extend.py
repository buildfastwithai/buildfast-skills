#!/usr/bin/env python3
"""extend.py - add styles, motion languages, templates and animation primitives; lint the registries.

  extend.py lint                                   validate every registry (run after any edit; must print 0 errors)
  extend.py new-style ID --name "Name" --family retro --from vhs [--alias a --alias b]
  extend.py new-motion ID --name "Name" --from snappy [--alias ...]
  extend.py new-template ID --name "Name" --from product-ad [--alias ...]
  extend.py new-preset NAME                        stub for a reusable animation primitive in engine/extensions/NAME.js
  extend.py new-transition NAME                    stub for a transition in engine/extensions/NAME.js

New entries are copied from an existing one (--from) so every field exists; edit the copy, then run lint.
Files in engine/extensions/*.js are appended to ms.js automatically when projects are served/rendered.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mslib  # noqa: E402

EXT = mslib.ENGINE / "extensions"
ENGINE_SRC = (mslib.ENGINE / "ms.js").read_text()
PRESETS = set(re.findall(r"\bP\.(\w+)\s*=", ENGINE_SRC)) | {"none"}
TRANSITIONS = set(re.findall(r"\bTR\.(\w+)\s*=", ENGINE_SRC))
BACKGROUNDS = set(re.findall(r"\bBG\.(\w+)\s*=", ENGINE_SRC)) | {"auto"}
OVERLAYS = set(re.findall(r"\bOV\.(\w+)\s*=", ENGINE_SRC))
EASE_NAMES = set(re.findall(r"^\s{4}(\w+):", ENGINE_SRC[ENGINE_SRC.index("const NAMED"):ENGINE_SRC.index("MS.ease = function")], re.M)) | \
    set(re.findall(r"\b(\w+):\s*(?:p =>|back|elastic|bounce|bezier)", ENGINE_SRC[ENGINE_SRC.index("const NAMED"):ENGINE_SRC.index("MS.ease = function")]))
for f in EXT.glob("*.js") if EXT.exists() else []:
    src = f.read_text()
    PRESETS |= set(re.findall(r"MS\.presets\.(\w+)\s*=", src))
    TRANSITIONS |= set(re.findall(r"MS\.transitions\.(\w+)\s*=", src))
    BACKGROUNDS |= set(re.findall(r"MS\.backgrounds\.(\w+)\s*=", src))
FONT_CSS = (mslib.ENGINE / "fonts.css").read_text()
FONTS = {}
for m in re.finditer(r"font-family:\s*'([^']+)';[^}]*font-weight:\s*(\d+)", FONT_CSS):
    FONTS.setdefault(m.group(1), set()).add(m.group(2))


def ease_ok(e):
    if e in EASE_NAMES:
        return True
    return bool(re.match(r"^(bezier|cubic-bezier|spring|steps|back|elastic)\([\d.,\s-]+\)$", str(e)))


def lint() -> int:
    errs, warns = [], []
    S, M, T = mslib.styles(), mslib.motions(), mslib.templates()
    alias_owner = {}
    for sid, s in S.items():
        for k in ("id", "name", "family", "aliases", "description", "palette", "fonts", "type", "texture", "background", "transitions", "sound", "motion_default", "do", "dont", "assets", "camera"):
            if k not in s:
                errs.append(f"style {sid}: missing '{k}'")
        for k in ("bg", "fg", "accent", "accent2", "accent3", "muted"):
            if k not in s.get("palette", {}):
                errs.append(f"style {sid}: palette.{k} missing")
            elif not re.match(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$", s["palette"][k]):
                errs.append(f"style {sid}: palette.{k} '{s['palette'][k]}' is not #rrggbb")
        for role in ("display", "body"):
            fam, _, w = str(s.get("fonts", {}).get(role, "")).partition(":")
            if fam not in FONTS:
                errs.append(f"style {sid}: font '{fam}' is not bundled in engine/fonts (add the woff2 + @font-face to fonts.css)")
            elif (w or "400").rstrip("i") not in FONTS[fam]:
                warns.append(f"style {sid}: {fam} weight {w} not bundled (has {sorted(FONTS[fam])}) - browser will synthesise")
        bg = s.get("background")
        if bg not in BACKGROUNDS:
            errs.append(f"style {sid}: background '{bg}' unknown (engine has {sorted(BACKGROUNDS)})")
        for tx in s.get("texture", []):
            if tx.split(":")[0] not in OVERLAYS:
                errs.append(f"style {sid}: texture overlay '{tx}' unknown")
        for tr in s.get("transitions", {}).get("prefer", []) + s.get("transitions", {}).get("avoid", []):
            if tr not in TRANSITIONS:
                errs.append(f"style {sid}: transition '{tr}' unknown")
        if s.get("motion_default") not in M:
            errs.append(f"style {sid}: motion_default '{s.get('motion_default')}' unknown")
        for a in s.get("aliases", []):
            if a in alias_owner and alias_owner[a] != sid:
                warns.append(f"alias '{a}' used by both {alias_owner[a]} and {sid}")
            alias_owner[a] = sid
    for mid, m in M.items():
        for k in ("id", "name", "aliases", "description", "ease", "dur", "stagger", "camera", "transitions", "enter", "exit", "pacing", "principles"):
            if k not in m:
                errs.append(f"motion {mid}: missing '{k}'")
        for k, e in m.get("ease", {}).items():
            if not ease_ok(e):
                errs.append(f"motion {mid}: ease.{k} '{e}' not understood by MS.ease")
        for k in ("enter", "exit"):
            if m.get(k) not in PRESETS:
                errs.append(f"motion {mid}: {k} preset '{m.get(k)}' unknown")
        for tr in m.get("transitions", {}).get("prefer", []) + m.get("transitions", {}).get("avoid", []):
            if tr not in TRANSITIONS:
                errs.append(f"motion {mid}: transition '{tr}' unknown")
    for tid, t in T.items():
        for k in ("id", "name", "aliases", "default_duration", "default_format", "default_style", "default_motion", "purpose", "beats", "pacing"):
            if k not in t:
                errs.append(f"template {tid}: missing '{k}'")
        tot = sum(b.get("share", 0) for b in t.get("beats", []))
        if abs(tot - 1) > .02:
            errs.append(f"template {tid}: beat shares sum to {tot:.2f} (must be 1.0)")
        if t.get("default_style") not in S:
            errs.append(f"template {tid}: default_style '{t.get('default_style')}' unknown")
        if t.get("default_motion") not in M:
            errs.append(f"template {tid}: default_motion '{t.get('default_motion')}' unknown")
        if t.get("default_format") not in mslib.formats()["formats"]:
            errs.append(f"template {tid}: default_format unknown")
        for b in t.get("beats", []):
            for k in ("id", "share", "purpose", "visual", "camera", "animation", "typography", "transition", "audio", "energy", "intent"):
                if k not in b:
                    errs.append(f"template {tid} beat {b.get('id')}: missing '{k}'")
    for e in errs:
        print("ERROR", e)
    for w in warns:
        print("warn ", w)
    print(f"{len(S)} styles, {len(M)} motion languages, {len(T)} templates, {len(PRESETS)} presets, {len(TRANSITIONS)} transitions, "
          f"{len(BACKGROUNDS)} backgrounds, {len(OVERLAYS)} overlays: {len(errs)} errors, {len(warns)} warnings")
    return 1 if errs else 0


def write_json(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def new_style(a):
    S = mslib.styles()
    if a.id in S:
        sys.exit(f"style {a.id} exists")
    base = copy.deepcopy(S[a.base])
    base.pop("_file", None)
    base.update(id=a.id, name=a.name or a.id.replace("-", " ").title(), family=a.family or base["family"],
                aliases=a.alias or [a.id.replace("-", " ")], weak_aliases=[], description=f"TODO: describe the {a.name or a.id} visual language")
    f = mslib.STYLE_DIR / f"{base['family']}.json"
    data = json.loads(f.read_text()) if f.exists() else {"family": base["family"], "styles": []}
    data["styles"].append(base)
    write_json(f, data)
    print(f"added style '{a.id}' to {f.name} (copied from {a.base}). Edit palette, fonts, type, texture, background, transitions, sound, do/dont, then: extend.py lint")


def new_motion(a):
    M = mslib.motions()
    if a.id in M:
        sys.exit(f"motion {a.id} exists")
    base = copy.deepcopy(M[a.base])
    base.update(id=a.id, name=a.name or a.id.title(), aliases=a.alias or [a.id], description="TODO: how things move in this language")
    data = json.loads(mslib.MOTION_FILE.read_text())
    data["motions"].append(base)
    write_json(mslib.MOTION_FILE, data)
    print(f"added motion '{a.id}' (copied from {a.base}). Tune ease/dur/stagger/camera/transitions/signature channels, then: extend.py lint")


def new_template(a):
    T = mslib.templates()
    if a.id in T:
        sys.exit(f"template {a.id} exists")
    base = copy.deepcopy(T[a.base])
    base.update(id=a.id, name=a.name or a.id.replace("-", " ").title(), aliases=a.alias or [a.id.replace("-", " ")], purpose="TODO: what this video type is for")
    write_json(mslib.TEMPLATE_DIR / f"{a.id}.json", base)
    print(f"added template '{a.id}' (copied from {a.base}). Rewrite beats (shares must sum to 1), then: extend.py lint")


STUB_PRESET = """/* {name} - custom animation primitive. Loaded automatically after ms.js.
   Use in a composition:  s.anim(node, '{name}', at, {{ dur: .6 }})
   s.tween(node, at, dur, ease, fn) calls fn(easedProgress, state, rawProgress, secondsSinceStart) every frame;
   add to the per-frame state (x, y, z, s, sx, sy, r, rx, ry, skx, o, blur, clip, track, filter, bright) - never set styles directly. */
MS.presets.{name} = (s, n, at, o) => {{
  const dur = o.dur != null ? o.dur : s.M.dur.enter, ease = o.ease || s.M.ease.enter, dist = (o.dist || s.M.dist) * s.C.u;
  s.tween(n, at, dur, ease, (e, st) => {{ st.o *= e; st.y += (1 - e) * dist; st.r += (1 - e) * (o.deg || 6); }});
}};
"""
STUB_TRANSITION = """/* {name} - custom transition. Loaded automatically after ms.js.
   Use:  C.transition('a', 'b', {{ type: '{name}', dur: .6 }})
   Called every frame of the transition window with p = 0..1; style tr.a.root (outgoing) and tr.b.root (incoming).
   Styles are reset every frame, so write complete values. Optional overlay elements go in C.fx (cleared per frame). */
MS.transitions.{name} = (C, tr, p, o) => {{
  const a = tr.a.root.style, b = tr.b.root.style, e = MS.ease(C.motion.ease.move)(p);
  b.zIndex = 2; b.clipPath = `inset(${{(1 - e) * 50}}% 0 ${{(1 - e) * 50}}% 0)`;   // horizontal split opening
  a.filter = `brightness(${{1 - e * .6}})`;
}};
"""


def new_js(a, kind):
    EXT.mkdir(exist_ok=True)
    f = EXT / f"{a.name}.js"
    if f.exists():
        sys.exit(f"{f} exists")
    f.write_text((STUB_PRESET if kind == "preset" else STUB_TRANSITION).format(name=a.name))
    print(f"wrote {f} - edit it, then use it by name. It is appended to ms.js when projects are served.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint")
    for c, default in (("new-style", "minimal"), ("new-motion", "smooth"), ("new-template", "explainer")):
        p = sub.add_parser(c)
        p.add_argument("id")
        p.add_argument("--name")
        p.add_argument("--from", dest="base", default=default)
        p.add_argument("--alias", action="append")
        if c == "new-style":
            p.add_argument("--family")
    for c in ("new-preset", "new-transition"):
        p = sub.add_parser(c)
        p.add_argument("name")
    a = ap.parse_args()
    if a.cmd == "lint":
        sys.exit(lint())
    {"new-style": new_style, "new-motion": new_motion, "new-template": new_template}.get(a.cmd, lambda x: new_js(x, "preset" if a.cmd == "new-preset" else "transition"))(a)


if __name__ == "__main__":
    main()
