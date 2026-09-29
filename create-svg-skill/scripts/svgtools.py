#!/usr/bin/env python3
"""Shared helpers for SVG Style Studio scripts.

Pure-Python (lxml only). Provides:
  - SVG parsing and namespace-free tag helpers
  - affine transform parsing / composition
  - path-data tokenising and conservative bounding boxes
  - inherited style-property lookup (attributes, style="", simple <style> rules)
  - colour normalisation
  - style-registry loading

Nothing here renders pixels; see render_svg.py for that.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.exit("lxml is required: pip install lxml")

SKILL_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = SKILL_DIR / "styles" / "registry"
REFERENCE_DIR = SKILL_DIR / "styles" / "references"

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

SHAPE_TAGS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path"}
GRAPHIC_TAGS = SHAPE_TAGS | {"text", "image", "use"}
# containers whose children are never painted directly
NON_RENDERED = {
    "defs", "clipPath", "mask", "pattern", "symbol", "marker", "filter",
    "linearGradient", "radialGradient", "style", "title", "desc", "metadata",
    "script", "font", "cursor", "view",
}
INHERITED = {
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "fill-opacity", "stroke-opacity", "visibility", "font-family", "font-size",
    "shape-rendering", "fill-rule", "stroke-dasharray", "text-anchor",
}


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def local(tag) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_svg(source):
    """Parse a path or SVG text. Returns (root, error_message_or_None)."""
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True)
    try:
        if isinstance(source, (str, Path)) and os.path.exists(str(source)):
            tree = etree.parse(str(source), parser)
            return tree.getroot(), None
        data = source.encode("utf-8") if isinstance(source, str) else source
        return etree.fromstring(data, parser), None
    except etree.XMLSyntaxError as exc:
        return None, str(exc)
    except OSError as exc:
        return None, str(exc)


def iter_elements(root):
    for el in root.iter():
        if isinstance(el.tag, str):
            yield el


def get_href(el):
    return el.get("{%s}href" % XLINK_NS) or el.get("href")


def ids_map(root):
    out = {}
    for el in iter_elements(root):
        i = el.get("id")
        if i is not None and i not in out:
            out[i] = el
    return out


# --------------------------------------------------------------------------
# numbers / lengths
# --------------------------------------------------------------------------
NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def fnum(value, default=0.0):
    """Parse a leading number from an attribute (ignores px, pt, %, etc.)."""
    if value is None:
        return default
    m = NUM_RE.search(str(value))
    return float(m.group()) if m else default


def parse_viewbox(root):
    vb = root.get("viewBox")
    if not vb:
        return None
    nums = [float(x) for x in NUM_RE.findall(vb)]
    if len(nums) != 4:
        return None
    return tuple(nums)


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mat_mul(m, n):
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def mat_apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def parse_transform(s):
    if not s:
        return IDENTITY
    m = IDENTITY
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s):
        v = [float(x) for x in NUM_RE.findall(args)]
        t = IDENTITY
        if name == "translate" and v:
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale" and v:
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate" and v:
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            r = (ca, sa, -sa, ca, 0, 0)
            if len(v) >= 3:
                t = mat_mul(mat_mul((1, 0, 0, 1, v[1], v[2]), r), (1, 0, 0, 1, -v[1], -v[2]))
            else:
                t = r
        elif name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "skewX" and v:
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY" and v:
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        m = mat_mul(m, t)
    return m


# --------------------------------------------------------------------------
# path data
# --------------------------------------------------------------------------
_CMD_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


class PathParseError(ValueError):
    pass


def parse_path(d):
    """Parse path data into a list of (command, [absolute coords]) plus the raw
    command letters used. Returns (segments, letters_used).

    segments: list of tuples (cmd_upper, points) where points are absolute
    (x, y) pairs (control points included; arcs give sampled points).
    """
    i, n = 0, len(d)
    segs = []
    letters = []
    cx = cy = 0.0
    sx = sy = 0.0
    cmd = None

    def skip_sep():
        nonlocal i
        while i < n and d[i] in " ,\t\r\n":
            i += 1

    def read_num():
        nonlocal i
        skip_sep()
        m = NUM_RE.match(d, i)
        if not m:
            raise PathParseError("expected number at %d in path data" % i)
        i = m.end()
        return float(m.group())

    def read_flag():
        nonlocal i
        skip_sep()
        if i < n and d[i] in "01":
            v = int(d[i])
            i += 1
            return v
        raise PathParseError("expected arc flag at %d" % i)

    while True:
        skip_sep()
        if i >= n:
            break
        ch = d[i]
        if ch.isalpha():
            cmd = ch
            i += 1
            letters.append(cmd)
            if cmd in "Zz":
                segs.append(("Z", [(sx, sy)]))
                cx, cy = sx, sy
                continue
        elif cmd is None:
            raise PathParseError("path data must start with a command")
        elif cmd in "Zz":
            raise PathParseError("numbers after closepath")
        up = cmd.upper()
        rel = cmd.islower()
        # parse one argument group for this command
        if up == "M":
            x, y = read_num(), read_num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy = x, y
            sx, sy = x, y
            segs.append(("M", [(x, y)]))
            cmd = "l" if rel else "L"  # implicit lineto
        elif up == "L" or up == "T":
            x, y = read_num(), read_num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy = x, y
            segs.append((up, [(x, y)]))
        elif up == "H":
            x = read_num()
            x = cx + x if rel else x
            cx = x
            segs.append(("H", [(cx, cy)]))
        elif up == "V":
            y = read_num()
            y = cy + y if rel else y
            cy = y
            segs.append(("V", [(cx, cy)]))
        elif up == "C":
            v = [read_num() for _ in range(6)]
            pts = [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]
            if rel:
                pts = [(cx + px, cy + py) for px, py in pts]
            cx, cy = pts[-1]
            segs.append(("C", pts))
        elif up in "SQ":
            v = [read_num() for _ in range(4)]
            pts = [(v[0], v[1]), (v[2], v[3])]
            if rel:
                pts = [(cx + px, cy + py) for px, py in pts]
            cx, cy = pts[-1]
            segs.append((up, pts))
        elif up == "A":
            rx, ry, rot = read_num(), read_num(), read_num()
            fa, fs = read_flag(), read_flag()
            x, y = read_num(), read_num()
            if rel:
                x, y = cx + x, cy + y
            pts = _arc_points(cx, cy, rx, ry, rot, fa, fs, x, y)
            cx, cy = x, y
            segs.append(("A", pts))
        else:
            raise PathParseError("unknown path command %r" % cmd)
    return segs, letters


def inherit_text_attrs(root):
    """In-memory only (validation): copy inheritable text attributes from ancestors onto <text>
    so bbox estimates honour group-level font-size / text-anchor. Never write this tree back."""
    parents = {ch: p for p in root.iter() for ch in p if isinstance(ch.tag, str)}
    for el in root.iter():
        if not isinstance(el.tag, str) or local(el.tag) != "text":
            continue
        for attr in ("font-size", "text-anchor"):
            if el.get(attr) is not None:
                continue
            cur = parents.get(el)
            while cur is not None:
                if cur.get(attr) is not None:
                    el.set(attr, cur.get(attr))
                    break
                cur = parents.get(cur)


def _arc_points(x1, y1, rx, ry, phi_deg, fa, fs, x2, y2, samples=24):
    """Sample points along an SVG elliptical arc (endpoint parameterisation)."""
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [(x2, y2)]
    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    lam = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        co = -co
    cxp = co * rx * y1p / ry
    cyp = -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dth > 0:
        dth -= 2 * math.pi
    elif fs and dth < 0:
        dth += 2 * math.pi
    pts = []
    for k in range(1, samples + 1):
        t = th1 + dth * k / samples
        px = cp * rx * math.cos(t) - sp * ry * math.sin(t) + cx
        py = sp * rx * math.cos(t) + cp * ry * math.sin(t) + cy
        pts.append((px, py))
    return pts


def path_bbox(d):
    """Conservative bbox (control points included) of path data, or None."""
    segs, _ = parse_path(d)
    xs, ys = [], []
    for _, pts in segs:
        for x, y in pts:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


# --------------------------------------------------------------------------
# styles / inherited properties
# --------------------------------------------------------------------------
_CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def collect_css(root):
    """Parse simple <style> rules: .class, tag, #id (no combinators)."""
    rules = {"class": {}, "tag": {}, "id": {}}
    for st in root.iter("{%s}style" % SVG_NS, "style"):
        text = st.text or ""
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for sel, body in _CSS_RULE.findall(text):
            props = parse_style_attr(body)
            for one in sel.split(","):
                one = one.strip()
                if re.fullmatch(r"\.[\w-]+", one):
                    rules["class"].setdefault(one[1:], {}).update(props)
                elif re.fullmatch(r"#[\w-]+", one):
                    rules["id"].setdefault(one[1:], {}).update(props)
                elif re.fullmatch(r"[a-zA-Z][\w-]*", one):
                    rules["tag"].setdefault(one, {}).update(props)
    return rules


def parse_style_attr(s):
    out = {}
    for part in (s or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class StyleResolver:
    def __init__(self, root):
        self.root = root
        self.css = collect_css(root)
        self._cache = {}

    def own(self, el, prop):
        """Value declared on el itself (style attr > CSS > presentation attr)."""
        inline = parse_style_attr(el.get("style", ""))
        if prop in inline:
            return inline[prop]
        i = el.get("id")
        if i and prop in self.css["id"].get(i, {}):
            return self.css["id"][i][prop]
        for c in (el.get("class") or "").split():
            if prop in self.css["class"].get(c, {}):
                return self.css["class"][c][prop]
        t = local(el.tag)
        if prop in self.css["tag"].get(t, {}):
            return self.css["tag"][t][prop]
        return el.get(prop)

    def get(self, el, prop, default=None):
        node = el
        while node is not None and isinstance(node.tag, str):
            v = self.own(node, prop)
            if v is not None and v != "inherit":
                return v
            if prop not in INHERITED:
                break
            node = node.getparent()
        return default

    def opacity_chain(self, el):
        """Product of opacity along the ancestor chain (opacity is not inherited
        but compounds visually)."""
        prod = 1.0
        node = el
        while node is not None and isinstance(node.tag, str):
            v = self.own(node, "opacity")
            if v is not None:
                try:
                    prod *= float(v.rstrip("%")) / (100.0 if v.endswith("%") else 1.0)
                except ValueError:
                    pass
            node = node.getparent()
        return prod

    def displayed(self, el):
        node = el
        while node is not None and isinstance(node.tag, str):
            if (self.own(node, "display") or "").strip() == "none":
                return False
            node = node.getparent()
        return True


# --------------------------------------------------------------------------
# colours
# --------------------------------------------------------------------------
try:  # PIL knows all CSS colour names
    from PIL import ImageColor as _IC
except Exception:  # pragma: no cover
    _IC = None


def norm_color(value):
    """Return '#rrggbb' or None for none/url()/currentColor/unparseable."""
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("", "none", "transparent", "currentcolor", "inherit") or v.startswith("url("):
        return None
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return "#" + "".join(ch * 2 for ch in v[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return v
    if re.fullmatch(r"#[0-9a-f]{8}", v):
        return v[:7]
    m = re.fullmatch(r"rgba?\(([^)]*)\)", v)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        try:
            rgb = []
            for p in parts[:3]:
                rgb.append(round(float(p[:-1]) * 2.55) if p.endswith("%") else round(float(p)))
            return "#%02x%02x%02x" % tuple(max(0, min(255, c)) for c in rgb)
        except ValueError:
            return None
    if _IC is not None:
        try:
            r, g, b = _IC.getrgb(v)[:3]
            return "#%02x%02x%02x" % (r, g, b)
        except ValueError:
            return None
    return None


def luminance(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def hex_to_hsl(hexcolor):
    import colorsys
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0, s, l


# --------------------------------------------------------------------------
# element geometry (bbox in the root user space)
# --------------------------------------------------------------------------
def local_bbox(el, ids=None, _depth=0):
    """bbox of a single graphic element in its own coordinate system
    (element's own transform NOT applied). Returns None if unknown."""
    t = local(el.tag)
    try:
        if t == "rect":
            x, y = fnum(el.get("x")), fnum(el.get("y"))
            w, h = fnum(el.get("width")), fnum(el.get("height"))
            return (x, y, x + w, y + h)
        if t == "circle":
            cx, cy, r = fnum(el.get("cx")), fnum(el.get("cy")), fnum(el.get("r"))
            return (cx - r, cy - r, cx + r, cy + r)
        if t == "ellipse":
            cx, cy = fnum(el.get("cx")), fnum(el.get("cy"))
            rx, ry = fnum(el.get("rx")), fnum(el.get("ry"))
            return (cx - rx, cy - ry, cx + rx, cy + ry)
        if t == "line":
            x1, y1, x2, y2 = (fnum(el.get(k)) for k in ("x1", "y1", "x2", "y2"))
            return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if t in ("polyline", "polygon"):
            nums = [float(x) for x in NUM_RE.findall(el.get("points", ""))]
            pts = list(zip(nums[0::2], nums[1::2]))
            if not pts:
                return None
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            return (min(xs), min(ys), max(xs), max(ys))
        if t == "path":
            return path_bbox(el.get("d", ""))
        if t == "image":
            x, y = fnum(el.get("x")), fnum(el.get("y"))
            return (x, y, x + fnum(el.get("width")), y + fnum(el.get("height")))
        if t == "text":
            size = fnum(el.get("font-size"), 16.0)
            txt = "".join(el.itertext()).strip()
            x, y = fnum(el.get("x")), fnum(el.get("y"))
            w = len(txt) * size * 0.58
            if fnum(el.get("textLength"), 0) > 0:
                w = fnum(el.get("textLength"))
            anchor = el.get("text-anchor", "start")
            if anchor == "middle":
                x -= w / 2
            elif anchor == "end":
                x -= w
            return (x, y - size * 0.8, x + w, y + size * 0.25)
        if t == "use" and ids is not None and _depth < 6:
            href = get_href(el)
            if href and href.startswith("#") and href[1:] in ids:
                tgt = ids[href[1:]]
                inner = subtree_bbox(tgt, ids, IDENTITY, _depth + 1, include_self_transform=True)
                if inner:
                    tx, ty = fnum(el.get("x")), fnum(el.get("y"))
                    return (inner[0] + tx, inner[1] + ty, inner[2] + tx, inner[3] + ty)
    except PathParseError:
        return None
    return None


def transform_bbox(m, bb):
    x0, y0, x1, y1 = bb
    pts = [mat_apply(m, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def subtree_bbox(el, ids, parent_m=IDENTITY, _depth=0, include_self_transform=True):
    """Union bbox of everything painted under el (skips non-rendered containers)."""
    t = local(el.tag)
    if t in NON_RENDERED and _depth > 0:
        return None
    m = parent_m
    if include_self_transform:
        m = mat_mul(parent_m, parse_transform(el.get("transform")))
    if t in GRAPHIC_TAGS:
        bb = local_bbox(el, ids, _depth)
        return transform_bbox(m, bb) if bb else None
    out = None
    for ch in el:
        if isinstance(ch.tag, str):
            out = union(out, subtree_bbox(ch, ids, m, _depth + 1, True))
    return out


_CLIP_RE = re.compile(r"url\(\s*['\"]?#([^)'\"\s]+)")


def clip_bbox(el, ids, parents):
    """Root-space bbox that ancestors' (and el's own) clip-path attributes confine el to.

    Approximation: a clipPath's extent is the union of its children's bboxes, placed with the
    matrix of the element that references it (clipPathUnits=objectBoundingBox is ignored).
    Returns None when el is unclipped.
    """
    chain, cur = [], el
    while cur is not None:
        chain.append(cur)
        cur = parents.get(cur)
    chain.reverse()                      # root ... el
    m, out = IDENTITY, None
    for node in chain:
        m = mat_mul(m, parse_transform(node.get("transform")))
        cp = node.get("clip-path")
        mt = _CLIP_RE.search(cp) if cp else None
        if not mt:
            continue
        cpe = (ids or {}).get(mt.group(1))
        if cpe is None or local(cpe.tag) != "clipPath":
            continue
        box = None
        for ch in cpe:
            if isinstance(ch.tag, str):
                box = union(box, subtree_bbox(ch, ids, m, 1, True))
        if box is None:
            continue
        out = box if out is None else (max(out[0], box[0]), max(out[1], box[1]), min(out[2], box[2]), min(out[3], box[3]))
    return out


def walk_painted(root, ids=None):
    """Yield (element, matrix_to_root_space) for every painted graphic element
    in document order, skipping defs/clipPath/etc."""
    def rec(el, m):
        t = local(el.tag)
        if t in NON_RENDERED and el is not root:
            return
        cur = mat_mul(m, parse_transform(el.get("transform"))) if el is not root else m
        if t in GRAPHIC_TAGS:
            yield el, cur
            return
        for ch in el:
            if isinstance(ch.tag, str):
                yield from rec(ch, cur)
    yield from rec(root, IDENTITY)


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------
def load_registry(directory=None):
    """Load every styles/registry/*.json. Each file is a JSON list of style
    objects or {"styles": [...]}. Returns dict id -> style (with '_file')."""
    directory = Path(directory) if directory else REGISTRY_DIR
    styles = {}
    for f in sorted(directory.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit("Invalid JSON in %s: %s" % (f, exc))
        items = data["styles"] if isinstance(data, dict) and "styles" in data else data
        if not isinstance(items, list):
            raise SystemExit("%s must contain a list of styles" % f)
        for s in items:
            s["_file"] = f.name
            if s.get("id") in styles:
                raise SystemExit("Duplicate style id %r (in %s and %s)" % (s.get("id"), styles[s["id"]]["_file"], f.name))
            styles[s["id"]] = s
    return styles


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
