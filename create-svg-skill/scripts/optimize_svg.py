#!/usr/bin/env python3
"""optimize_svg.py - structure-preserving SVG optimiser for SVG Style Studio.

Usage:
  optimize_svg.py in.svg -o out.svg [--precision 2] [--minify] [--no-use] [--no-hoist]
  optimize_svg.py in.svg --in-place
  optimize_svg.py in.svg --dry-run          (report only)

What it does (all appearance-preserving):
  * strips comments, editor metadata (inkscape/sodipodi/sketch/...), empty <defs>/<g>
  * trims numeric precision in path data, points, transforms and numeric attributes
    (use --precision 0 for pixel-grid art)
  * re-serialises path data compactly (implicit repeats, no redundant separators)
  * removes default-valued presentation attributes when nothing above overrides them
  * removes unreferenced gradients / filters / clipPaths / masks / patterns / symbols / markers
  * merges byte-identical gradients, filters, clipPaths, masks, patterns and rewrites refs
  * converts >=3 identical, sufficiently long <path d> / <polygon points> into <use> of one definition
  * hoists presentation attributes shared by every child into the parent <g>
  * unwraps bare <g> wrappers (named/ID'd/styled/transformed groups are KEPT - they are the
    semantic structure that keeps the file editable)

It never rasterises, never reorders painted elements, and never touches text content.
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import (  # noqa: E402
    NON_RENDERED, NUM_RE, SVG_NS, XLINK_NS, INHERITED, PathParseError,
    get_href, iter_elements, local, parse_svg,
)
from lxml import etree  # noqa: E402

EDITOR_PREFIXES = ("inkscape", "sodipodi", "sketch", "serif", "figma", "adobe", "i", "x", "a", "xmlns:inkscape")
EDITOR_NS_HINTS = ("inkscape", "sodipodi", "sketch", "serif", "illustrator", "adobe", "bohemian", "creativecommons", "purl.org/dc", "w3.org/1999/02/22-rdf")

NUMERIC_ATTRS = {
    "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "fx", "fy",
    "offset", "stroke-width", "stroke-miterlimit", "stroke-dashoffset", "opacity", "fill-opacity",
    "stroke-opacity", "stop-opacity", "font-size", "stdDeviation", "dx", "dy", "k1", "k2", "k3", "k4",
    "viewBox", "points", "transform", "gradientTransform", "patternTransform", "stroke-dasharray",
    "radius", "baseFrequency", "scale", "surfaceScale", "diffuseConstant", "specularExponent",
}
DEFAULTS = {
    "opacity": "1", "fill-opacity": "1", "stroke-opacity": "1", "stop-opacity": "1",
    "display": "inline", "visibility": "visible", "fill-rule": "nonzero", "clip-rule": "nonzero",
    "stroke-linecap": "butt", "stroke-linejoin": "miter", "stroke-miterlimit": "4",
    "stroke-dashoffset": "0", "stroke-dasharray": "none", "font-style": "normal", "font-weight": "normal",
}
HOISTABLE = ["fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "shape-rendering",
             "fill-opacity", "stroke-opacity", "fill-rule", "stroke-dasharray", "stroke-miterlimit"]
DEDUPE_TAGS = {"linearGradient", "radialGradient", "filter", "clipPath", "mask", "pattern"}


def fmt(v, prec, lead_zero=True):
    s = ("%." + str(prec) + "f") % v if prec > 0 else "%d" % round(v)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    if not lead_zero:
        s = re.sub(r"^(-?)0\.", r"\1.", s)
    return s


def round_numbers(text, prec):
    return NUM_RE.sub(lambda m: fmt(float(m.group()), prec), text)


# ---------------------------------------------------------------- path data
_ARGC = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def reserialize_path(d, prec):
    """Compact path data. Raises PathParseError on malformed data."""
    i, n = 0, len(d)
    groups = []  # (cmd, [floats/ints])
    cmd = None

    def skip():
        nonlocal i
        while i < n and d[i] in " ,\t\r\n":
            i += 1

    def num():
        nonlocal i
        skip()
        m = NUM_RE.match(d, i)
        if not m:
            raise PathParseError("bad number at %d" % i)
        i = m.end()
        return float(m.group())

    def flag():
        nonlocal i
        skip()
        if i < n and d[i] in "01":
            i += 1
            return int(d[i - 1])
        raise PathParseError("bad arc flag at %d" % i)

    while True:
        skip()
        if i >= n:
            break
        if d[i].isalpha():
            cmd = d[i]
            i += 1
            if cmd in "Zz":
                groups.append((cmd, []))
                continue
        elif cmd is None or cmd in "Zz":
            raise PathParseError("unexpected number")
        up = cmd.upper()
        if up not in _ARGC:
            raise PathParseError("unknown command %r" % cmd)
        if up == "A":
            vals = [num(), num(), num(), flag(), flag(), num(), num()]
        else:
            vals = [num() for _ in range(_ARGC[up])]
        groups.append((cmd, vals))
        if up == "M":
            cmd = "l" if cmd == "m" else "L"

    out = []
    prev = None
    for cmd, vals in groups:
        toks = []
        for idx, v in enumerate(vals):
            if cmd.upper() == "A" and idx in (3, 4):
                toks.append(str(int(v)))
            else:
                toks.append(fmt(v, prec, lead_zero=False))
        body = ""
        for k, t in enumerate(toks):
            body += t if (k == 0 or t.startswith("-")) else " " + t
        if cmd in "Zz":
            out.append(cmd)
        elif prev == cmd:
            # implicit repeat of the same command: only a separator is needed
            out.append(body if body.startswith("-") else " " + body)
        else:
            out.append(cmd + body)
        prev = cmd
    return "".join(out)


# ---------------------------------------------------------------- helpers
def q(el):
    return etree.QName(el.tag)


def is_editor_ns(uri):
    return any(h in (uri or "") for h in EDITOR_NS_HINTS)


def strip_editor_cruft(root, stats):
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        ns = etree.QName(el.tag).namespace
        if ns and is_editor_ns(ns):
            el.getparent().remove(el)
            stats["cruft"] += 1
            continue
        if local(el.tag) == "metadata":
            el.getparent().remove(el)
            stats["cruft"] += 1
            continue
        for k in list(el.attrib):
            kns = etree.QName(k).namespace
            if kns and is_editor_ns(kns):
                del el.attrib[k]
                stats["cruft"] += 1
            elif k in ("data-name",) and False:
                pass


def strip_comments(root, stats):
    for c in list(root.iter(etree.Comment, etree.ProcessingInstruction)):
        par = c.getparent()
        if par is not None:
            # keep the text tail
            if c.tail and c.tail.strip():
                prev = c.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + c.tail
                else:
                    par.text = (par.text or "") + c.tail
            par.remove(c)
            stats["comments"] += 1


def trim_numbers(root, prec, stats):
    for el in iter_elements(root):
        t = local(el.tag)
        if t == "path" and el.get("d"):
            try:
                new = reserialize_path(el.get("d"), prec)
                if new != el.get("d"):
                    stats["numbers"] += 1
                el.set("d", new)
            except PathParseError:
                pass  # leave malformed data untouched; validator reports it
        for k in list(el.attrib):
            name = local(k)
            if name in NUMERIC_ATTRS and name != "d":
                v = el.get(k)
                nv = round_numbers(v, prec)
                if nv != v:
                    el.set(k, nv)
                    stats["numbers"] += 1
        if el.get("style"):
            st = el.get("style")
            ns = re.sub(r"(?<![#\w])(-?\d*\.\d{%d,})" % (prec + 1), lambda m: fmt(float(m.group(1)), prec), st)
            if ns != st:
                el.set("style", ns)


def ancestor_defines(el, prop):
    node = el.getparent()
    while node is not None and isinstance(node.tag, str):
        if node.get(prop) is not None:
            return True
        st = node.get("style") or ""
        if re.search(r"(^|;)\s*%s\s*:" % re.escape(prop), st):
            return True
        node = node.getparent()
    return False


def drop_defaults(root, stats):
    for el in iter_elements(root):
        for prop, dv in DEFAULTS.items():
            if el.get(prop) is not None and el.get(prop).strip() == dv:
                if prop in INHERITED and ancestor_defines(el, prop):
                    continue
                if prop in ("opacity", "display", "stop-opacity", "visibility") or True:
                    del el.attrib[prop]
                    stats["defaults"] += 1
        if local(el.tag) == "rect":
            for a in ("x", "y"):
                if el.get(a) in ("0", "0.0"):
                    del el.attrib[a]
                    stats["defaults"] += 1


def gather_refs(root):
    """Return set of ids referenced by url(#..) or href."""
    refs = set()
    for el in iter_elements(root):
        for k, v in el.attrib.items():
            for m in re.finditer(r"url\(\s*['\"]?#([^)'\" ]+)", v):
                refs.add(m.group(1))
            if local(k) == "href" and v.startswith("#"):
                refs.add(v[1:])
        if local(el.tag) == "style" and el.text:
            for m in re.finditer(r"url\(\s*['\"]?#([^)'\" ]+)", el.text):
                refs.add(m.group(1))
    return refs


def remove_unused_defs(root, stats):
    removable = {"linearGradient", "radialGradient", "filter", "clipPath", "mask", "pattern", "symbol", "marker"}
    changed = True
    while changed:
        changed = False
        refs = gather_refs(root)
        for el in list(iter_elements(root)):
            if local(el.tag) in removable and el.get("id") and el.get("id") not in refs:
                el.getparent().remove(el)
                stats["unused_defs"] += 1
                changed = True
        # a <style> block may target ids/classes; leave <path id> etc. alone


def canonical(el):
    c = copy.deepcopy(el)
    if "id" in c.attrib:
        del c.attrib["id"]
    return etree.tostring(c, method="c14n")


def rewrite_ref(root, old, new):
    for el in iter_elements(root):
        for k, v in list(el.attrib.items()):
            nv = v
            if ("#" + old) in v:
                nv = re.sub(r"url\(\s*(['\"]?)#%s\1\s*\)" % re.escape(old), "url(#%s)" % new, nv)
                if local(k) == "href" and nv == "#" + old:
                    nv = "#" + new
            if nv != v:
                el.set(k, nv)
        if local(el.tag) == "style" and el.text and ("#" + old) in el.text:
            el.text = re.sub(r"url\(\s*(['\"]?)#%s\1\s*\)" % re.escape(old), "url(#%s)" % new, el.text)


def merge_duplicate_defs(root, stats):
    seen = {}
    for el in list(iter_elements(root)):
        if local(el.tag) in DEDUPE_TAGS and el.get("id"):
            key = canonical(el)
            if key in seen and seen[key] is not el:
                keep = seen[key].get("id")
                old = el.get("id")
                rewrite_ref(root, old, keep)
                el.getparent().remove(el)
                stats["merged_defs"] += 1
            else:
                seen[key] = el


def unique_id(root, base):
    used = {e.get("id") for e in iter_elements(root) if e.get("id")}
    n = 1
    while "%s%d" % (base, n) in used:
        n += 1
    return "%s%d" % (base, n)


def ensure_defs(root):
    for ch in root:
        if isinstance(ch.tag, str) and local(ch.tag) == "defs":
            return ch
    defs = etree.Element("{%s}defs" % SVG_NS)
    # after <title>/<desc> if present
    idx = 0
    for i, ch in enumerate(root):
        if isinstance(ch.tag, str) and local(ch.tag) in ("title", "desc"):
            idx = i + 1
    root.insert(idx, defs)
    return defs


def dedupe_to_use(root, stats, min_len=60, min_count=3):
    groups = defaultdict(list)
    for el in iter_elements(root):
        t = local(el.tag)
        # only shapes that are painted (not already inside defs/clipPath/mask)
        anc = [local(a.tag) for a in el.iterancestors()]
        if any(a in NON_RENDERED for a in anc):
            continue
        if t == "path" and len(el.get("d", "")) >= min_len:
            groups[("path", "d", el.get("d").strip())].append(el)
        elif t == "polygon" and len(el.get("points", "")) >= min_len:
            groups[("polygon", "points", el.get("points").strip())].append(el)
    defs = None
    for (tag, attr, data), els in groups.items():
        if len(els) < min_count:
            continue
        if defs is None:
            defs = ensure_defs(root)
        new_id = unique_id(root, "shape")
        proto = etree.SubElement(defs, "{%s}%s" % (SVG_NS, tag))
        proto.set("id", new_id)
        proto.set(attr, data)
        for el in els:
            use = etree.Element("{%s}use" % SVG_NS)
            use.set("href", "#" + new_id)
            for k, v in el.attrib.items():
                if k == attr:
                    continue
                use.set(k, v)
            use.tail = el.tail
            el.getparent().replace(el, use)
        stats["use_converted"] += len(els)


def hoist_common(root, stats):
    for g in list(iter_elements(root)):
        if local(g.tag) not in ("g",):
            continue
        kids = [c for c in g if isinstance(c.tag, str)]
        if len(kids) < 3:
            continue
        if any(local(c.tag) not in ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "use") for c in kids):
            continue
        if any(c.get("style") or c.get("class") for c in kids) or g.get("style"):
            continue
        for prop in HOISTABLE:
            if g.get(prop) is not None:
                continue
            vals = {c.get(prop) for c in kids}
            if len(vals) == 1 and None not in vals:
                v = vals.pop()
                # a <use> child inherits into its shadow tree only if the referenced
                # element does not set the property itself; those prototypes never do.
                g.set(prop, v)
                for c in kids:
                    del c.attrib[prop]
                stats["hoisted"] += 1


def prune_empty_and_unwrap(root, stats):
    changed = True
    while changed:
        changed = False
        for el in list(iter_elements(root)):
            t = local(el.tag)
            par = el.getparent()
            if par is None:
                continue
            kids = [c for c in el if isinstance(c.tag, str)]
            if t == "defs" and not kids:
                par.remove(el)
                stats["empty"] += 1
                changed = True
            elif t == "g" and not kids and not (el.text or "").strip() and not el.get("id"):
                par.remove(el)
                stats["empty"] += 1
                changed = True
            elif t == "g" and not el.attrib and kids:
                idx = list(par).index(el)
                for off, ch in enumerate(list(el)):
                    par.insert(idx + off, ch)
                # preserve tail
                if el.tail and el.tail.strip():
                    last = par[idx + len(kids) - 1]
                    last.tail = (last.tail or "") + el.tail
                par.remove(el)
                stats["unwrapped"] += 1
                changed = True


def optimize(root, precision=2, use_convert=True, hoist=True):
    stats = Counter()
    strip_comments(root, stats)
    strip_editor_cruft(root, stats)
    trim_numbers(root, precision, stats)
    drop_defaults(root, stats)
    merge_duplicate_defs(root, stats)
    if use_convert:
        dedupe_to_use(root, stats)
    if hoist:
        hoist_common(root, stats)
    remove_unused_defs(root, stats)
    prune_empty_and_unwrap(root, stats)
    etree.cleanup_namespaces(root)
    return stats


def serialise(root, minify=False):
    if minify:
        for el in root.iter():
            if isinstance(el.tag, str):
                if el.text is not None and not el.text.strip() and len(el) >= 0 and local(el.tag) not in ("text", "tspan", "style"):
                    el.text = None
                if el.tail is not None and not el.tail.strip():
                    el.tail = None
    else:
        # pretty print: clear whitespace-only text so indent() works, but keep <text>/<style> content
        for el in root.iter():
            if isinstance(el.tag, str) and local(el.tag) not in ("text", "tspan", "style"):
                if el.text is not None and not el.text.strip():
                    el.text = None
                if el.tail is not None and not el.tail.strip():
                    el.tail = None
        # do not re-indent inside text
        etree.indent(root, space=" ")
    data = etree.tostring(root, encoding="unicode", xml_declaration=False)
    return data + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("-o", "--out")
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--precision", type=int, default=2)
    ap.add_argument("--minify", action="store_true", help="no indentation (smaller, less editable)")
    ap.add_argument("--no-use", action="store_true", help="do not convert repeated shapes to <use>")
    ap.add_argument("--no-hoist", action="store_true", help="do not hoist shared attributes into groups")
    args = ap.parse_args()

    root, err = parse_svg(args.file)
    if root is None:
        sys.exit("cannot parse %s: %s" % (args.file, err))
    before = len(Path(args.file).read_bytes())
    stats = optimize(root, args.precision, not args.no_use, not args.no_hoist)
    text = serialise(root, args.minify)
    after = len(text.encode("utf-8"))
    summary = ", ".join("%s=%d" % kv for kv in sorted(stats.items())) or "nothing to change"
    print("%s: %d -> %d bytes (%.0f%%)  [%s]" % (args.file, before, after, 100.0 * after / max(before, 1), summary))
    if args.dry_run:
        return
    out = args.file if args.in_place else args.out
    if not out:
        sys.exit("give -o OUT.svg, --in-place, or --dry-run")
    Path(out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
