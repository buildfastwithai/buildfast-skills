#!/usr/bin/env python3
"""convert_svg.py - transform an EXISTING SVG into another style without
rebuilding it (Style Preservation mode).

Sub-commands
  inspect  IN.svg                       structure/palette/stroke report (JSON with --json)
  recolor  IN.svg -o OUT.svg ...        palette transform
      --palette "#0b0221,#ff2a6d,#05d9e8,#d1f7ff"   remap by luminance rank (dark->light)
      --map "#aabbcc=#112233,#fff=#000"             explicit colour swaps (applied first)
      --darken 0.25 | --lighten 0.2                 HSL lightness shift (-1..1 via sign)
      --saturate 1.3                                saturation multiplier
      --hue-shift 20                                degrees
      --grayscale                                   drop saturation entirely
  strokes  IN.svg -o OUT.svg ...        line treatment
      --width-scale 1.5 | --set-width 3
      --linecap round|butt|square  --linejoin round|miter|bevel
      --outline "#111111:3"     add a stroke to every filled shape that has none
      --remove                  remove all strokes (flat / cut-paper look)
  inject   IN.svg -o OUT.svg ...        add style layers to the existing art
      --defs FRAG.xml        elements appended to <defs> (filters, patterns, gradients)
      --underlay FRAG.xml    elements inserted BEFORE the artwork (background, sky, grid)
      --overlay FRAG.xml     elements appended AFTER the artwork (scanlines, grain, vignette)
      --set "#subject:filter=url(#glow)"   set an attribute on a selector (#id, .class or tag)
      --wrap-id subject      wrap all original artwork in <g id="subject"> (so filters/masks can target it)
      --drop-background      remove the original full-canvas background rect(s) (else they hide the underlay)
      --viewbox "0 0 W H"    change canvas (e.g. to add a border)

Fragments are plain SVG elements (no <svg> wrapper needed).

Typical conversion ("make this cyberpunk"):
  inspect  ->  recolor --palette ... ->  strokes --linecap round --width-scale 0.8
           ->  inject --wrap-id subject --defs glow.xml --underlay bg.xml --overlay scan.xml
                       --set "#subject:filter=url(#neon)"
then validate_svg.py + render_svg.py.
"""
from __future__ import annotations

import argparse
import colorsys
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import (  # noqa: E402
    SVG_NS, SHAPE_TAGS, StyleResolver, fnum, hex_to_hsl, iter_elements, local,
    luminance, norm_color, parse_svg, parse_style_attr, parse_viewbox, walk_painted, ids_map,
)
from lxml import etree  # noqa: E402

COLOR_PROPS = ("fill", "stroke", "stop-color", "flood-color", "lighting-color", "color")


def load(path):
    root, err = parse_svg(path)
    if root is None:
        sys.exit("cannot parse %s: %s" % (path, err))
    return root


def save(root, out):
    etree.cleanup_namespaces(root)
    etree.indent(root, space="  ")
    Path(out).write_text(etree.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
    print("wrote", out)


def hex_from_hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, max(0, min(1, l)), max(0, min(1, s)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def color_slots(root):
    """Yield (element, kind, name, raw_value) for every colour-bearing attribute/style entry."""
    for el in iter_elements(root):
        for prop in COLOR_PROPS:
            v = el.get(prop)
            if v is not None:
                yield el, "attr", prop, v
        st = el.get("style")
        if st:
            for k, v in parse_style_attr(st).items():
                if k in COLOR_PROPS:
                    yield el, "style", k, v
        if local(el.tag) == "style" and el.text:
            for m in re.finditer(r"(fill|stroke|stop-color|color)\s*:\s*(#[0-9a-fA-F]{3,8}|rgb[a]?\([^)]*\)|[a-zA-Z]+)", el.text):
                yield el, "css", m.group(1), m.group(2)


def set_slot(el, kind, name, old, new):
    if kind == "attr":
        el.set(name, new)
    elif kind == "style":
        d = parse_style_attr(el.get("style"))
        d[name] = new
        el.set("style", ";".join("%s:%s" % kv for kv in d.items()))
    elif kind == "css":
        el.text = re.sub(r"(%s\s*:\s*)%s" % (re.escape(name), re.escape(old)), lambda m: m.group(1) + new, el.text)


def is_canvas_rect(el, vb, frac=0.95):
    """True for a <rect> that covers (almost) the whole viewBox - i.e. a background."""
    if local(el.tag) != "rect" or vb is None:
        return False
    x, y = fnum(el.get("x")), fnum(el.get("y"))
    w, h = fnum(el.get("width")), fnum(el.get("height"))
    return w >= frac * vb[2] and h >= frac * vb[3] and x <= vb[0] + 0.03 * vb[2] and y <= vb[1] + 0.03 * vb[3]


# ---------------------------------------------------------------- inspect
def cmd_inspect(a):
    root = load(a.file)
    ids = ids_map(root)
    res = StyleResolver(root)
    tags = Counter(local(e.tag) for e in iter_elements(root))
    usage = Counter()
    for el, kind, name, v in color_slots(root):
        c = norm_color(v)
        if c:
            usage[c] += 1
    stroke_w = Counter()
    for el, m in walk_painted(root, ids):
        if (res.get(el, "stroke") or "none") != "none":
            stroke_w[round(fnum(res.get(el, "stroke-width", "1"), 1), 2)] += 1
    palette = [{"color": c, "uses": n, "luminance": round(luminance(c), 3),
                "hue": round(hex_to_hsl(c)[0]), "sat": round(hex_to_hsl(c)[1], 2)} for c, n in usage.most_common()]
    palette.sort(key=lambda p: p["luminance"])
    groups = [{"id": g.get("id"), "children": len([c for c in g if isinstance(c.tag, str)])}
              for g in root.iter("{%s}g" % SVG_NS) if g.get("id")]
    info = {
        "viewBox": parse_viewbox(root),
        "elements": dict(tags),
        "named_groups": groups,
        "palette_dark_to_light": palette,
        "stroke_widths": dict(stroke_w),
        "gradients": tags.get("linearGradient", 0) + tags.get("radialGradient", 0),
        "filters": tags.get("filter", 0),
        "patterns": tags.get("pattern", 0),
        "text": ["".join(t.itertext()).strip() for t in root.iter("{%s}text" % SVG_NS)][:10],
    }
    if a.json:
        print(json.dumps(info, indent=2))
        return
    print("viewBox:", info["viewBox"])
    print("elements:", ", ".join("%s=%d" % kv for kv in sorted(tags.items())))
    print("named groups:", ", ".join("#%s(%d)" % (g["id"], g["children"]) for g in groups) or "none (consider --wrap-id when injecting)")
    print("stroke widths:", dict(stroke_w) or "none (fill-only art)")
    print("gradients=%d filters=%d patterns=%d" % (info["gradients"], info["filters"], info["patterns"]))
    print("palette (dark -> light):")
    for p in palette:
        print("  %s  L=%.3f  hue=%3d sat=%.2f  x%d" % (p["color"], p["luminance"], p["hue"], p["sat"], p["uses"]))


# ---------------------------------------------------------------- recolor
def cmd_recolor(a):
    root = load(a.file)
    slots = list(color_slots(root))
    mapping = {}
    if a.map:
        for kv in a.map.split(","):
            k, v = kv.split("=", 1)
            nk = norm_color(k.strip())
            if nk is None:
                sys.exit("cannot parse colour %r in --map" % k)
            mapping[nk] = v.strip()
    usage = Counter()
    for _e, _k, _n, v in slots:
        c = norm_color(v)
        if c:
            usage[c] += 1
    if a.palette:
        pal = [norm_color(x.strip()) for x in a.palette.split(",")]
        if any(p is None for p in pal):
            sys.exit("bad colour in --palette")
        pal.sort(key=luminance)
        pal_l = [luminance(p) for p in pal]
        unmapped = [c for c in usage if c not in mapping]
        lums = sorted(luminance(c) for c in unmapped)
        # weight by usage so quantiles reflect how much of the art is dark/light
        weighted = sorted(((luminance(c), usage[c]) for c in unmapped))
        total = sum(w for _l, w in weighted) or 1
        run = 0.0
        rank = {}
        for l, w in weighted:
            rank[l] = (run + w / 2) / total
            run += w
        for c in unmapped:
            q = rank[luminance(c)]
            # nearest palette colour by quantile position
            idx = min(len(pal) - 1, int(q * len(pal)))
            mapping[c] = pal[idx]
    adjust = any(x is not None for x in (a.darken, a.lighten, a.saturate, a.hue_shift)) or a.grayscale
    for el, kind, name, v in slots:
        c = norm_color(v)
        if not c:
            continue
        new = mapping.get(c, c)
        if adjust:
            nc = norm_color(new) or c
            h, s, l = hex_to_hsl(nc)
            if a.darken:
                l = l * (1 - a.darken)
            if a.lighten:
                l = l + (1 - l) * a.lighten
            if a.saturate is not None:
                s = min(1.0, s * a.saturate)
            if a.hue_shift:
                h += a.hue_shift
            if a.grayscale:
                s = 0
            new = hex_from_hsl(h, s, l)
        if new != v:
            set_slot(el, kind, name, v, new)
    save(root, a.out)


# ---------------------------------------------------------------- strokes
def cmd_strokes(a):
    root = load(a.file)
    res = StyleResolver(root)
    ids = ids_map(root)
    outline = None
    if a.outline:
        col, _, w = a.outline.partition(":")
        outline = (col, w or "2")
    n = 0
    vb = parse_viewbox(root)
    for el, _m in walk_painted(root, ids):
        if local(el.tag) not in SHAPE_TAGS:
            continue
        if outline and is_canvas_rect(el, vb):
            continue  # never outline the background
        has_stroke = (res.get(el, "stroke") or "none") != "none"
        if a.remove and has_stroke:
            for k in ("stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray"):
                if k in el.attrib:
                    del el.attrib[k]
            el.set("stroke", "none")
            n += 1
            continue
        if not has_stroke:
            if outline and (res.get(el, "fill", "black") or "black") != "none":
                el.set("stroke", outline[0])
                el.set("stroke-width", outline[1])
                has_stroke = True
                n += 1
            else:
                continue
        if a.set_width is not None:
            el.set("stroke-width", str(a.set_width))
        elif a.width_scale is not None:
            el.set("stroke-width", ("%.3f" % (fnum(res.get(el, "stroke-width", "1"), 1) * a.width_scale)).rstrip("0").rstrip("."))
        if a.linecap:
            el.set("stroke-linecap", a.linecap)
        if a.linejoin:
            el.set("stroke-linejoin", a.linejoin)
        n += 1
    print("touched %d shapes" % n)
    save(root, a.out)


# ---------------------------------------------------------------- inject
def load_fragment(path):
    text = Path(path).read_text(encoding="utf-8")
    wrapped = '<svg xmlns="%s" xmlns:xlink="http://www.w3.org/1999/xlink">%s</svg>' % (SVG_NS, text)
    frag, err = parse_svg(wrapped)
    if frag is None:
        sys.exit("bad fragment %s: %s" % (path, err))
    return list(frag)


def select(root, sel):
    if sel.startswith("#"):
        return [e for e in iter_elements(root) if e.get("id") == sel[1:]]
    if sel.startswith("."):
        return [e for e in iter_elements(root) if sel[1:] in (e.get("class") or "").split()]
    return [e for e in iter_elements(root) if local(e.tag) == sel]


def cmd_inject(a):
    root = load(a.file)
    if a.viewbox:
        root.set("viewBox", a.viewbox)
    if a.drop_background:
        vb = parse_viewbox(root)
        dropped = 0
        for el in list(iter_elements(root)):
            par = el.getparent()
            if par is not None and is_canvas_rect(el, vb) and not any(local(x.tag) in ("defs", "clipPath", "mask", "pattern") for x in el.iterancestors()):
                par.remove(el)
                dropped += 1
        print("dropped %d canvas-sized background rect(s)" % dropped)
    art_start = 0
    for i, ch in enumerate(root):
        if isinstance(ch.tag, str) and local(ch.tag) in ("title", "desc", "defs", "metadata"):
            art_start = i + 1
    if a.wrap_id:
        wrapper = etree.Element("{%s}g" % SVG_NS)
        wrapper.set("id", a.wrap_id)
        movers = [ch for ch in root if isinstance(ch.tag, str) and local(ch.tag) not in ("title", "desc", "defs", "metadata", "style")]
        first = list(root).index(movers[0]) if movers else len(root)
        for m in movers:
            wrapper.append(m)
        root.insert(first, wrapper)
    if a.defs:
        defs = next((c for c in root if isinstance(c.tag, str) and local(c.tag) == "defs"), None)
        if defs is None:
            defs = etree.Element("{%s}defs" % SVG_NS)
            root.insert(art_start if art_start else 0, defs)
        for el in load_fragment(a.defs):
            defs.append(el)
    if a.underlay:
        # after title/desc/defs, before artwork
        idx = 0
        for i, ch in enumerate(root):
            if isinstance(ch.tag, str) and local(ch.tag) in ("title", "desc", "defs", "metadata", "style"):
                idx = i + 1
        for off, el in enumerate(load_fragment(a.underlay)):
            root.insert(idx + off, el)
    if a.overlay:
        for el in load_fragment(a.overlay):
            root.append(el)
    for spec in a.set or []:
        sel, _, kv = spec.partition(":")
        k, _, v = kv.partition("=")
        targets = select(root, sel)
        if not targets:
            print("warning: selector %r matched nothing" % sel, file=sys.stderr)
        for t in targets:
            t.set(k, v)
    save(root, a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_inspect)

    p = sub.add_parser("recolor")
    p.add_argument("file")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--palette")
    p.add_argument("--map")
    p.add_argument("--darken", type=float)
    p.add_argument("--lighten", type=float)
    p.add_argument("--saturate", type=float)
    p.add_argument("--hue-shift", type=float, dest="hue_shift")
    p.add_argument("--grayscale", action="store_true")
    p.set_defaults(fn=cmd_recolor)

    p = sub.add_parser("strokes")
    p.add_argument("file")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--width-scale", type=float, dest="width_scale")
    p.add_argument("--set-width", type=float, dest="set_width")
    p.add_argument("--linecap", choices=["round", "butt", "square"])
    p.add_argument("--linejoin", choices=["round", "miter", "bevel"])
    p.add_argument("--outline")
    p.add_argument("--remove", action="store_true")
    p.set_defaults(fn=cmd_strokes)

    p = sub.add_parser("inject")
    p.add_argument("file")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--defs")
    p.add_argument("--underlay")
    p.add_argument("--overlay")
    p.add_argument("--set", action="append")
    p.add_argument("--wrap-id", dest="wrap_id")
    p.add_argument("--drop-background", action="store_true", dest="drop_background",
                   help="remove the original canvas-sized background rect(s) so an --underlay shows through")
    p.add_argument("--viewbox")
    p.set_defaults(fn=cmd_inject)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
