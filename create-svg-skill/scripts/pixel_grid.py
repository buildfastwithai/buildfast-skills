#!/usr/bin/env python3
"""pixel_grid.py - turn an ASCII sprite into a crisp, editable SVG.

Pixel styles must sit on a strict grid with hard edges. Hand-typing hundreds of
<rect>s is error-prone, so author the sprite as text and let this tool merge it
into one <path> per colour (greedy rectangle merge, integer coordinates,
shape-rendering="crispEdges").

Sprite file format
  ; comment lines start with ';'
  @k=#1b1b2f            palette entry: '@' + one character + '=' + colour
  @o=#e8702a
  ................      '.' (or space) is transparent, any other character is a palette key
  ....kk......kk....
  ...kook....kook...

Usage
  pixel_grid.py sprite.txt -o sprite.svg [--bg "#2b2d42"] [--pad 2] [--mirror]
                [--outline "#111111"] [--title "Pixel fox"] [--palette "k=#111,o=#f80"]

  --mirror    the sprite text is the LEFT half; the right half is mirrored automatically
  --outline   add a 1-cell outline around all opaque pixels (4-neighbour), in the given colour
  --bg        solid background rect behind the sprite (full canvas, includes padding)
  --pad       transparent/bg margin in cells around the sprite
  --frame     alias for --pad 0 --bg none (default behaviour)
"""
from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

TRANSPARENT = {".", " "}


def parse_sprite(text, palette_override=None):
    palette = OrderedDict()
    rows = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            if rows:
                rows.append("")  # blank rows inside a sprite are transparent rows
            continue
        if line.lstrip().startswith(";"):
            continue
        if line.startswith("@"):
            body = line[1:].split(";")[0].strip()
            if "=" not in body or len(body.split("=")[0].strip()) != 1:
                raise SystemExit("bad palette line: %r (use @k=#rrggbb)" % line)
            key, val = body.split("=", 1)
            palette[key.strip()] = val.strip()
            continue
        rows.append(line)
    while rows and rows[-1] == "":
        rows.pop()
    if palette_override:
        for kv in palette_override.split(","):
            k, v = kv.split("=", 1)
            palette[k.strip()] = v.strip()
    if not rows:
        raise SystemExit("sprite has no pixel rows")
    return rows, palette


def to_grid(rows, mirror=False):
    width = max(len(r) for r in rows)
    grid = []
    for r in rows:
        r = r.ljust(width, ".")
        if mirror:
            r = r + r[::-1]
        grid.append(list(r))
    return grid


def add_outline(grid, key="\0"):
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] in TRANSPARENT:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] not in TRANSPARENT and grid[ny][nx] != key:
                        out[y][x] = key
                        break
    return out


def pad_grid(grid, n):
    if n <= 0:
        return grid
    w = len(grid[0]) + 2 * n
    blank = ["."] * w
    return [blank[:] for _ in range(n)] + [["."] * n + row + ["."] * n for row in grid] + [blank[:] for _ in range(n)]


def merge_rects(grid, key):
    """Greedy maximal-rectangle cover of all cells == key. Returns [(x, y, w, h)]."""
    h, w = len(grid), len(grid[0])
    seen = [[False] * w for _ in range(h)]
    rects = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] != key or seen[y][x]:
                continue
            x2 = x
            while x2 + 1 < w and grid[y][x2 + 1] == key and not seen[y][x2 + 1]:
                x2 += 1
            y2 = y
            while y2 + 1 < h and all(grid[y2 + 1][i] == key and not seen[y2 + 1][i] for i in range(x, x2 + 1)):
                y2 += 1
            for yy in range(y, y2 + 1):
                for xx in range(x, x2 + 1):
                    seen[yy][xx] = True
            rects.append((x, y, x2 - x + 1, y2 - y + 1))
    return rects


def build_svg(grid, palette, bg=None, title="Pixel art", outline=None):
    h, w = len(grid), len(grid[0])
    keys = []
    for row in grid:
        for c in row:
            if c not in TRANSPARENT and c not in keys:
                keys.append(c)
    missing = [k for k in keys if k != "\0" and k not in palette]
    if missing:
        raise SystemExit("no palette colour for key(s): %s" % ", ".join(repr(m) for m in missing))
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" shape-rendering="crispEdges">' % (w, h),
        "  <title>%s</title>" % escape(title),
    ]
    if bg and bg.lower() != "none":
        lines.append('  <rect id="background" width="%d" height="%d" fill=%s/>' % (w, h, quoteattr(bg)))
    lines.append('  <g id="sprite">')
    # outline first so the sprite paints over it
    order = (["\0"] if "\0" in keys else []) + [k for k in keys if k != "\0"]
    for k in order:
        color = outline if k == "\0" else palette[k]
        rects = merge_rects(grid, k)
        d = "".join("M%d %dh%dv%dh-%dz" % (x, y, rw, rh, rw) for x, y, rw, rh in rects)
        name = "outline" if k == "\0" else "c-" + (k if k.isalnum() else "x%02x" % ord(k))
        lines.append('    <path id=%s fill=%s d="%s"/>' % (quoteattr(name), quoteattr(color), d))
    lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n", len(keys)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sprite", help="sprite text file or - for stdin")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--bg")
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--outline")
    ap.add_argument("--title", default="Pixel art")
    ap.add_argument("--palette", help='extra/override entries, e.g. "k=#111111,o=#ff8800"')
    args = ap.parse_args()

    text = sys.stdin.read() if args.sprite == "-" else Path(args.sprite).read_text(encoding="utf-8")
    rows, palette = parse_sprite(text, args.palette)
    grid = to_grid(rows, args.mirror)
    if args.outline:
        grid = add_outline(grid)
    grid = pad_grid(grid, args.pad)
    svg, n = build_svg(grid, palette, args.bg, args.title, args.outline)
    Path(args.out).write_text(svg, encoding="utf-8")
    print("wrote %s  (%dx%d grid, %d colours, %d bytes)" % (args.out, len(grid[0]), len(grid), n, len(svg)))


if __name__ == "__main__":
    main()
