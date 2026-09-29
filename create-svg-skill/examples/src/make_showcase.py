#!/usr/bin/env python3
"""More fox variants (same frozen scene spec as make_fox_set.py) + non-fox showcase pieces.

Usage: python3 make_showcase.py OUTDIR [name ...]
Low-poly needs a flat render of fox.svg as its colour source: it renders one with
scripts/render_svg.py (Chromium) if OUTDIR/fox.svg exists.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILL / "scripts"))
from make_fox_set import (TAIL, TAIL_TIP, BODY, HAUNCH, CHEST, LEG, LEG2, HEAD, MUZZLE,  # noqa: E402
                          EAR_L, EAR_R, EYE, CHEEK, HDR)
from text_to_path import text_path  # noqa: E402

FONTS = HERE / "fonts"
ANTON = str(FONTS / "anton-latin-400-normal.woff2")
UNB = str(FONTS / "unbounded-latin-800-normal.woff2")
SERIF = str(FONTS / "instrument-serif-latin-400-normal.woff2")
FOX_PARTS = [TAIL, BODY, LEG2, LEG, HEAD]           # silhouette pieces


def silhouette(**attrs):
    a = " ".join('%s="%s"' % (k.replace("_", "-"), v) for k, v in attrs.items())
    return "".join('<path d="%s" %s/>' % (p, a) for p in FOX_PARTS)


# ------------------------------------------------------------------------------------------
# LOW POLY: mesh from contour + interior points, facets shaded from a height field
# ------------------------------------------------------------------------------------------
def low_poly(out):
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    from scipy.spatial import Delaunay

    png, keyed = out / "_fox_flat.png", out / "_fox_keyed.svg"
    src = (out / "fox.svg").read_text(encoding="utf-8")
    keyed.write_text(src.replace('fill="#f4efe6"', 'fill="#00ff00"').replace('fill="#e5dccb"', 'fill="#00ff00"'), encoding="utf-8")
    subprocess.run([sys.executable, str(SKILL / "scripts/render_svg.py"), str(keyed), "-o", str(png), "-w", "1024"],
                   check=True, capture_output=True)
    im = np.asarray(Image.open(png).convert("RGB")).astype(float)
    png.unlink(); keyed.unlink()
    mask = ~((im[..., 1] > 200) & (im[..., 0] < 80) & (im[..., 2] < 80))
    mask = ndimage.binary_opening(mask, iterations=2)
    dist = ndimage.distance_transform_edt(mask)
    height = np.sqrt(dist) * 9.0
    gy, gx = np.gradient(ndimage.gaussian_filter(height, 6))
    rnd = random.Random(3)

    pts = []
    edge = mask ^ ndimage.binary_erosion(mask, iterations=1)
    ey, ex = np.nonzero(edge)
    order = list(range(0, len(ex), 22))
    pts += [(ex[i], ey[i]) for i in order]
    # interior colour boundaries (chest, muzzle, legs) keep their shapes
    q = (im[..., 0] // 24) * 10000 + (im[..., 1] // 24) * 100 + im[..., 2] // 24
    cb = (np.abs(np.diff(q, axis=0, prepend=q[:1])) + np.abs(np.diff(q, axis=1, prepend=q[:, :1]))) > 0
    cb &= ndimage.binary_erosion(mask, iterations=4)
    cy, cx = np.nonzero(cb)
    pts += [(cx[i], cy[i]) for i in range(0, len(cx), 30)]
    for y in range(0, 1025, 34):                         # interior fill (denser in the fox)
        for x in range(0, 1025, 34):
            jx, jy = x + rnd.uniform(-11, 11), y + rnd.uniform(-11, 11)
            xi, yi = int(min(1023, max(0, jx))), int(min(1023, max(0, jy)))
            if mask[yi, xi] or (x % 102 == 0 and y % 68 == 0):
                pts.append((jx, jy))
    for i in range(0, 1025, 128):                        # frame
        pts += [(i, 0), (i, 1024), (0, i), (1024, i)]
    for i in range(28):                                  # sun rim
        a = i * math.pi * 2 / 28
        pts.append((760 + 150 * math.cos(a), 300 + 150 * math.sin(a)))
    pts.append((760, 300))
    for i in range(24):                                  # ground ridge
        pts.append((i * 1024 / 23, 846 + rnd.uniform(-6, 6)))
    pts = np.clip(np.array(pts, float), 0, 1024)
    tri = Delaunay(pts)

    light = np.array([-0.55, -0.65, 0.52]); light /= np.linalg.norm(light)
    polys = {"sky": [], "ground": [], "fox": []}
    for s in tri.simplices:
        p = pts[s]
        c = p.mean(0)
        xi, yi = int(min(1023, c[0])), int(min(1023, c[1]))
        a = abs((p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[1][1] - p[0][1]) * (p[2][0] - p[0][0])) / 2
        if a < 4:
            continue
        if mask[yi, xi]:
            col = im[yi, xi]
            n = np.array([-gx[yi, xi], -gy[yi, xi], 1.0]); n /= np.linalg.norm(n)
            k = 0.78 + 0.34 * max(0, n @ light) + rnd.uniform(-0.025, 0.025)
            layer = "fox"
        elif c[1] > 846:
            t = (c[1] - 846) / 178
            col = np.array([0x5c, 0x7c, 0x4f]) * (1 - t) + np.array([0x2e, 0x46, 0x33]) * t
            k = 1 + rnd.uniform(-0.07, 0.07)
            layer = "ground"
        else:
            t = c[1] / 846
            col = np.array([0x2b, 0x3a, 0x67]) * (1 - t) + np.array([0xf2, 0x9e, 0x6d]) * t
            d = math.hypot(c[0] - 760, c[1] - 300)
            if d < 150:
                col = np.array([0xff, 0xd8, 0x9a], float)
            k = 1 + rnd.uniform(-0.06, 0.06)
            layer = "sky"
        rgb = np.clip(col * k, 0, 255).astype(int)
        hexc = "#%02x%02x%02x" % tuple(rgb)
        polys[layer].append('<polygon points="%s" fill="%s" stroke="%s"/>' % (
            " ".join("%.1f,%.1f" % tuple(v) for v in p), hexc, hexc))
    body = "".join('<g id="%s" stroke-width="0.8" stroke-linejoin="round">%s</g>' % (k, "".join(v)) for k, v in polys.items())
    return HDR + ('<title id="t">Low Poly Fox</title><desc id="d">Low poly: triangulated mesh, flat facets shaded by '
                  'facing direction to a top-left light, dusk sky and meadow meshes.</desc>' + body + "</svg>\n")


# ------------------------------------------------------------------------------------------
# RISOGRAPH: two inks, multiply overprint, halftone, misregistration, grain
# ------------------------------------------------------------------------------------------
def riso(out):
    pink, blue, paper = "#ff48b0", "#0078bf", "#f4efe4"
    title, _ = text_path(ANTON, "WILD", size=290, x=512, y=330, anchor="middle", tracking=6)
    sub, _ = text_path(ANTON, "FOX CLUB  ·  NO. 07", size=40, x=512, y=985, anchor="middle", tracking=10)
    return HDR + """<title id="t">Riso Fox</title><desc id="d">Risograph: fluorescent pink and blue inks overprinting (multiply), halftone dot shading, slight misregistration, paper grain.</desc>
<defs>
<clipPath id="sheet"><rect width="1024" height="1024"/></clipPath>
<pattern id="dot-p" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(15)"><circle cx="7" cy="7" r="4.2" fill="{pink}"/></pattern>
<pattern id="dot-b" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(75)"><circle cx="6" cy="6" r="3.1" fill="{blue}"/></pattern>
<pattern id="dot-b2" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(75)"><circle cx="5" cy="5" r="1.7" fill="{blue}"/></pattern>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 0.25  0 0 0 0 0.2  0 0 0 0 0.15  0 0 0 -1.6 1.05"/><feComposite in2="SourceGraphic" operator="in"/></filter>
</defs>
<rect id="paper" width="1024" height="1024" fill="{paper}"/>
<g id="ink-blue" style="mix-blend-mode:multiply" clip-path="url(#sheet)"><g transform="translate(-5 3)">
<path d="{title}" fill="{blue}" opacity=".9"/>
<rect x="0" y="846" width="1024" height="100" fill="url(#dot-b2)"/>
<path d="M0 846H1024" stroke="{blue}" stroke-width="8"/>
<path d="{sub}" fill="{blue}"/>
<g id="fox-blue"><path d="{HAUNCH}" fill="url(#dot-b)"/><path d="{LEG}" fill="{blue}"/><path d="{LEG2}" fill="{blue}"/><path d="{EAR_L}" fill="{blue}"/><path d="{EAR_R}" fill="{blue}"/><path d="{EYE}" fill="{blue}"/><circle cx="236" cy="488" r="11" fill="{blue}"/><path d="{TAIL}" fill="url(#dot-b2)"/></g>
</g></g>
<g id="ink-pink" style="mix-blend-mode:multiply" transform="translate(4 -3)">
<circle cx="800" cy="210" r="120" fill="url(#dot-p)"/>
<g id="fox-pink"><path d="{TAIL}" fill="{pink}"/><path d="{BODY}" fill="{pink}"/><path d="{HEAD}" fill="{pink}"/><path d="{LEG2}" fill="{pink}"/></g>
<g fill="{paper}"><path d="{TAIL_TIP}"/><path d="{CHEST}"/><path d="{MUZZLE}"/><path d="{CHEEK}"/></g>
<path d="{CHEST}" fill="url(#dot-p)" opacity=".35"/>
</g>
<rect id="grain-overlay" width="1024" height="1024" filter="url(#grain)" opacity=".5" fill="{paper}"/>
</svg>
""".format(**dict(globals(), pink=pink, blue=blue, paper=paper, title=title, sub=sub))


# ------------------------------------------------------------------------------------------
# COMIC BOOK: burst, speed lines, halftone shading, thick ink, lettering
# ------------------------------------------------------------------------------------------
def comic(out):
    cx, cy = 400, 470
    burst = []
    for i in range(36):
        r = 700 if i % 2 == 0 else 470
        a = math.radians(i * 10)
        burst.append("%.0f,%.0f" % (cx + r * math.cos(a), cy + r * math.sin(a)))
    speed = "".join('<path d="M%d %d L%d %d"/>' % (cx + 330 * math.cos(math.radians(a)), cy + 330 * math.sin(math.radians(a)),
                                                  cx + 900 * math.cos(math.radians(a)), cy + 900 * math.sin(math.radians(a)))
                    for a in range(3, 360, 9))
    yip, _ = text_path(ANTON, "YIP!", size=150, x=740, y=260, anchor="middle", tracking=4)
    cap, _ = text_path(ANTON, "MEANWHILE, IN THE WOODS...", size=36, x=78, y=112, tracking=2)
    ink = "#111"
    return HDR + """<title id="t">Comic Fox</title><desc id="d">Comic book: action burst, speed lines, halftone shading, thick-to-thin black inks, caption box and outlined lettering.</desc>
<defs>
<clipPath id="panel"><rect width="1024" height="1024"/></clipPath>
<pattern id="ht-dark" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="12" height="12" fill="#e63946"/><circle cx="6" cy="6" r="3.4" fill="#9e1b2a"/></pattern>
<pattern id="ht-bg" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="18" height="18" fill="#ffd60a"/><circle cx="9" cy="9" r="4" fill="#ff9f1c"/></pattern>
<pattern id="ht-sky" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="16" height="16" fill="#00b4d8"/><circle cx="8" cy="8" r="3" fill="#0077b6"/></pattern>
</defs>
<rect id="panel-bg" width="1024" height="1024" fill="url(#ht-sky)"/>
<polygon id="burst" clip-path="url(#panel)" points="{burst}" fill="url(#ht-bg)" stroke="{ink}" stroke-width="6" stroke-linejoin="miter"/>
<g id="speed-lines" clip-path="url(#panel)" stroke="#fff8e1" stroke-width="5" opacity=".75">{speed}</g>
<rect id="ground" y="846" width="1024" height="178" fill="#2a9d8f" stroke="{ink}" stroke-width="8" clip-path="url(#panel)"/>
<g id="fox-color">
<path d="{TAIL}" fill="#e63946"/><path d="{BODY}" fill="#f77f00"/><path d="{HAUNCH}" fill="url(#ht-dark)"/><path d="{TAIL_TIP}" fill="#fff8e1"/>
<path d="{LEG2}" fill="#3d1f14"/><path d="{CHEST}" fill="#fff8e1"/><path d="{LEG}" fill="#2a1510"/>
<path d="{HEAD}" fill="#f77f00"/><path d="{CHEEK}" fill="#fff8e1"/><path d="{MUZZLE}" fill="#fff8e1"/><path d="{EAR_L}" fill="{ink}"/><path d="{EAR_R}" fill="{ink}"/></g>
<g id="ink" fill="none" stroke="{ink}" stroke-linejoin="round" stroke-linecap="round">
<g stroke-width="13"><path d="{TAIL}"/><path d="{BODY}"/><path d="{HEAD}"/></g>
<g stroke-width="6"><path d="{TAIL_TIP}"/><path d="{HAUNCH}"/><path d="{CHEST}"/><path d="{MUZZLE}"/><path d="{LEG}"/><path d="{LEG2}"/></g>
<path d="M560 600q30 20 44 52M620 560q22 18 30 40M820 600q20 30 20 70" stroke-width="5"/></g>
<g id="face"><path d="{EYE}" fill="{ink}"/><circle cx="236" cy="488" r="12" fill="{ink}"/><circle cx="344" cy="446" r="4" fill="#fff"/></g>
<g id="balloon"><path d="M560 150 C560 60 920 60 920 150 C920 240 700 250 640 236 L560 300 L590 222 C570 205 560 180 560 150Z" fill="#fff" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/>
<path d="{yip}" fill="#e63946" stroke="{ink}" stroke-width="6" paint-order="stroke" stroke-linejoin="round" transform="rotate(-4 740 200)"/></g>
<g id="caption"><rect x="60" y="64" width="468" height="66" fill="#ffd60a" stroke="{ink}" stroke-width="6"/><path d="{cap}" fill="{ink}"/></g>
<rect id="panel-border" x="10" y="10" width="1004" height="1004" fill="none" stroke="{ink}" stroke-width="20"/>
</svg>
""".format(**dict(globals(), burst=" ".join(burst), speed=speed, yip=yip, cap=cap, ink=ink))


# ------------------------------------------------------------------------------------------
# STICKER: die-cut white border, drop shadow, glossy streak, dark outlines
# ------------------------------------------------------------------------------------------
def sticker(out):
    ink = "#1c1c28"
    return HDR + """<title id="t">Fox Sticker</title><desc id="d">Sticker: thick white die-cut border with soft shadow, saturated flat fills, dark outlines, glossy highlight.</desc>
<defs>
<g id="cut">{sil}</g>
<filter id="lift" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="14" stdDeviation="12" flood-color="#1c1c28" flood-opacity=".35"/></filter>
</defs>
<g id="border" filter="url(#lift)"><use href="#cut" fill="#fff" stroke="#fff" stroke-width="64" stroke-linejoin="round"/></g>
<g id="art" stroke="{ink}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round">
<path d="{TAIL}" fill="#ff6b35"/><path d="{TAIL_TIP}" fill="#fffaf0"/><path d="{BODY}" fill="#ff7f3f"/><path d="{HAUNCH}" fill="#ff5d73" stroke-width="6"/>
<path d="{LEG2}" fill="#3b2230"/><path d="{CHEST}" fill="#fffaf0" stroke-width="6"/><path d="{LEG}" fill="#2b1a24"/>
<path d="{HEAD}" fill="#ff7f3f"/><path d="{CHEEK}" fill="#fffaf0" stroke-width="6"/><path d="{MUZZLE}" fill="#fffaf0" stroke-width="6"/>
<path d="{EAR_L}" fill="#ff5d73" stroke-width="5"/><path d="{EAR_R}" fill="#ff5d73" stroke-width="5"/></g>
<g id="face" fill="{ink}"><ellipse cx="342" cy="452" rx="20" ry="14"/><circle cx="348" cy="447" r="5" fill="#fff"/><circle cx="238" cy="488" r="13"/><ellipse cx="385" cy="505" rx="22" ry="12" fill="#ff9fb0"/></g>
<g id="gloss" fill="#fff" opacity=".55"><path d="M470 540 C560 520 640 560 700 630 C690 640 676 644 664 640 C620 590 560 564 488 566 C478 560 470 552 470 540Z"/><circle cx="716" cy="668" r="9"/><path d="M372 280 L384 250 L396 292Z"/></g>
<g id="badge" transform="rotate(-10 820 250)"><circle cx="820" cy="250" r="92" fill="#ffc857" stroke="#fff" stroke-width="18"/><circle cx="820" cy="250" r="92" fill="none" stroke="{ink}" stroke-width="7"/><path d="{hey}" fill="{ink}"/></g>
</svg>
""".format(**dict(globals(), ink=ink, sil=silhouette(), hey=text_path(ANTON, "HEY!", size=74, x=820, y=278, anchor="middle", tracking=2)[0]))


# ------------------------------------------------------------------------------------------
# SUMI-E: tapered brush strokes, ink wash, mist, hanko seal
# ------------------------------------------------------------------------------------------
def _bez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def brush(pts, w0, w1, wmid=None, seed=0, rough=0.9):
    """Tapered brush stroke polygon along a polyline: width w0 -> (wmid) -> w1, slightly ragged."""
    rnd = random.Random(seed)
    L, R = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1)
        w = (w0 + (w1 - w0) * t) if wmid is None else (w0 + (wmid - w0) * (t / .35) if t < .35 else wmid + (w1 - wmid) * ((t - .35) / .65))
        w *= 1 + rnd.uniform(-.08, .08) * rough
        xa, ya = pts[max(0, i - 1)]; xb, yb = pts[min(n - 1, i + 1)]
        dx, dy = xb - xa, yb - ya; l = math.hypot(dx, dy) or 1
        nx, ny = -dy / l, dx / l
        L.append((x + nx * w / 2, y + ny * w / 2)); R.append((x - nx * w / 2, y - ny * w / 2))
    poly = L + R[::-1]
    return "M" + " L".join("%.1f %.1f" % p for p in poly) + "Z"


def sumie(out):
    ink = "#1a1a1a"
    strokes = [
        # (bezier control points, w0, w1, wmid, seed, fill)
        (((352, 222), (344, 280), (336, 330), (318, 420)), 3, 14, 12, 1),       # left ear edge
        (((352, 222), (380, 270), (396, 310), (410, 338)), 2, 10, 9, 2),
        (((468, 240), (490, 300), (494, 340), (510, 440)), 4, 12, 16, 3),       # right ear + back of head
        (((232, 486), (290, 440), (300, 430), (322, 420)), 3, 10, 8, 4),        # brow / snout top
        (((236, 492), (300, 530), (400, 556), (470, 562)), 3, 6, 10, 5),         # jaw
        (((512, 470), (600, 480), (700, 560), (756, 700)), 10, 26, 30, 6),       # back
        (((756, 700), (780, 780), (740, 842), (650, 842)), 26, 6, 22, 7),        # rump
        (((420, 560), (398, 640), (410, 720), (420, 830)), 18, 5, 16, 8),        # chest line
        (((470, 742), (476, 790), (482, 820), (488, 842)), 20, 8, 22, 9),        # foreleg
        (((520, 770), (530, 800), (538, 826), (540, 842)), 16, 6, 16, 10),
    ]
    paths = "".join('<path d="%s"/>' % brush(_bez(*s[0]), s[1], s[2], s[3], seed=s[4]) for s in strokes)
    tail_stroke = brush(_bez((700, 810), (860, 860), (990, 700), (872, 486)), 60, 4, 110, seed=11)
    seal, _ = text_path(SERIF, "狐" if False else "KITSUNE", size=26, x=0, y=0)
    return HDR + """<title id="t">Ink Fox</title><desc id="d">Sumi-e: wet ink wash tail, single-gesture tapered brush strokes, mist, vast negative space and a vermilion seal.</desc>
<defs>
<linearGradient id="wash-g" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2a28"/><stop offset=".55" stop-color="#6b6a64" stop-opacity=".85"/><stop offset="1" stop-color="#b9b5a8" stop-opacity=".3"/></linearGradient>
<linearGradient id="mist-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4eddc" stop-opacity="0"/><stop offset="1" stop-color="#f4eddc"/></linearGradient>
<filter id="bleed" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="2"/><feDisplacementMap in="SourceGraphic" scale="14"/><feGaussianBlur stdDeviation="2.2"/></filter>
<filter id="dry" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".6 .04" numOctaves="2" seed="9" result="n"/><feColorMatrix in="n" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -1.5 1.55" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
</defs>
<rect id="paper" width="1024" height="1024" fill="#f4eddc"/>
<g id="far" opacity=".22" filter="url(#bleed)"><path d="M0 700 C160 640 260 690 380 650 S600 610 700 660 S900 680 1024 620 V760 H0Z" fill="#6b6a64"/></g>
<g id="wash" filter="url(#bleed)"><path d="{tail}" fill="url(#wash-g)"/><path d="{BODY}" fill="#8c8a84" opacity=".13"/><path d="{HEAD}" fill="#8c8a84" opacity=".1"/></g>
<g id="strokes" fill="{ink}" filter="url(#dry)">{paths}</g>
<g id="accents" fill="{ink}"><path d="M318 452 Q340 438 364 450 Q340 458 318 452Z"/><circle cx="238" cy="488" r="9"/><path d="M364 300 L368 262 L386 318Z" opacity=".7"/><path d="M458 300 L468 268 L474 330Z" opacity=".7"/></g>
<rect id="mist" y="780" width="1024" height="244" fill="url(#mist-g)"/>
<g id="seal" transform="rotate(-3 880 830)"><rect x="840" y="780" width="84" height="100" rx="4" fill="#c1272d"/><g fill="#f4eddc"><rect x="852" y="794" width="60" height="8"/><rect x="878" y="794" width="8" height="72"/><rect x="852" y="826" width="60" height="7"/><path d="M856 866 L878 842 L884 848 L864 872Z"/><path d="M908 866 L886 842 L880 848 L900 872Z"/></g></g>
</svg>
""".format(**dict(globals(), ink=ink, paths=paths, tail=tail_stroke,
                  cal="".join('<path d="%s"/>' % brush(_bez((930, 120 + i * 80), (936, 140 + i * 80), (926, 160 + i * 80), (932, 178 + i * 80), 12), 9, 2, 7, seed=20 + i) for i in range(6))))


# ------------------------------------------------------------------------------------------
# HORROR: near-black forest, cold moon, fog, silhouette, red eyes, vignette
# ------------------------------------------------------------------------------------------
def horror(out):
    rnd = random.Random(13)

    def tree(x, h, w, seed):
        r = random.Random(seed)
        d = "M%d 900 L%d %d L%d %d L%d 900Z" % (x - w, x - w * .3, 900 - h, x + w * .3, 900 - h, x + w)
        br = ""
        for i in range(7):
            y = 900 - h * r.uniform(.35, .95); s = r.choice([-1, 1]); L = r.uniform(60, 160)
            br += "M%d %d L%d %d L%d %d Z" % (x, y, x + s * L, y - L * r.uniform(.4, .9), x, y - 10)
        return d + br
    trees = "".join('<path d="%s"/>' % tree(x, h, w, s) for x, h, w, s in [(60, 900, 26, 1), (170, 760, 16, 2), (940, 920, 30, 3), (860, 700, 14, 4), (620, 620, 10, 5)])
    fog = "".join('<rect x="0" y="%d" width="1024" height="%d" fill="url(#fog-g)" opacity="%.2f"/>' % (y, h, o) for y, h, o in [(620, 120, .25), (760, 140, .35), (830, 194, .5)])
    return HDR + """<title id="t">Night Fox</title><desc id="d">Horror: near-black forest, cold moon, layered fog, roughened silhouette revealing only red eyes, vignette.</desc>
<defs>
<radialGradient id="moon-g" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#dfe8e2"/><stop offset=".6" stop-color="#b9c7bf"/><stop offset="1" stop-color="#8fa39a"/></radialGradient>
<radialGradient id="moonglow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#8fa39a" stop-opacity=".45"/><stop offset="1" stop-color="#8fa39a" stop-opacity="0"/></radialGradient>
<linearGradient id="fog-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a5b52" stop-opacity="0"/><stop offset=".5" stop-color="#4a5b52"/><stop offset="1" stop-color="#4a5b52" stop-opacity="0"/></linearGradient>
<radialGradient id="vig" cx=".45" cy=".45" r=".75"><stop offset=".55" stop-color="#050706" stop-opacity="0"/><stop offset="1" stop-color="#050706" stop-opacity=".95"/></radialGradient>
<radialGradient id="eyeglow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff2a1a" stop-opacity=".9"/><stop offset="1" stop-color="#ff2a1a" stop-opacity="0"/></radialGradient>
<clipPath id="canvas"><rect width="1024" height="1024"/></clipPath>
<filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="turbulence" baseFrequency=".05" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="9"/></filter>
</defs>
<rect id="night" width="1024" height="1024" fill="#0b120f"/>
<circle id="moon-halo" cx="470" cy="430" r="470" fill="url(#moonglow)" clip-path="url(#canvas)"/>
<circle id="moon" cx="470" cy="430" r="290" fill="url(#moon-g)"/>
<g id="craters" fill="#8fa39a" opacity=".35"><circle cx="600" cy="300" r="46"/><circle cx="330" cy="620" r="30"/><circle cx="640" cy="560" r="22"/><circle cx="360" cy="260" r="18"/></g>
<g id="far-trees" fill="#16211c" filter="url(#rough)" clip-path="url(#canvas)">{trees}</g>
<path id="ground" d="M0 846 C200 830 420 850 600 842 S900 830 1024 846 V1024 H0Z" fill="#070a09"/>
<g id="fox" fill="#050706" filter="url(#rough)"><path d="{TAIL}"/><path d="{BODY}"/><path d="{LEG2}"/><path d="{LEG}"/><path d="{HEAD}"/></g>
<g id="rim" fill="none" stroke="#8fa39a" stroke-width="3" opacity=".55" filter="url(#rough)"><path d="M468 240 L492 362 C510 392 514 430 512 462 L536 516"/><path d="M530 492 C610 500 650 540 690 580 C750 640 780 720 760 800"/><path d="M872 486 C940 560 962 676 924 752"/></g>
<g id="eyes"><circle cx="340" cy="449" r="40" fill="url(#eyeglow)"/><path d="M318 452 Q338 438 362 446 Q342 460 318 452Z" fill="#ff2a1a"/><circle cx="346" cy="449" r="3" fill="#ffd1c9"/></g>
<g id="fog">{fog}</g>
<rect id="vignette" width="1024" height="1024" fill="url(#vig)"/>
</svg>
""".format(**dict(globals(), trees=trees, fog=fog))


# ------------------------------------------------------------------------------------------
# BAUHAUS: fox rebuilt from circle / square / triangle on a unit grid, primaries, rotated type
# ------------------------------------------------------------------------------------------
def bauhaus(out):
    U = 64  # grid unit; canvas = 16 U
    R, Y, B, K, W = "#d62828", "#f7b500", "#1d4e9f", "#111111", "#f1eadb"
    word, _ = text_path(UNB, "FUCHS", size=86, x=0, y=0, tracking=6)
    word2, _ = text_path(UNB, "1925", size=40, x=0, y=0, tracking=4)
    return HDR + """<title id="t">Bauhaus Fox</title><desc id="d">Bauhaus: fox built only from circles, quarter-circles, triangles and bars on a 64-unit grid in red, yellow, blue and black.</desc>
<!-- grid unit U=64; all coordinates are multiples of U/2 -->
<rect id="ground" width="1024" height="1024" fill="{W}"/>
<g id="composition">
<circle id="sun" cx="{c1}" cy="{c2}" r="{r1}" fill="{Y}"/>
<rect id="bar" x="0" y="{gy}" width="1024" height="{h1}" fill="{K}"/>
<path id="tail" d="M{tx} {gy} A{tr} {tr} 0 0 1 {tx2} {gy} Z" fill="{B}"/>
<path id="tail-tip" d="M{ttx} {gy} A{ttr} {ttr} 0 0 1 {ttx2} {gy} Z" fill="{W}"/>
<path id="body" d="M{bx} {gy} V{by} A{br} {br} 0 0 1 {bx2} {gy} Z" fill="{R}"/>
<rect id="chest" x="{chx}" y="{chy}" width="{chw}" height="{chh}" fill="{W}"/>
<rect id="leg" x="{lx}" y="{ly}" width="{lw}" height="{lh}" fill="{K}"/>
<path id="head" d="M{h0x} {h0y} L{h1x} {h1y} L{h2x} {h2y} Z" fill="{R}"/>
<path id="muzzle" d="M{h0x} {h0y} L{m1x} {m1y} L{h2x} {h2y} Z" fill="{W}"/>
<path id="ear-l" d="M{e1} L{e2} L{e3} Z" fill="{K}"/>
<path id="ear-r" d="M{f1} L{f2} L{f3} Z" fill="{K}"/>
<circle id="eye" cx="{ex}" cy="{ey}" r="{er}" fill="{K}"/>
<circle id="nose" cx="{h0x}" cy="{h0y}" r="14" fill="{K}"/>
<rect id="rule" x="{rx}" y="96" width="16" height="560" fill="{B}"/>
<g id="type" fill="{K}"><path d="{word}" transform="translate(944 640) rotate(-90)"/><path d="{word2}" transform="translate(96 976)"/></g>
</g>
</svg>
""".format(**dict(
        R=R, Y=Y, B=B, K=K, W=W, word=word, word2=word2,
        c1=12 * U, c2=4 * U, r1=2.5 * U, gy=13 * U + 20, h1=1024 - (13 * U + 20),
        tx=10 * U, tx2=15.5 * U, tr=2.75 * U, ttx=13.5 * U, ttx2=15.5 * U, ttr=1 * U,
        bx=6.5 * U, by=13 * U + 20 - 5 * U, br=5 * U, bx2=11.5 * U + 0,
        chx=6.5 * U, chy=9 * U, chw=1 * U, chh=4 * U + 20,
        lx=7.5 * U, ly=11 * U, lw=U, lh=2 * U + 20,
        h0x=3.5 * U, h0y=7.5 * U, h1x=8 * U, h1y=4.5 * U, h2x=8 * U, h2y=9 * U, m1x=6 * U, m1y=8.3 * U,
        e1="%d %d" % (5.5 * U, 5.5 * U + 12), e2="%d %d" % (6 * U, 2.5 * U), e3="%d %d" % (7 * U, 5 * U - 2),
        f1="%d %d" % (7 * U, 5 * U), f2="%d %d" % (8.5 * U, 2.5 * U), f3="%d %d" % (8 * U, 5.5 * U),
        ex=6 * U, ey=6.5 * U, er=U / 4, rx=14.5 * U - 8))


# ------------------------------------------------------------------------------------------
# UKIYO-E BUT DARKER (modifier demo): night palette, moon, lantern glow; structure unchanged
# ------------------------------------------------------------------------------------------
def ukiyo_night(out):
    from make_fox_set import ukiyo
    s = ukiyo()
    swaps = [('<stop offset="0" stop-color="#9fc0c4"/><stop offset="1" stop-color="#efe3c4"/>',
              '<stop offset="0" stop-color="#0f1a33"/><stop offset="1" stop-color="#3b4a6b"/>'),
             ('<circle id="sun" cx="760" cy="290" r="116" fill="#c9412c"/>',
              '<circle id="moon" cx="760" cy="290" r="116" fill="#f1e4b8"/>'),
             ('<g id="kasumi" fill="#f5ecd2">', '<g id="kasumi" fill="#4c5b7a" opacity=".85">'),
             ('fill="#e6dab9"/></g>', 'fill="#2c3a5a"/></g>'),
             ('<rect id="paper" width="1024" height="1024" fill="#efe3c4"/>', '<rect id="paper" width="1024" height="1024" fill="#e4d5b0"/>'),
             ('"#2b4a6b"', '"#16284a"'), ('stroke="#e9dfc4" stroke-width="3"', 'stroke="#9fb0c8" stroke-width="3"'),
             ('#e9712f', '#c2542a'), ('#d8642c', '#a6431f'), ('#f5ecd2', '#e8dcbc'),
             ('<title id="t">Fox at Dusk</title>', '<title id="t">Fox at Night</title>'),
             ('Ukiyo-e style:', 'Ukiyo-e, darker modifier:')]
    for a, b in swaps:
        s = s.replace(a, b)
    return s


# ------------------------------------------------------------------------------------------
# ART NOUVEAU: arched double frame, halo, whiplash tendrils, lilies, ornamental title
# ------------------------------------------------------------------------------------------
def nouveau(out):
    ink = "#2d2a24"
    rays = "".join('<path d="M512 430 L%.1f %.1f" />' % (512 + 330 * math.cos(math.radians(a)), 430 + 330 * math.sin(math.radians(a))) for a in range(180, 361, 6))
    ring = "".join('<circle cx="%.1f" cy="%.1f" r="7"/>' % (512 + 352 * math.cos(math.radians(a)), 430 + 352 * math.sin(math.radians(a))) for a in range(180, 361, 10))
    title, _ = text_path(SERIF, "Vulpes", size=110, x=512, y=968, anchor="middle", tracking=6)
    return HDR + """<title id="t">Nouveau Fox</title><desc id="d">Art Nouveau: arched double frame, sun-ray halo, whiplash tendrils and lilies growing into the border, muted jewel tones, dark contours.</desc>
<defs>
<symbol id="lily" viewBox="-40 -80 80 90" overflow="visible"><g stroke="{ink}" stroke-width="3" stroke-linejoin="round"><path d="M0 0 C-30 -20 -34 -56 -8 -78 C-10 -50 -6 -26 0 0Z" fill="#e8c9b8"/><path d="M0 0 C30 -20 34 -56 8 -78 C10 -50 6 -26 0 0Z" fill="#e8c9b8"/><path d="M0 0 C-10 -30 -6 -60 0 -80 C6 -60 10 -30 0 0Z" fill="#f3e2d4"/></g></symbol>
<pattern id="scale" width="28" height="18" patternUnits="userSpaceOnUse"><rect width="28" height="18" fill="#7f9c7e"/><path d="M0 18a14 14 0 0 1 28 0" fill="none" stroke="#5f7d62" stroke-width="2.5"/></pattern>
</defs>
<g id="art" stroke-linecap="round">
<rect id="ground" width="1024" height="1024" fill="#efe2c0"/>
<g id="frame" stroke="{ink}" stroke-width="6">
<path d="M70 1000 V472 A442 442 0 0 1 954 472 V1000 Z" fill="#d9c49a"/>
<path d="M100 880 V472 A412 412 0 0 1 924 472 V880 Z" fill="#c9d3b0" stroke-width="4"/></g>
<g id="halo"><circle cx="512" cy="430" r="340" fill="#e7c77d" stroke="{ink}" stroke-width="4"/><g stroke="#c9a24f" stroke-width="5">{rays}</g><g fill="#b5543c" stroke="{ink}" stroke-width="2">{ring}</g><circle cx="512" cy="430" r="200" fill="#f0dca0" stroke="{ink}" stroke-width="3"/></g>
<path id="hill" d="M100 880 V800 C300 760 420 820 560 820 S820 780 924 800 V880Z" fill="url(#scale)" stroke="{ink}" stroke-width="4"/>
<g id="tendrils" fill="none" stroke="{ink}" stroke-linecap="round">
<path d="M100 880 C150 760 60 640 150 540 C220 460 160 380 230 330 C270 300 300 320 290 350 C282 372 256 366 262 346" stroke-width="10"/>
<path d="M100 880 C150 760 60 640 150 540 C220 460 160 380 230 330 C270 300 300 320 290 350 C282 372 256 366 262 346" stroke="#7f9c7e" stroke-width="5"/>
<path d="M924 880 C880 780 960 660 880 560 C820 480 880 400 820 350 C786 322 752 338 762 364 C770 384 796 378 790 358" stroke-width="10"/>
<path d="M924 880 C880 780 960 660 880 560 C820 480 880 400 820 350 C786 322 752 338 762 364 C770 384 796 378 790 358" stroke="#7f9c7e" stroke-width="5"/>
<path d="M150 540 C110 520 96 480 120 456" stroke-width="6"/><path d="M880 560 C920 540 934 500 910 474" stroke-width="6"/></g>
<g id="leaves" fill="#7f9c7e" stroke="{ink}" stroke-width="3"><path d="M150 620 C110 600 96 560 104 540 C130 556 150 590 150 620Z"/><path d="M880 640 C920 620 934 580 926 560 C900 576 880 610 880 640Z"/><path d="M200 460 C230 430 270 430 290 440 C266 462 230 470 200 460Z"/></g>
<g id="lilies"><use href="#lily" x="124" y="470" width="80" height="90" transform="rotate(-20 164 520)"/><use href="#lily" x="820" y="490" width="80" height="90" transform="rotate(18 860 540)"/><use href="#lily" x="60" y="720" width="70" height="80" transform="rotate(-8 95 760)"/></g>
<g id="fox" stroke="{ink}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
<path d="{TAIL}" fill="#b5543c"/><path d="{TAIL_TIP}" fill="#f3e2d4"/><path d="{BODY}" fill="#c96a3f"/><path d="{HAUNCH}" fill="#b5543c"/>
<path d="{LEG2}" fill="#4a3a30"/><path d="{CHEST}" fill="#f3e2d4"/><path d="{LEG}" fill="#3a2e26"/>
<path d="{HEAD}" fill="#c96a3f"/><path d="{CHEEK}" fill="#f3e2d4"/><path d="{MUZZLE}" fill="#f3e2d4"/><path d="{EAR_L}" fill="#4a3a30"/><path d="{EAR_R}" fill="#4a3a30"/></g>
<g id="fur" fill="none" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"><path d="M560 540 C600 560 620 600 610 640"/><path d="M640 600 C680 630 690 670 676 710"/><path d="M800 540 C840 600 850 660 830 720"/><path d="M860 600 C880 650 880 700 860 740"/></g>
<g id="face"><path d="{EYE}" fill="{ink}"/><circle cx="236" cy="488" r="10" fill="{ink}"/></g>
<g id="title-panel"><path d="M70 1000 V900 H954 V1000Z" fill="#2f4a45" stroke="{ink}" stroke-width="6"/><path d="{title}" fill="#e7c77d"/><path d="M150 950 C200 930 240 960 290 944 M734 944 C784 960 824 930 874 950" fill="none" stroke="#e7c77d" stroke-width="4" stroke-linecap="round"/></g>
<rect id="outer" x="24" y="24" width="976" height="976" fill="none" stroke="{ink}" stroke-width="8"/>
</g>
</svg>
""".format(**dict(globals(), ink=ink, rays=rays, ring=ring, title=title))


# ------------------------------------------------------------------------------------------
# LOW-POLY LANDSCAPE (non-fox): procedural mountains
# ------------------------------------------------------------------------------------------
def lowpoly_landscape(out):
    import numpy as np
    from scipy.spatial import Delaunay
    rnd = random.Random(21)
    W, H = 1600, 900

    def ridge(x, base, amp, f, ph):
        return base - amp * (0.6 * abs(math.sin(x * f + ph)) + 0.4 * abs(math.sin(x * f * 2.3 + ph * 1.7)))
    layers = [(560, 300, .0042, .3), (660, 240, .0061, 1.9), (760, 160, .0083, 4.2)]
    pts = [(x, y) for x in range(0, W + 1, 100) for y in (0, H)] + [(0, y) for y in range(0, H, 90)] + [(W, y) for y in range(0, H, 90)]
    for x in range(0, W + 1, 30):
        for (b, a, f, ph) in layers:
            pts.append((min(W, max(0, x + rnd.uniform(-8, 8))), ridge(x, b, a, f, ph)))
    for _ in range(900):
        pts.append((rnd.uniform(0, W), rnd.uniform(0, H)))
    pts = np.array(pts)
    tri = Delaunay(pts)
    sky_top, sky_bot = np.array([0x1b, 0x1f, 0x4b]), np.array([0xff, 0x9a, 0x76])
    cols = [np.array([0x6b, 0x4f, 0x8f]), np.array([0x45, 0x3a, 0x74]), np.array([0x24, 0x22, 0x4f])]
    out_p = []
    for s in tri.simplices:
        p = pts[s]; c = p.mean(0)
        layer = None
        for i, (b, a, f, ph) in enumerate(layers):
            if c[1] > ridge(c[0], b, a, f, ph):
                layer = i
        if layer is None:
            t = c[1] / 600
            col = sky_top * (1 - t) + sky_bot * t
            d = math.hypot(c[0] - 1050, c[1] - 430)
            if d < 130:
                col = np.array([0xff, 0xe0, 0x9e])
            elif d < 260:
                col = col * .6 + np.array([0xff, 0xc0, 0x80]) * .4
            k = 1 + rnd.uniform(-.05, .05)
        else:
            col = cols[layer].astype(float)
            v1, v2 = p[1] - p[0], p[2] - p[0]
            n = np.array([v1[1] * 0 - 0, 0, 0])
            slope = (p[:, 1].max() - p[:, 1].min()) / (p[:, 0].max() - p[:, 0].min() + 1)
            side = 1 if (p[:, 0][p[:, 1].argmin()] < c[0]) else -1
            k = 1 + side * .12 * min(1, slope) + rnd.uniform(-.06, .06)
            if layer == 0 and c[1] < ridge(c[0], *layers[0]) + 40:
                col = col * .5 + np.array([0xf7, 0xd6, 0xe0]) * .5
        rgb = np.clip(col * k, 0, 255).astype(int)
        hx = "#%02x%02x%02x" % tuple(rgb)
        out_p.append('<polygon points="%s" fill="%s" stroke="%s"/>' % (" ".join("%.1f,%.1f" % tuple(v) for v in p), hx, hx))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="t d">'
            '<title id="t">Low Poly Dusk</title><desc id="d">Low poly landscape: three triangulated mountain ranges under a dusk sky with a faceted sun.</desc>'
            '<g id="mesh" stroke-width=".8" stroke-linejoin="round">%s</g></svg>\n' % "".join(out_p))


# ------------------------------------------------------------------------------------------
# ISOMETRIC (non-fox): tiny island town
# ------------------------------------------------------------------------------------------
def isometric(out):
    cx, cy, S = 800, 416, 36  # screen origin and cell size

    def iso(x, y, z):
        return (cx + (x - y) * S * 0.866, cy + (x + y) * S * 0.5 - z * S)

    def box(x, y, w, d, h, top, left, right, z=0):
        P = lambda a, b, c: "%.1f,%.1f" % iso(a, b, c)
        t = '<polygon points="%s %s %s %s" fill="%s"/>' % (P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h), top)
        l = '<polygon points="%s %s %s %s" fill="%s"/>' % (P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x, y + d, z + h), left)
        r = '<polygon points="%s %s %s %s" fill="%s"/>' % (P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x + w, y, z + h), right)
        return t + l + r

    def roof(x, y, w, d, z, h, c1, c2):
        P = lambda a, b, c: "%.1f,%.1f" % iso(a, b, c)
        return ('<polygon points="%s %s %s %s" fill="%s"/>' % (P(x, y, z), P(x + w, y, z), P(x + w, y + d / 2, z + h), P(x, y + d / 2, z + h), c2) +
                '<polygon points="%s %s %s %s" fill="%s"/>' % (P(x, y + d / 2, z + h), P(x + w, y + d / 2, z + h), P(x + w, y + d, z), P(x, y + d, z), c1) +
                '<polygon points="%s %s %s" fill="%s"/>' % (P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d / 2, z + h), c2))

    def windows(x, y, w, d, z0, h, col):
        s = ""
        for zz in range(int(z0) + 1, int(z0 + h), 1):
            for i in range(int(w)):
                a, b = iso(x + i + .3, y + d, zz - .1), iso(x + i + .7, y + d, zz - .1)
                c, e = iso(x + i + .7, y + d, zz + .45), iso(x + i + .3, y + d, zz + .45)
                s += '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>' % (a + b + c + e + (col,))
        return s

    def tree(x, y):
        tx, ty = iso(x, y, 0)
        return ('<g transform="translate(%.1f %.1f)"><rect x="-4" y="-26" width="8" height="26" fill="#6b4b33"/>'
                '<circle cy="-48" r="26" fill="#3f8f5a"/><circle cx="-8" cy="-56" r="14" fill="#62b27a"/></g>' % (tx, ty))

    parts = []
    parts.append(box(-7, -7, 14, 14, 1.2, "#8bd17c", "#5f9e56", "#4c8446", z=-2.2))       # island top
    parts.append(box(-7, -7, 14, 14, 2.2, "#c9a26b", "#a57d4d", "#8a663c", z=-4.4))      # cliff
    parts.append(box(-5.5, 1.5, 11, 2, .05, "#d8d2c4", "#bdb5a3", "#aaa190", z=-1))       # road
    parts.append(box(1.5, -5.5, 2, 7, .05, "#d8d2c4", "#bdb5a3", "#aaa190", z=-1))
    parts.append(box(-5, -5, 4, 4, 5, "#f2f0ea", "#d9d4c9", "#bdb6a8", z=-1) + windows(-5, -5, 4, 4, -1, 5, "#4a90c2"))
    parts.append(box(-5.4, -5.4, 4.8, 4.8, .5, "#e76f51", "#c65a3f", "#a84a33", z=4))
    parts.append(box(4, -5, 3, 3, 2, "#f4d58d", "#d9b56a", "#bf9a52", z=-1) + windows(4, -5, 3, 3, -1, 2, "#6b4b33"))
    parts.append(roof(4, -5, 3, 3, 1, 1.4, "#e76f51", "#c65a3f"))
    parts.append(box(-5, 4, 3, 2.5, 2, "#a8dadc", "#86b9bc", "#6e9fa2", z=-1) + windows(-5, 4, 3, 2.5, -1, 2, "#1d3557"))
    parts.append(roof(-5, 4, 3, 2.5, 1, 1.2, "#457b9d", "#35627e"))
    parts.append(box(4, 4, 2.5, 2.5, 3.5, "#ffb4a2", "#e5989b", "#c9797d", z=-1) + windows(4, 4, 2.5, 2.5, -1, 3.5, "#6d597a"))
    parts.append(box(3.8, 3.8, 2.9, 2.9, .4, "#6d597a", "#574766", "#433652", z=2.5))
    trees = "".join(tree(x, y) for x, y in [(-1, -6), (0.2, -3), (6.2, -1), (-6.3, 0.5), (-0.5, 5.8), (6.3, 1.2), (-2.4, -1.8)])
    clouds = ('<g id="clouds" fill="#fff" opacity=".9"><ellipse cx="300" cy="170" rx="120" ry="34"/><ellipse cx="350" cy="148" rx="70" ry="40"/>'
              '<ellipse cx="1280" cy="220" rx="140" ry="36"/><ellipse cx="1240" cy="196" rx="70" ry="40"/></g>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="t d">'
            '<title id="t">Isometric Island</title><desc id="d">Isometric: 30-degree axonometric island town, three-tone faces from a single top-left light, no perspective.</desc>'
            '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bfe3f2"/><stop offset="1" stop-color="#f6f1e7"/></linearGradient></defs>'
            '<rect id="sky-bg" width="1600" height="900" fill="url(#sky)"/>' + clouds +
            '<ellipse id="shadow" cx="800" cy="790" rx="470" ry="66" fill="#1d3557" opacity=".12"/>'
            '<g id="island">' + "".join(parts) + '</g><g id="trees">' + trees + '</g></svg>\n')


# ------------------------------------------------------------------------------------------
PIXEL_SHIP = r"""; Pixel spaceship (mirrored). Build:
;   python3 scripts/pixel_grid.py examples/src/ship-pixel.txt --mirror -o OUT --outline "#0b0b1a" --pad 4 --bg "#141433"
@w=#f2f2f2
@l=#9bd0ff
@b=#3a7bd5
@d=#1f3f8f
@r=#ff4d6d
@o=#ffb703
@y=#ffe66d
@g=#6c757d
@k=#2b2d42
...............w
..............ww
..............ll
.............lll
.............lbl
............wlbl
............wlbl
...........wwbbd
...........wbbbd
...........wbbbd
..........wwbbbd
.....r....wbbbdd
.....r...wwbbbdd
....rr...wbbbddw
....rr..wwbbddww
...rrr.wwgbbdwww
...rrrwwggbddwwg
..rrrrwggkbdwwgg
..rrrwwgkkbwwggg
.rrrrwggkkwwgggg
.rrrwwggkkggggkk
rrrrwgggkkggkkk.
rrr..ggkk..kk...
rr....oo....o...
......yo....y...
......y.........
"""


NAMES = {
    "fox-low-poly": low_poly, "fox-risograph": riso, "fox-comic-book": comic, "fox-sticker": sticker,
    "fox-sumi-e": sumie, "fox-horror": horror, "fox-bauhaus": bauhaus, "fox-ukiyo-e-darker": ukiyo_night,
    "fox-art-nouveau": nouveau, "landscape-low-poly": lowpoly_landscape, "island-isometric": isometric,
}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "."); out.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[2:] or list(NAMES) + ["ship-pixel-art"]
    for name in wanted:
        if name == "ship-pixel-art":
            src = HERE / "ship-pixel.txt"
            src.write_text(PIXEL_SHIP, encoding="utf-8")
            subprocess.run([sys.executable, str(SKILL / "scripts/pixel_grid.py"), str(src), "--mirror", "-o", str(out / "ship-pixel-art.svg"),
                            "--outline", "#0b0b1a", "--pad", "4", "--bg", "#141433", "--title", "Pixel starship"], check=True)
            continue
        (out / (name + ".svg")).write_text(NAMES[name](out), encoding="utf-8")
        print("wrote", out / (name + ".svg"))
