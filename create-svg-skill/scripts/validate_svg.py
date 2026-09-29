#!/usr/bin/env python3
"""validate_svg.py - static QC for SVG Style Studio.

Usage:
  validate_svg.py FILE.svg [FILE2.svg ...] [--style STYLE_ID ...] [--json] [--strict]

Checks (maps to the QC pipeline in SKILL.md):
  syntax, root/xmlns, viewBox, broken/duplicate ids, unused defs, embedded
  raster, gradients/masks/clipPaths/filters sanity, invisible objects,
  content clipped / off-canvas / cramped, z-order (hidden shapes, obscured
  text, background not first), balance, complexity, duplicate geometry,
  precision bloat, and optional per-style conformance from the registry's
  "checks" block.

Exit code: 0 = no errors, 1 = errors (or warnings with --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import (  # noqa: E402
    NON_RENDERED, SHAPE_TAGS, StyleResolver, fnum, get_href, ids_map,
    iter_elements, load_registry, local, mat_mul, norm_color, parse_path,
    parse_svg, parse_viewbox, parse_transform, PathParseError, transform_bbox,
    walk_painted, clip_bbox, inherit_text_attrs, local_bbox, IDENTITY, NUM_RE, union,
)

LEVELS = {"error": 0, "warn": 1, "info": 2}


class Report:
    def __init__(self, path):
        self.path = str(path)
        self.findings = []
        self.stats = {}

    def add(self, level, code, msg, el=None):
        where = None
        if el is not None:
            where = local(el.tag)
            if el.get("id"):
                where += "#" + el.get("id")
            if getattr(el, "sourceline", None):
                where += " (line %d)" % el.sourceline
        self.findings.append({"level": level, "code": code, "message": msg, "where": where})

    @property
    def errors(self):
        return [f for f in self.findings if f["level"] == "error"]

    @property
    def warnings(self):
        return [f for f in self.findings if f["level"] == "warn"]


URL_REF = re.compile(r"url\(\s*['\"]?#([^)'\" ]+)['\"]?\s*\)")


def validate(path, style_ids=None, registry=None):
    rep = Report(path)
    p = Path(path)
    if not p.exists():
        rep.add("error", "missing-file", "file not found")
        return rep
    raw = p.read_text(encoding="utf-8", errors="replace")
    rep.stats["bytes"] = len(raw.encode("utf-8"))

    # 1. syntax ------------------------------------------------------------
    root, err = parse_svg(str(p))
    if root is None:
        rep.add("error", "xml-syntax", "not well-formed XML: %s" % err)
        return rep
    if local(root.tag) != "svg":
        rep.add("error", "root", "root element is <%s>, expected <svg>" % local(root.tag))
        return rep
    if root.nsmap.get(None) != "http://www.w3.org/2000/svg" and not root.tag.startswith("{http://www.w3.org/2000/svg}"):
        rep.add("error", "xmlns", 'missing xmlns="http://www.w3.org/2000/svg" on <svg>')

    ids = ids_map(root)
    res = StyleResolver(root)
    elements = list(iter_elements(root))
    rep.stats["elements"] = len(elements)

    # 3. viewBox -----------------------------------------------------------
    vb = parse_viewbox(root)
    if vb is None:
        rep.add("error", "viewbox", "missing or invalid viewBox (needed for scaling)")
        vb = (0.0, 0.0, fnum(root.get("width"), 100), fnum(root.get("height"), 100))
    elif vb[2] <= 0 or vb[3] <= 0:
        rep.add("error", "viewbox", "viewBox has non-positive size")
    W, H = vb[2], vb[3]
    rep.stats["viewBox"] = list(vb)
    for attr in ("width", "height"):
        v = root.get(attr)
        if v and re.fullmatch(r"\s*[\d.]+(px)?\s*", v):
            rep.add("info", "fixed-size", "<svg %s=%r> is fixed-size; drop it or use 100%% so the file is responsive" % (attr, v))
    ar = W / H if H else 1
    if ar > 6 or ar < 1 / 6:
        rep.add("warn", "aspect", "extreme aspect ratio %.2f" % ar)

    if root.find("{http://www.w3.org/2000/svg}title") is None and root.find("title") is None:
        rep.add("warn", "title", "no <title>; add one for accessibility")

    # 2. references / ids ---------------------------------------------------
    id_counts = Counter(e.get("id") for e in elements if e.get("id"))
    for i, c in id_counts.items():
        if c > 1:
            rep.add("error", "duplicate-id", "id %r used %d times" % (i, c))

    referenced = set()
    for el in elements:
        blobs = []
        for k, v in el.attrib.items():
            blobs.append(v)
            if local(k) == "href" and v.startswith("#"):
                referenced.add(v[1:])
                if v[1:] not in ids:
                    rep.add("error", "broken-href", "href points to missing id %r" % v[1:], el)
            elif local(k) == "href" and re.match(r"https?:", v):
                rep.add("warn", "external-ref", "external resource %r will not load offline" % v[:60], el)
        if local(el.tag) == "style" and el.text:
            blobs.append(el.text)
            if "@import" in el.text:
                rep.add("warn", "css-import", "@import in <style> is not portable", el)
        for blob in blobs:
            for ref in URL_REF.findall(blob):
                referenced.add(ref)
                if ref not in ids:
                    rep.add("error", "broken-url-ref", "url(#%s) refers to a missing id" % ref, el)
        for k in el.attrib:
            if k.lower().startswith("on"):
                rep.add("error", "event-handler", "inline event handler %r is not allowed" % k, el)
    for el in elements:
        t = local(el.tag)
        if t == "script":
            rep.add("error", "script", "<script> in artwork; SVG art should be static", el)
        if t == "foreignObject":
            rep.add("warn", "foreignobject", "<foreignObject> is poorly supported outside browsers", el)
        if t == "image":
            h = get_href(el) or ""
            if h.startswith("data:image") and not h.startswith("data:image/svg"):
                rep.add("error", "embedded-raster", "embedded raster image; artwork must be real vector", el)
            elif h and not h.startswith("#"):
                rep.add("warn", "image-ref", "<image> reference to %r; prefer native vector shapes" % h[:50], el)

    # unused ids inside <defs>
    for el in elements:
        if local(el.tag) in NON_RENDERED and local(el.tag) not in ("title", "desc", "style", "metadata", "defs", "script") and el.get("id"):
            if el.get("id") not in referenced:
                # allow <symbol>/<marker> etc. only if unused -> warn
                rep.add("info", "unused-def", "definition %r is never referenced" % el.get("id"), el)

    # 7. gradients / masks / clipPaths / filters ---------------------------
    for el in elements:
        t = local(el.tag)
        if t in ("linearGradient", "radialGradient"):
            stops = [c for c in el if local(c.tag) == "stop"]
            href = get_href(el)
            if not stops and not (href and href.lstrip("#") in ids):
                rep.add("error", "gradient-stops", "%s has no <stop> children" % t, el)
            offs = [fnum(s.get("offset"), 0) / (100 if (s.get("offset") or "").endswith("%") else 1) for s in stops]
            if offs and any(b < a - 1e-9 for a, b in zip(offs, offs[1:])):
                rep.add("warn", "gradient-order", "gradient stops are not in ascending offset order", el)
            if t == "radialGradient" and el.get("r") is not None and fnum(el.get("r")) <= 0:
                rep.add("error", "gradient-radius", "radialGradient r <= 0 renders nothing", el)
        elif t in ("clipPath", "mask"):
            kids = [c for c in el if isinstance(c.tag, str)]
            if not kids:
                rep.add("error", "empty-" + t.lower(), "<%s> is empty; anything using it disappears" % t, el)
        elif t == "filter":
            prims = [c for c in el if local(c.tag).startswith("fe")]
            if not prims:
                rep.add("error", "empty-filter", "<filter> has no primitives; targets may vanish", el)
            results = set()
            for pr in prims:
                for attr in ("in", "in2"):
                    v = pr.get(attr)
                    if v and v not in ("SourceGraphic", "SourceAlpha", "BackgroundImage", "BackgroundAlpha", "FillPaint", "StrokePaint") and v not in results:
                        rep.add("error", "filter-input", "filter primitive %s=%r has no earlier result with that name" % (attr, v), pr)
                if pr.get("result"):
                    results.add(pr.get("result"))
                if local(pr.tag) == "feGaussianBlur":
                    sd = fnum(pr.get("stdDeviation"), 0)
                    if sd > 0.05 * max(W, H) and not el.get("width"):
                        rep.add("warn", "filter-region", "large blur (%.1f) with default filter region may clip the glow; set x/y/width/height on <filter>" % sd, el)
    n_filt = sum(1 for e in elements if local(e.tag) == "filter")
    n_filt_use = sum(1 for e in elements if "filter" in (e.get("filter") or "") + (e.get("style") or ""))
    rep.stats["filters"] = n_filt
    rep.stats["filter_uses"] = n_filt_use
    if n_filt_use > 12:
        rep.add("warn", "filter-heavy", "%d elements use filters; group them or replace with vector techniques" % n_filt_use)

    # painted elements ------------------------------------------------------
    inherit_text_attrs(root)
    painted = list(walk_painted(root, ids))
    parents = {ch: p for p in root.iter() for ch in p if isinstance(ch.tag, str)}
    rep.stats["painted"] = len(painted)
    if not painted:
        rep.add("error", "empty", "no painted graphic elements")
        return rep

    # 6. invisible objects, 4. clipped ------------------------------------
    boxes = []  # (el, bbox in root space, opaque)
    for el, m in painted:
        t = local(el.tag)
        disp = res.displayed(el)
        vis = (res.get(el, "visibility", "visible") or "visible").strip()
        op = res.opacity_chain(el)
        if not disp or vis in ("hidden", "collapse"):
            rep.add("warn", "invisible", "element is hidden (display:none / visibility:hidden)", el)
            continue
        if op <= 0.001:
            rep.add("warn", "invisible", "opacity 0 makes this element invisible", el)
            continue
        fill = res.get(el, "fill", "black")
        stroke = res.get(el, "stroke", "none")
        fo = fnum(res.get(el, "fill-opacity", "1"), 1)
        so = fnum(res.get(el, "stroke-opacity", "1"), 1)
        sw = fnum(res.get(el, "stroke-width", "1"), 1)
        has_fill = (fill or "none").strip() != "none" and fo > 0 and t != "line"
        has_stroke = (stroke or "none").strip() != "none" and so > 0 and sw > 0
        if t in SHAPE_TAGS and not has_fill and not has_stroke:
            # polylines/lines default fill (black) is irrelevant when stroke none
            rep.add("warn", "invisible", "no fill and no stroke: nothing is painted", el)
            continue
        bb = local_bbox(el, ids)
        if t in SHAPE_TAGS:
            zero = False
            if t == "rect" and (fnum(el.get("width")) <= 0 or fnum(el.get("height")) <= 0):
                zero = True
            if t == "circle" and fnum(el.get("r")) <= 0:
                zero = True
            if t == "ellipse" and (fnum(el.get("rx")) <= 0 or fnum(el.get("ry")) <= 0):
                zero = True
            if zero:
                rep.add("warn", "zero-size", "zero-size shape paints nothing", el)
                continue
        if t == "path":
            try:
                parse_path(el.get("d", ""))
            except PathParseError as exc:
                rep.add("error", "path-syntax", "invalid path data: %s" % exc, el)
                continue
            if not el.get("d", "").strip():
                rep.add("warn", "empty-path", "empty path data", el)
                continue
        if bb is None:
            continue
        pad = sw / 2 if has_stroke else 0
        bbr = transform_bbox(m, (bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad))
        cb = clip_bbox(el, ids, parents)
        if cb is not None:
            bbr = (max(bbr[0], cb[0]), max(bbr[1], cb[1]), min(bbr[2], cb[2]), min(bbr[3], cb[3]))
            if bbr[2] <= bbr[0] or bbr[3] <= bbr[1]:
                continue
        opaque = bool(has_fill and fo >= 0.95 and op >= 0.95 and norm_color(fill) is not None)
        boxes.append((el, bbr, opaque, has_fill))

    vx0, vy0, vx1, vy1 = vb[0], vb[1], vb[0] + W, vb[1] + H
    canvas_area = W * H

    def area(b):
        return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])

    bg_like = set()
    for el, bb, opq, hf in boxes:
        if area(bb) >= 0.85 * canvas_area:
            bg_like.add(id(el))

    allow_bleed = False
    style_specs = [registry[s] for s in (style_ids or []) if registry and s in registry]
    for s in style_specs:
        if s.get("checks", {}).get("allow_bleed"):
            allow_bleed = True

    content = None
    off_canvas = 0
    for el, bb, opq, hf in boxes:
        ix0, iy0, ix1, iy1 = max(bb[0], vx0), max(bb[1], vy0), min(bb[2], vx1), min(bb[3], vy1)
        if ix1 <= ix0 or iy1 <= iy0:
            off_canvas += 1
            rep.add("warn", "off-canvas", "element lies completely outside the viewBox", el)
            continue
        if id(el) in bg_like:
            continue
        content = union(content, bb)
    rep.stats["off_canvas"] = off_canvas

    if content:
        m_l, m_t = (content[0] - vx0) / W, (content[1] - vy0) / H
        m_r, m_b = (vx1 - content[2]) / W, (vy1 - content[3]) / H
        rep.stats["content_margins_pct"] = [round(100 * v, 1) for v in (m_l, m_t, m_r, m_b)]
        fill_ratio = area(content) / canvas_area if canvas_area else 0
        rep.stats["content_fill_pct"] = round(100 * fill_ratio, 1)
        if min(m_l, m_t, m_r, m_b) < -0.002:
            if not allow_bleed:
                rep.add("warn", "clipped", "content extends past the viewBox on at least one side (margins %% L/T/R/B: %s); important content may be clipped" % [round(100 * v, 1) for v in (m_l, m_t, m_r, m_b)])
        elif min(m_l, m_t, m_r, m_b) < 0.015 and not allow_bleed:
            rep.add("info", "tight-margin", "content is within 1.5%% of the edge (margins %% L/T/R/B: %s)" % [round(100 * v, 1) for v in (m_l, m_t, m_r, m_b)])
        if fill_ratio < 0.30:
            rep.add("warn", "small-subject", "subject bounding box fills only %.0f%% of the canvas; scale up or tighten the viewBox" % (100 * fill_ratio))
        # visual weight centroid (area weighted, capped so huge shapes don't dominate)
        tot = cx = cy = 0.0
        for el, bb, opq, hf in boxes:
            if id(el) in bg_like or not hf:
                continue
            a = min(area(bb), 0.25 * canvas_area)
            if a <= 0:
                continue
            tot += a
            cx += a * (bb[0] + bb[2]) / 2
            cy += a * (bb[1] + bb[3]) / 2
        if tot:
            ox = (cx / tot - (vx0 + W / 2)) / W
            oy = (cy / tot - (vy0 + H / 2)) / H
            rep.stats["weight_offset_pct"] = [round(100 * ox, 1), round(100 * oy, 1)]
            if abs(ox) > 0.18 or abs(oy) > 0.18:
                rep.add("info", "balance", "visual weight sits %.0f%%/%.0f%% from centre (x/y); fine for deliberate asymmetry, otherwise rebalance" % (100 * ox, 100 * oy))

    # 5. z-order ------------------------------------------------------------
    order = {id(el): i for i, (el, *_rest) in enumerate(boxes)}
    if boxes:
        big = [i for i, (el, bb, *_r) in enumerate(boxes) if id(el) in bg_like]
        if big and big[0] != 0:
            rep.add("warn", "z-background", "a canvas-sized shape is painted after smaller shapes and may cover them", boxes[big[0]][0])
        for i in big[1:]:
            el, bb, opq, hf = boxes[i]
            if opq and i > 0:
                rep.add("warn", "z-cover", "opaque canvas-sized shape painted late (element %d of %d) covers earlier art" % (i + 1, len(boxes)), el)
                break
    if len(boxes) <= 1500:
        for i, (el, bb, opq, hf) in enumerate(boxes):
            if area(bb) <= 0:
                continue
            for j in range(i + 1, len(boxes)):
                el2, bb2, opq2, hf2 = boxes[j]
                if not opq2 or local(el2.tag) not in ("rect", "circle", "ellipse"):
                    continue
                if parse_transform(el2.get("transform")) != IDENTITY and local(el2.tag) == "rect":
                    continue
                if local(el2.tag) != "rect":
                    # circles/ellipses cover only their inscribed box (~70%)
                    cx0 = bb2[0] + (bb2[2] - bb2[0]) * 0.146
                    cx1 = bb2[2] - (bb2[2] - bb2[0]) * 0.146
                    cy0 = bb2[1] + (bb2[3] - bb2[1]) * 0.146
                    cy1 = bb2[3] - (bb2[3] - bb2[1]) * 0.146
                    cover = (cx0, cy0, cx1, cy1)
                else:
                    cover = bb2
                if bb[0] >= cover[0] - 1e-6 and bb[1] >= cover[1] - 1e-6 and bb[2] <= cover[2] + 1e-6 and bb[3] <= cover[3] + 1e-6:
                    lvl = "warn" if local(el.tag) == "text" else "info"
                    what = "text is hidden behind a later opaque shape" if local(el.tag) == "text" else "fully hidden behind a later opaque shape (wasted geometry or wrong z-order)"
                    if id(el) not in bg_like and area(bb) > 0.0005 * canvas_area:
                        rep.add(lvl, "z-hidden", what, el)
                    break
    # text sanity
    for el, m in painted:
        if local(el.tag) == "text":
            ff = (res.get(el, "font-family", "") or "").lower()
            if not ff:
                rep.add("info", "font-missing", "text has no font-family; renderers will fall back unpredictably", el)
            elif not re.search(r"(serif|sans-serif|monospace|cursive|fantasy|system-ui)", ff):
                rep.add("info", "font-fallback", "font-family %r lacks a generic fallback; fonts are not embedded (outline text to paths for logos)" % ff[:60], el)

    # complexity / hygiene ------------------------------------------------------
    d_lens = []
    long_decimals = 0
    geo = defaultdict(list)
    for el in elements:
        if local(el.tag) == "path":
            d = el.get("d", "")
            d_lens.append(len(d))
            if len(d) > 6000:
                rep.add("warn", "huge-path", "path data is %d chars; split into meaningful sub-shapes or simplify" % len(d), el)
            long_decimals += len(re.findall(r"\d+\.\d{4,}", d))
            geo[("path", d.strip())].append(el)
        elif local(el.tag) in ("polygon", "polyline"):
            geo[(local(el.tag), el.get("points", "").strip())].append(el)
    rep.stats["path_chars"] = sum(d_lens)
    if long_decimals > 20:
        rep.add("info", "precision", "%d numbers carry 4+ decimals; run optimize_svg.py to trim precision" % long_decimals)
    for (t, data), els in geo.items():
        if len(els) >= 3 and len(data) > 30:
            rep.add("info", "duplicate-geometry", "%d <%s> elements share identical geometry; define once and <use> it" % (len(els), t), els[1])
    if rep.stats["bytes"] > 1_000_000:
        rep.add("warn", "size", "file is %.0f KB; consider simplifying" % (rep.stats["bytes"] / 1024))
    elif rep.stats["bytes"] > 400_000:
        rep.add("info", "size", "file is %.0f KB" % (rep.stats["bytes"] / 1024))
    groups = [e for e in elements if local(e.tag) == "g"]
    empties = [g for g in groups if len([c for c in g if isinstance(c.tag, str)]) == 0]
    for g in empties[:5]:
        rep.add("info", "empty-group", "empty <g>", g)
    rep.stats["groups"] = len(groups)
    named = [g for g in groups if g.get("id") or g.get("class") or g.get("data-name")]
    rep.stats["named_groups"] = len(named)
    if len(painted) > 25 and len(named) < 3:
        rep.add("info", "structure", "%d shapes but only %d named groups; group semantically (id=\"background\", \"subject\", ...) for editability" % (len(painted), len(named)))

    # style conformance ------------------------------------------------------------
    colors = Counter()
    stroke_widths = Counter()
    curve_paths = 0
    non_int = 0
    for el, m in painted:
        c = norm_color(res.get(el, "fill", None) if local(el.tag) != "text" else res.get(el, "fill", None))
        if c:
            colors[c] += 1
        c2 = norm_color(res.get(el, "stroke", None))
        if c2:
            colors[c2] += 1
            stroke_widths[round(fnum(res.get(el, "stroke-width", "1"), 1), 2)] += 1
        if local(el.tag) == "path":
            try:
                _, letters = parse_path(el.get("d", ""))
                if any(l.upper() in "CSQTA" for l in letters):
                    curve_paths += 1
            except PathParseError:
                pass
        if local(el.tag) == "rect":
            for k in ("x", "y", "width", "height"):
                v = el.get(k)
                if v and abs(fnum(v) - round(fnum(v))) > 1e-6:
                    non_int += 1
                    break
    stop_colors = [norm_color(s.get("stop-color") or parse_style(s).get("stop-color")) for s in elements if local(s.tag) == "stop"]
    for c in stop_colors:
        if c:
            colors[c] += 1
    rep.stats["distinct_colors"] = len(colors)
    rep.stats["distinct_stroke_widths"] = len(stroke_widths)
    rep.stats["gradients"] = sum(1 for e in elements if local(e.tag) in ("linearGradient", "radialGradient"))
    rep.stats["patterns"] = sum(1 for e in elements if local(e.tag) == "pattern")
    rep.stats["text_elements"] = sum(1 for e in elements if local(e.tag) == "text")
    # outlined lettering (text_to_path.py) counts as typography: <g|path aria-label="...">
    rep.stats["outlined_text"] = sum(1 for e in root.iter() if isinstance(e.tag, str) and e is not root and e.get("aria-label") and local(e.tag) in ("g", "path"))

    for spec in style_specs:
        run_style_checks(rep, spec, elements, painted, colors, stroke_widths, curve_paths, non_int, res, root)
    for sid in (style_ids or []):
        if not registry or sid not in registry:
            rep.add("warn", "unknown-style", "style %r not found in registry; conformance checks skipped" % sid)
    return rep


def parse_style(el):
    from svgtools import parse_style_attr
    return parse_style_attr(el.get("style", ""))


def run_style_checks(rep, spec, elements, painted, colors, stroke_widths, curve_paths, non_int, res, root):
    chk = spec.get("checks") or {}
    sid = spec["id"]
    tags = Counter(local(e.tag) for e in elements)

    def w(code, msg):
        rep.add("warn", "style:%s:%s" % (sid, code), "[%s] %s" % (spec["name"], msg))

    for t in chk.get("forbid_elements", []):
        if tags.get(t):
            w("forbid-" + t, "<%s> used %d times but this style avoids it" % (t, tags[t]))
    req_any = chk.get("require_elements_any")
    if req_any and not any(tags.get(t) for t in req_any):
        w("require-any", "expected at least one of: %s" % ", ".join(req_any))
    if chk.get("max_colors") and len(colors) > chk["max_colors"]:
        w("max-colors", "%d distinct colours; this style keeps a palette of <= %d" % (len(colors), chk["max_colors"]))
    if chk.get("min_colors") and len(colors) < chk["min_colors"]:
        w("min-colors", "only %d distinct colours; expected >= %d" % (len(colors), chk["min_colors"]))
    if chk.get("forbid_path_curves") and curve_paths:
        w("curves", "%d paths use curves/arcs; this style is straight-edged" % curve_paths)
    if chk.get("integer_coords") and non_int:
        w("grid", "%d <rect> elements have non-integer coordinates; snap to the grid" % non_int)
    sr = chk.get("require_shape_rendering")
    if sr:
        n_ok = sum(1 for e, _m in painted if (res.get(e, "shape-rendering") or "") == sr)
        if n_ok < max(1, int(0.9 * len(painted))):
            w("shape-rendering", 'set shape-rendering="%s" on <svg> or the pixel group (%d/%d elements have it)' % (sr, n_ok, len(painted)))
    if chk.get("max_filters") is not None and rep.stats.get("filter_uses", 0) > chk["max_filters"]:
        w("max-filters", "%d filtered elements; limit is %d for this style" % (rep.stats["filter_uses"], chk["max_filters"]))
    if chk.get("min_filters") is not None and rep.stats.get("filters", 0) < chk["min_filters"]:
        w("min-filters", "expected at least %d filter(s) (e.g. glow) for this style" % chk["min_filters"])
    if chk.get("max_gradients") is not None and rep.stats["gradients"] > chk["max_gradients"]:
        w("max-gradients", "%d gradients; limit is %d for this style" % (rep.stats["gradients"], chk["max_gradients"]))
    if chk.get("min_gradients") is not None and rep.stats["gradients"] < chk["min_gradients"]:
        w("min-gradients", "expected at least %d gradient(s)" % chk["min_gradients"])
    if chk.get("min_elements") and rep.stats["painted"] < chk["min_elements"]:
        w("min-elements", "only %d painted elements; this style expects richer detail (>= %d)" % (rep.stats["painted"], chk["min_elements"]))
    if chk.get("max_elements") and rep.stats["painted"] > chk["max_elements"]:
        w("max-elements", "%d painted elements; this style stays simple (<= %d)" % (rep.stats["painted"], chk["max_elements"]))
    if chk.get("min_groups") and rep.stats["groups"] < chk["min_groups"]:
        w("min-groups", "only %d groups; layer the artwork (>= %d)" % (rep.stats["groups"], chk["min_groups"]))
    if chk.get("require_text") and not (rep.stats["text_elements"] or rep.stats.get("outlined_text")):
        w("text", "this style/format expects typography (<text>)")
    if chk.get("forbid_text") and (rep.stats["text_elements"] or rep.stats.get("outlined_text")):
        w("text", "this style avoids text")
    if chk.get("min_stroke_widths") and len(stroke_widths) < chk["min_stroke_widths"]:
        w("line-hierarchy", "%d distinct stroke widths; expected >= %d for line hierarchy" % (len(stroke_widths), chk["min_stroke_widths"]))
    if chk.get("max_stroke_widths") and len(stroke_widths) > chk["max_stroke_widths"]:
        w("stroke-consistency", "%d distinct stroke widths; expected <= %d for consistent weight" % (len(stroke_widths), chk["max_stroke_widths"]))
    if chk.get("require_stroke") and not stroke_widths:
        w("stroke", "no strokes found; this style relies on outlines")
    if chk.get("forbid_stroke") and stroke_widths:
        w("stroke", "strokes used; this style is fill-only")
    if chk.get("require_linecap"):
        caps = {res.get(e, "stroke-linecap") for e, _m in painted if res.get(e, "stroke") not in (None, "none")}
        if caps and caps != {chk["require_linecap"]}:
            w("linecap", 'stroke-linecap should be "%s" (found %s)' % (chk["require_linecap"], sorted(c or "butt" for c in caps)))
    if chk.get("require_linejoin"):
        joins = {res.get(e, "stroke-linejoin") for e, _m in painted if res.get(e, "stroke") not in (None, "none")}
        if joins and joins != {chk["require_linejoin"]}:
            w("linejoin", 'stroke-linejoin should be "%s" (found %s)' % (chk["require_linejoin"], sorted(j or "miter" for j in joins)))
    if chk.get("dark_base") or chk.get("light_base"):
        from svgtools import luminance
        base = base_color(painted, res, root)
        if base:
            L = luminance(base)
            if chk.get("dark_base") and L > 0.12:
                w("dark-base", "the base/background colour %s is light; this style sits on a dark base" % base)
            if chk.get("light_base") and L < 0.30:
                w("light-base", "the base/background colour %s is dark; this style sits on a light base" % base)


def base_color(painted, res, root):
    """Colour of the first painted element that looks like a background (or simply
    the first painted element); gradients resolve to their first stop."""
    ids = ids_map(root)
    for el, _m in painted:
        f = res.get(el, "fill", None)
        if f is None or f.strip() == "none":
            continue
        c = norm_color(f)
        if c:
            return c
        m = URL_REF.search(f)
        if m and m.group(1) in ids:
            g = ids[m.group(1)]
            for st in g.iter():
                if isinstance(st.tag, str) and local(st.tag) == "stop":
                    return norm_color(st.get("stop-color") or parse_style(st).get("stop-color"))
        return None
    return None


def format_text(rep, verbose_info=True):
    lines = []
    e, wn = len(rep.errors), len(rep.warnings)
    status = "FAIL" if e else ("WARN" if wn else "OK")
    lines.append("%s  %s   (%d errors, %d warnings)" % (status, rep.path, e, wn))
    s = rep.stats
    keys = ["viewBox", "bytes", "painted", "groups", "named_groups", "gradients", "patterns", "filters", "distinct_colors", "distinct_stroke_widths", "content_margins_pct", "content_fill_pct", "weight_offset_pct"]
    bits = ["%s=%s" % (k, s[k]) for k in keys if k in s]
    lines.append("  stats: " + ", ".join(bits))
    for f in sorted(rep.findings, key=lambda f: LEVELS[f["level"]]):
        if f["level"] == "info" and not verbose_info:
            continue
        loc = "  @ " + f["where"] if f["where"] else ""
        lines.append("  %-5s %-28s %s%s" % (f["level"].upper(), f["code"], f["message"], loc))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--style", action="append", default=[], help="style id(s) to check conformance against (repeatable)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--quiet", action="store_true", help="hide info-level notes")
    args = ap.parse_args()

    registry = None
    if args.style:
        registry = load_registry()
    reports = [validate(f, args.style, registry) for f in args.files]
    if args.json:
        print(json.dumps([{"file": r.path, "ok": not r.errors, "stats": r.stats, "findings": r.findings} for r in reports], indent=2))
    else:
        print("\n\n".join(format_text(r, not args.quiet) for r in reports))
    bad = any(r.errors or (args.strict and r.warnings) for r in reports)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
