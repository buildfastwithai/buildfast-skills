#!/usr/bin/env python3
"""text_to_path.py - outline text as SVG <path> data, so logos/posters don't depend on installed fonts.

SVG fonts are never embedded; a <text> element renders in whatever font the viewer has.
For logos, posters and anything handed off for print, outline the lettering with this tool.

Needs fontTools (pip install fonttools; add brotli for .woff2). Any .ttf/.otf/.woff/.woff2 works.

CLI
  text_to_path.py FONT "TEXT" [--size 96] [--x 0] [--y 0] [--anchor start|middle|end]
                  [--tracking 0] [--width W] [--fill "#111"] [--id wordmark]
  -> prints one <path> element (paste into your SVG).  --width fits the text to W units by
     adjusting the tracking (like textLength="W" lengthAdjust="spacing").
  --d-only prints just the path data.  --glyphs prints a <g aria-label> with one <path> per glyph
  (recommended for long titles: small paths, letters individually editable).

Python
  sys.path.insert(0, S); from text_to_path import text_path, text_group
  d, width = text_path("Anton-Regular.ttf", "HIGHLANDS", size=120, x=400, y=1000, anchor="middle")
"""
from __future__ import annotations

import argparse
import sys
from functools import lru_cache

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError:  # pragma: no cover
    sys.exit("text_to_path.py needs fontTools: pip install fonttools brotli")


@lru_cache(maxsize=16)
def _font(path):
    f = TTFont(path)
    return f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm


def _kern_pairs(font):
    """Old-style 'kern' table pairs (GPOS kerning is ignored; tracking usually dominates in display type)."""
    pairs = {}
    if "kern" in font:
        for sub in font["kern"].kernTables:
            pairs.update(getattr(sub, "kernTable", {}) or {})
    return pairs


def measure(font_path, text, size, tracking=0.0):
    font, gs, cmap, upm = _font(font_path)
    scale = size / upm
    kern = _kern_pairs(font)
    names = [cmap.get(ord(ch), ".notdef") for ch in text]
    w = 0.0
    for i, gn in enumerate(names):
        w += gs[gn].width * scale
        if i + 1 < len(names):
            w += kern.get((gn, names[i + 1]), 0) * scale + tracking
    return w


def text_path(font_path, text, size=96, x=0.0, y=0.0, anchor="start", tracking=0.0, width=None, precision=1):
    """Return (path_d, advance_width). y is the baseline, like SVG <text>."""
    font, gs, cmap, upm = _font(font_path)
    scale = size / upm
    if width is not None and len(text) > 1:
        tracking = tracking + (width - measure(font_path, text, size, tracking)) / (len(text) - 1)
    total = measure(font_path, text, size, tracking)
    x0 = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
    kern = _kern_pairs(font)
    names = [cmap.get(ord(ch), ".notdef") for ch in text]
    parts, cx = [], x0
    for i, gn in enumerate(names):
        pen = SVGPathPen(gs, ntos=lambda v: ("%.*f" % (precision, v)).rstrip("0").rstrip("."))
        # font units are y-up; SVG is y-down
        gs[gn].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
        d = pen.getCommands()
        if d:
            parts.append(d)
        cx += gs[gn].width * scale
        if i + 1 < len(names):
            cx += kern.get((gn, names[i + 1]), 0) * scale + tracking
    return " ".join(parts), total


def text_glyphs(font_path, text, size=96, x=0.0, y=0.0, anchor="start", tracking=0.0, width=None, precision=1):
    """Like text_path but one path string per glyph (keeps each <path> small and letters individually editable)."""
    out, x_cursor = [], None
    font, gs, cmap, upm = _font(font_path)
    scale = size / upm
    if width is not None and len(text) > 1:
        tracking = tracking + (width - measure(font_path, text, size, tracking)) / (len(text) - 1)
    total = measure(font_path, text, size, tracking)
    x_cursor = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
    kern = _kern_pairs(font)
    names = [cmap.get(ord(ch), ".notdef") for ch in text]
    for i, gn in enumerate(names):
        d, _ = text_path(font_path, text[i], size, x_cursor, y, "start", 0, None, precision)
        if d:
            out.append(d)
        x_cursor += gs[gn].width * scale
        if i + 1 < len(names):
            x_cursor += kern.get((gn, names[i + 1]), 0) * scale + tracking
    return out, total


def text_group(font_path, text, size=96, x=0.0, y=0.0, anchor="start", tracking=0.0, width=None, attrs=""):
    """<g aria-label="TEXT" ...> with one <path> per glyph - the recommended form for logos and titles."""
    glyphs, _ = text_glyphs(font_path, text, size, x, y, anchor, tracking, width)
    label = text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return '<g aria-label="%s" %s>%s</g>' % (label, attrs, "".join('<path d="%s"/>' % d for d in glyphs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("font")
    ap.add_argument("text")
    ap.add_argument("--size", type=float, default=96)
    ap.add_argument("--x", type=float, default=0)
    ap.add_argument("--y", type=float, default=0)
    ap.add_argument("--anchor", choices=["start", "middle", "end"], default="start")
    ap.add_argument("--tracking", type=float, default=0)
    ap.add_argument("--width", type=float)
    ap.add_argument("--fill", default="#111111")
    ap.add_argument("--id")
    ap.add_argument("--d-only", action="store_true")
    ap.add_argument("--glyphs", action="store_true")
    a = ap.parse_args()
    if a.glyphs:
        idattr = 'id="%s" ' % a.id if a.id else ""
        print(text_group(a.font, a.text, a.size, a.x, a.y, a.anchor, a.tracking, a.width, attrs='%sfill="%s"' % (idattr, a.fill)))
        return
    d, w = text_path(a.font, a.text, a.size, a.x, a.y, a.anchor, a.tracking, a.width)
    if a.d_only:
        print(d)
    else:
        idattr = ' id="%s"' % a.id if a.id else ""
        print('<path%s aria-label="%s" fill="%s" d="%s"/>' % (idattr, a.text.replace('"', "&quot;"), a.fill, d))
    print("<!-- advance width: %.1f -->" % w, file=sys.stderr)


if __name__ == "__main__":
    main()
