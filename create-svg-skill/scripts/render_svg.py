#!/usr/bin/env python3
"""render_svg.py - render SVGs to PNG with headless Chromium (Playwright),
optionally build a labelled contact sheet and print pixel-level analysis.

Usage:
  render_svg.py art.svg                       -> art.png next to the file (1024px wide)
  render_svg.py art.svg -o /tmp/prev.png -w 800 --bg "#ffffff"
  render_svg.py a.svg b.svg c.svg --sheet compare.png --cols 3
  render_svg.py art.svg --analyze             -> also print JSON pixel stats

--bg accepts a CSS colour, "transparent", or "checker".
The SVG is rendered through <img>, i.e. the way it behaves when embedded or
opened as a standalone file: no scripts, no external fetches.

Analysis fields (see SKILL.md, step "inspect"):
  blank              nothing visible was drawn
  alpha_coverage_pct share of pixels that are not fully transparent
  content_bbox_pct   bounding box of non-transparent pixels as % of the canvas
  edge_touch         which canvas edges have painted pixels (useful when the
                     art is NOT meant to bleed)
  rendered_colors    number of distinct RGB values in the raster
  top32_share_pct    share of pixels covered by the 32 most common colours
                     (pixel art with crisp edges stays ~100%; anti-aliasing
                     leaks it)
  mean_luma/contrast average luminance and its standard deviation
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtools import parse_svg, parse_viewbox, fnum  # noqa: E402

CHECKER_CSS = (
    "background-color:#fff;background-image:linear-gradient(45deg,#d8d8d8 25%,transparent 25%,transparent 75%,#d8d8d8 75%),"
    "linear-gradient(45deg,#d8d8d8 25%,transparent 25%,transparent 75%,#d8d8d8 75%);background-size:24px 24px;background-position:0 0,12px 12px;"
)


def canvas_size(svg_path, width):
    root, err = parse_svg(str(svg_path))
    if root is None:
        raise SystemExit("cannot parse %s: %s" % (svg_path, err))
    vb = parse_viewbox(root)
    if vb:
        w, h = vb[2], vb[3]
    else:
        w, h = fnum(root.get("width"), 512), fnum(root.get("height"), 512)
    if w <= 0 or h <= 0:
        w, h = 512, 512
    return width, max(1, int(round(width * h / w)))


def render_many(jobs, bg="#ffffff", timeout_ms=20000):
    """jobs: list of (svg_path, out_png, width). Returns list of error strings/None."""
    from playwright.sync_api import sync_playwright

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for svg_path, out_png, width in jobs:
            try:
                w, h = canvas_size(svg_path, width)
                data = base64.b64encode(Path(svg_path).read_bytes()).decode()
                if bg == "transparent":
                    body_bg = "background:transparent;"
                elif bg == "checker":
                    body_bg = CHECKER_CSS
                else:
                    body_bg = "background:%s;" % bg
                html = (
                    "<!doctype html><html><body style='margin:0;%s'>"
                    "<img id='i' src='data:image/svg+xml;base64,%s' style='display:block;width:%dpx;height:%dpx'>"
                    "</body></html>" % (body_bg, data, w, h)
                )
                ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                page = ctx.new_page()
                page.set_content(html, wait_until="load", timeout=timeout_ms)
                ok = page.evaluate("() => { const i = document.getElementById('i'); return i.complete && i.naturalWidth > 0; }")
                page.screenshot(path=str(out_png), omit_background=(bg == "transparent"),
                                clip={"x": 0, "y": 0, "width": w, "height": h})
                ctx.close()
                errors.append(None if ok else "browser could not decode the SVG (invalid or unsupported)")
            except Exception as exc:  # noqa: BLE001
                errors.append("render failed: %s" % str(exc).splitlines()[0][:200])
        browser.close()
    return errors


def analyze_png(svg_path, width=512):
    """Render on transparent + analyse. Returns dict."""
    import tempfile
    from PIL import Image

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "a.png"
        err = render_many([(svg_path, out, width)], bg="transparent")[0]
        if err:
            return {"error": err}
        im = Image.open(out).convert("RGBA")
    w, h = im.size
    px = im.load()
    alpha = im.getchannel("A")
    hist = alpha.histogram()
    total = w * h
    painted = total - hist[0]
    res = {"size": [w, h], "blank": painted == 0}
    if painted == 0:
        return res
    res["alpha_coverage_pct"] = round(100 * painted / total, 1)
    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        res["content_bbox_pct"] = [round(100 * bbox[0] / w, 1), round(100 * bbox[1] / h, 1),
                                   round(100 * bbox[2] / w, 1), round(100 * bbox[3] / h, 1)]
        res["edge_touch"] = {
            "left": bbox[0] <= 0, "top": bbox[1] <= 0, "right": bbox[2] >= w, "bottom": bbox[3] >= h,
        }
    # colours on white composite
    from PIL import ImageChops
    white = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, im).convert("RGB")
    colors = flat.getcolors(maxcolors=total) or []
    res["rendered_colors"] = len(colors)
    top32 = sum(c for c, _ in sorted(colors, reverse=True)[:32])
    res["top32_share_pct"] = round(100 * top32 / total, 1)
    hist_l = flat.convert("L").histogram()
    mean = sum(i * n for i, n in enumerate(hist_l)) / total
    var = sum(n * (i - mean) ** 2 for i, n in enumerate(hist_l)) / total
    res["mean_luma"] = round(mean / 255, 3)
    res["contrast"] = round(math.sqrt(var) / 255, 3)
    if res["alpha_coverage_pct"] >= 99.0:
        # full-bleed art: measure the subject against the dominant border colour
        border = Counter()
        fp = flat.load()
        for x in range(w):
            border[fp[x, 0]] += 1
            border[fp[x, h - 1]] += 1
        for y in range(h):
            border[fp[0, y]] += 1
            border[fp[w - 1, y]] += 1
        bgc = border.most_common(1)[0][0]
        diff = ImageChops.difference(flat, Image.new("RGB", flat.size, bgc)).convert("L")
        sb = diff.point(lambda v: 255 if v > 40 else 0).getbbox()
        res["full_bleed"] = True
        if sb:
            res["subject_bbox_pct"] = [round(100 * sb[0] / w, 1), round(100 * sb[1] / h, 1),
                                       round(100 * sb[2] / w, 1), round(100 * sb[3] / h, 1)]
            res["subject_edge_touch"] = {"left": sb[0] <= 0, "top": sb[1] <= 0, "right": sb[2] >= w, "bottom": sb[3] >= h}
            res["subject_fill_pct"] = round(100 * (sb[2] - sb[0]) * (sb[3] - sb[1]) / total, 1)
    # left/right & top/bottom ink balance (alpha-weighted)
    lw = rw = tw = bw = 0
    a = alpha.load()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            v = a[x, y]
            if not v:
                continue
            if x < w / 2:
                lw += v
            else:
                rw += v
            if y < h / 2:
                tw += v
            else:
                bw += v
    if lw + rw:
        res["ink_balance_lr_pct"] = round(100 * (rw - lw) / (rw + lw), 1)
    if tw + bw:
        res["ink_balance_tb_pct"] = round(100 * (bw - tw) / (bw + tw), 1)
    return res


def build_sheet(items, out_path, cols, cell=420, bg="#ffffff"):
    """items: list of (png_path, label)."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.load_default(size=15)
    except TypeError:  # older Pillow
        font = ImageFont.load_default()
    pad, label_h = 16, 30
    rows = (len(items) + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = rows * (cell + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), "#e9e9ee")
    d = ImageDraw.Draw(sheet)
    for i, (png, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        im = Image.open(png).convert("RGBA")
        im.thumbnail((cell, cell), Image.LANCZOS)
        tile = Image.new("RGB", (cell, cell), bg)
        tile.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
        sheet.paste(tile, (x, y + label_h))
        d.text((x + 2, y + 6), label, fill="#222222", font=font)
    sheet.save(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out", help="output PNG (single input only)")
    ap.add_argument("-w", "--width", type=int, default=1024)
    ap.add_argument("--bg", default="#ffffff")
    ap.add_argument("--sheet", help="write a contact sheet PNG of all inputs")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--analyze", action="store_true", help="print pixel analysis JSON")
    ap.add_argument("--outdir", help="directory for PNGs (default: next to each SVG)")
    args = ap.parse_args()

    if args.out and len(args.files) > 1:
        sys.exit("-o works with a single input; use --outdir or --sheet")
    jobs = []
    for f in args.files:
        fp = Path(f)
        if args.out:
            out = Path(args.out)
        else:
            out = (Path(args.outdir) if args.outdir else fp.parent) / (fp.stem + ".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        jobs.append((fp, out, args.width))
    errs = render_many(jobs, bg=args.bg)
    rc = 0
    for (fp, out, _), err in zip(jobs, errs):
        if err:
            print("FAIL %s: %s" % (fp, err))
            rc = 1
        else:
            print("rendered %s -> %s" % (fp, out))
    if args.sheet:
        ok = [(o, Path(f).stem) for (f, o, _), e in zip(jobs, errs) if not e]
        if ok:
            Path(args.sheet).parent.mkdir(parents=True, exist_ok=True)
            build_sheet(ok, args.sheet, args.cols)
            print("contact sheet -> %s" % args.sheet)
    if args.analyze:
        out = {}
        for (fp, _o, _w), e in zip(jobs, errs):
            out[str(fp)] = {"error": e} if e else analyze_png(fp)
        print(json.dumps(out, indent=2))
    sys.exit(rc)


if __name__ == "__main__":
    main()
