#!/usr/bin/env python3
"""Generates the multi-style fox example set (same scene spec, different visual languages).

Scene spec (frozen, shared by every variant)
  subject : red fox, seated, side view facing left, big brush tail curling up on the right
  canvas  : 0 0 1024 1024
  anchors : head centre ~(370, 400), muzzle tip (232, 486), ground line y=840,
            subject bbox ~ x232..962, y222..844

Usage: python3 make_fox_set.py OUTDIR      (writes fox.svg + fox-<style-id>.svg, except pixel art
       which is built with scripts/pixel_grid.py from the ASCII in make_pixel_fox.py)
"""
import sys
from pathlib import Path

# ---- shared geometry (the "scene spec" as path data) ------------------------------------
TAIL = "M700 800 C770 846 880 838 924 752 C962 676 940 560 872 486 C866 566 842 628 790 664 C758 686 730 694 700 694 Z"
TAIL_TIP = "M872 486 C940 560 962 676 926 742 C922 680 900 600 850 540 C858 522 866 504 872 486Z"
BODY = "M430 500 C520 470 610 500 690 580 C750 640 780 720 760 800 C752 828 736 840 700 840 L470 840 C450 840 446 822 452 806 L436 700 C422 640 404 590 410 540 Z"
HAUNCH = "M600 640 C680 640 750 700 752 780 C752 816 736 840 700 840 L580 840 C560 800 556 700 600 640Z"
CHEST = "M410 545 C440 562 472 570 490 600 C470 650 458 700 458 770 L426 770 C412 700 396 610 410 545Z"
LEG = "M424 740 L456 730 L482 730 L490 822 C494 836 486 844 472 844 L404 844 C388 844 388 826 404 820 L418 790Z"
LEG2 = "M500 760 L540 752 L548 826 C550 838 544 844 532 844 L484 844 C486 830 494 822 498 800Z"
HEAD = "M232 486 C262 462 292 438 318 420 L334 352 L352 222 L410 338 L468 240 L492 362 C510 392 514 430 512 462 L536 516 L488 528 L468 562 C430 552 380 552 340 540 C312 534 282 520 256 512 C242 504 234 496 232 486Z"
MUZZLE = "M232 486 C262 462 292 438 318 430 C340 440 372 470 420 492 C452 508 480 516 488 528 L468 562 C430 552 380 552 340 540 C312 534 282 520 256 512 C242 504 234 496 232 486Z"
EAR_L = "M352 300 L358 248 L392 322Z"
EAR_R = "M452 306 L468 262 L478 342Z"
EYE = "M318 452 Q338 436 362 448 Q340 462 318 452Z"
NOSE = ("236", "488", "10")   # cx, cy, r
CHEEK = "M490 520 L536 516 L510 548 L468 562Z"

HDR = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-labelledby="t d">\n'


def nose(fill):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (NOSE + (fill,))


# ---- 1. flat base ------------------------------------------------------------------------
def base():
    return HDR + """<title id="t">Red fox</title><desc id="d">Neutral flat illustration of a seated red fox; the layout reference for the style set.</desc>
<rect width="1024" height="1024" fill="#f4efe6"/>
<g id="ground"><ellipse cx="640" cy="846" rx="380" ry="16" fill="#e5dccb"/></g>
<g id="tail"><path d="%(TAIL)s" fill="#d9642b"/><path d="%(TAIL_TIP)s" fill="#fbf3e4"/></g>
<g id="body"><path d="%(BODY)s" fill="#e9712f"/><path d="%(HAUNCH)s" fill="#d9642b"/><path d="%(LEG2)s" fill="#4a2a1f"/><path d="%(CHEST)s" fill="#fbf3e4"/><path d="%(LEG)s" fill="#3a2019"/></g>
<g id="head"><path d="%(HEAD)s" fill="#e9712f"/><path d="%(CHEEK)s" fill="#fbf3e4"/><path d="%(MUZZLE)s" fill="#fbf3e4"/><path d="%(EAR_L)s" fill="#3a2019"/><path d="%(EAR_R)s" fill="#3a2019"/><path d="%(EYE)s" fill="#2b1a14"/>%(NOSE)s</g>
</svg>
""" % dict(globals(), NOSE=nose("#2b1a14"))


# ---- 2. ukiyo-e --------------------------------------------------------------------------
def ukiyo():
    ink = "#1c1a1a"
    hatch = "".join('<path d="M%d %dl%d %d"/>' % (x, y, dx, dy) for x, y, dx, dy in [
        (800, 560, 34, -30), (830, 600, 36, -34), (790, 620, 40, -30), (830, 660, 40, -30), (800, 700, 38, -24),
        (860, 720, 30, -30), (760, 740, 34, -20), (840, 770, 30, -22), (890, 690, 22, -30), (880, 610, 26, -30)])
    fur = "".join('<path d="M%d %dl%d %d"/>' % (x, y, dx, dy) for x, y, dx, dy in [
        (560, 560, 30, 10), (600, 590, 30, 12), (650, 640, 26, 18), (690, 700, 20, 22), (620, 700, 22, 20), (660, 770, 14, 20)])
    grass = "".join('<path d="M%d 840q4 -30 %d -46M%d 840q2 -22 %d -30"/>' % (x, d, x + 10, d // 2) for x, d in [
        (140, -6), (300, 8), (560, -8), (620, 8), (980, -6), (90, 6)])
    return HDR + """<title id="t">Fox at Dusk</title><desc id="d">Ukiyo-e style: flat colour blocks, black key-block outlines, bokashi sky, kasumi mist, seigaiha waves, red cartouche.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fc0c4"/><stop offset="1" stop-color="#efe3c4"/></linearGradient>
<pattern id="seigaiha" width="80" height="40" patternUnits="userSpaceOnUse">
<rect width="80" height="40" fill="#2b4a6b"/>
<g fill="none" stroke="#e9dfc4" stroke-width="3">
<path id="wv" d="M0 40a40 40 0 0 1 80 0M14 40a26 26 0 0 1 52 0M28 40a12 12 0 0 1 24 0"/>
<use href="#wv" x="-40" y="-20"/><use href="#wv" x="40" y="-20"/>
</g></pattern>
</defs>
<rect id="paper" width="1024" height="1024" fill="#efe3c4"/>
<rect id="sky-band" width="1024" height="640" fill="url(#sky)"/>
<circle id="sun" cx="760" cy="290" r="116" fill="#c9412c"/>
<g id="kasumi" fill="#f5ecd2"><path d="M0 610C120 580 230 640 350 610S560 580 640 620 860 640 1024 600V690C900 720 780 670 660 700S420 730 300 690 90 700 0 680Z"/><path d="M420 470C520 450 600 490 700 470S860 450 1024 480V520C900 540 800 510 700 530S520 520 420 510Z" fill="#e6dab9"/></g>
<g id="cartouche"><rect x="70" y="70" width="86" height="270" fill="#c9412c" stroke="%(ink)s" stroke-width="5"/><rect x="82" y="82" width="62" height="246" fill="#f5ecd2"/>
<g fill="none" stroke="%(ink)s" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><path d="M96 118h34M113 104v44M96 150q17 -14 34 0"/><path d="M96 200h34M96 232h34M113 190v70M98 260l30 26"/></g>
<rect x="94" y="300" width="26" height="20" fill="#c9412c"/></g>
<g id="water"><rect y="840" width="1024" height="184" fill="url(#seigaiha)"/><rect y="837" width="1024" height="6" fill="%(ink)s"/></g>
<g id="grass" fill="none" stroke="%(ink)s" stroke-width="5" stroke-linecap="round">%(grass)s</g>
<g id="fox" stroke="%(ink)s" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
<g id="tail"><path d="%(TAIL)s" fill="#d8642c"/><path d="%(TAIL_TIP)s" fill="#f5ecd2"/><g fill="none" stroke-width="4">%(hatch)s</g></g>
<g id="body"><path d="%(BODY)s" fill="#e9712f"/><path d="%(HAUNCH)s" fill="#d8642c"/><path d="%(LEG2)s" fill="#3a2019"/><path d="%(CHEST)s" fill="#f5ecd2"/><path d="%(LEG)s" fill="#3a2019"/><g fill="none" stroke-width="4">%(fur)s</g></g>
<g id="head"><path d="%(HEAD)s" fill="#e9712f"/><path d="%(CHEEK)s" fill="#f5ecd2"/><path d="%(MUZZLE)s" fill="#f5ecd2"/><path d="%(EAR_L)s" fill="#3a2019"/><path d="%(EAR_R)s" fill="#3a2019"/><path d="%(EYE)s" fill="%(ink)s"/>%(NOSE)s</g>
</g>
</svg>
""" % dict(globals(), ink=ink, hatch=hatch, fur=fur, grass=grass, NOSE=nose(ink))


# ---- 3. cyberpunk neon -------------------------------------------------------------------
def cyber():
    import random
    rnd = random.Random(7)
    bld, x = [], 0
    while x < 1024:
        w = rnd.choice([70, 90, 110, 60]); h = rnd.randint(140, 380)
        w = min(w, 1024 - x)
        bld.append((x, 840 - h, w, h)); x += w + rnd.choice([0, 6, 10])
    towers = "".join('<rect x="%d" y="%d" width="%d" height="%d"/>' % b for b in bld)
    wins = []
    for (bx, by, bw, bh) in bld:
        for wy in range(by + 18, 820, 34):
            for wx in range(bx + 10, bx + bw - 12, 18):
                if rnd.random() < 0.22:
                    wins.append('<rect x="%d" y="%d" width="8" height="12"/>' % (wx, wy))
    wins = "".join(wins[:70])
    grid_h = "".join('<path d="M0 %d H1024"/>' % y for y in (860, 885, 920, 965, 1024))
    grid_v = "".join('<path d="M%d 850 L%d 1024"/>' % (512 + (i - 6) * 40, 512 + (i - 6) * 210) for i in range(13))
    return HDR + """<title id="t">Neon Fox</title><desc id="d">Cyberpunk neon: dark base, glowing outline on the hero silhouette, magenta skyline haze, perspective grid floor, lit windows.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#07040f"/><stop offset=".6" stop-color="#1c0a3a"/><stop offset="1" stop-color="#7a1462"/></linearGradient>
<radialGradient id="moon" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff4fd8" stop-opacity=".9"/><stop offset="1" stop-color="#ff4fd8" stop-opacity="0"/></radialGradient>
<clipPath id="floor-clip"><rect y="840" width="1024" height="184"/></clipPath>
<filter id="glow" x="-20%%" y="-20%%" width="140%%" height="140%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect id="sky-bg" width="1024" height="1024" fill="url(#sky)"/>
<circle id="halo" cx="760" cy="330" r="240" fill="url(#moon)"/>
<g id="skyline" fill="#0d0820" opacity=".95">%(towers)s</g>
<g id="windows" fill="#25e6ff" opacity=".75">%(wins)s</g>
<g id="floor"><rect y="840" width="1024" height="184" fill="#0a0518"/>
<g fill="none" stroke="#ff2fb8" stroke-width="2" opacity=".75" clip-path="url(#floor-clip)">%(grid_h)s%(grid_v)s</g>
<path d="M0 840H1024" stroke="#25e6ff" stroke-width="4" opacity=".9"/></g>
<g id="signs" fill="none" stroke-width="5" stroke-linecap="round" filter="url(#glow)"><path d="M96 200v130h60" stroke="#ff2fb8"/><path d="M900 160h70M900 190h44" stroke="#25e6ff"/></g>
<g id="fox-fill" fill="#150a2b"><path d="%(TAIL)s"/><path d="%(BODY)s"/><path d="%(LEG2)s"/><path d="%(LEG)s"/><path d="%(HEAD)s"/></g>
<g id="fox-neon" fill="none" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)">
<path d="%(TAIL)s" stroke="#ff2fb8" stroke-width="6"/><path d="%(TAIL_TIP)s" stroke="#25e6ff" stroke-width="5"/>
<path d="%(BODY)s" stroke="#ff7a2f" stroke-width="6"/><path d="%(HAUNCH)s" stroke="#ff2fb8" stroke-width="3" opacity=".7"/>
<path d="%(HEAD)s" stroke="#ff7a2f" stroke-width="6"/><path d="%(MUZZLE)s" stroke="#25e6ff" stroke-width="4"/>
<path d="%(CHEST)s" stroke="#25e6ff" stroke-width="3" opacity=".8"/><path d="%(LEG)s" stroke="#ff7a2f" stroke-width="4"/>
<path d="%(EAR_L)s" stroke="#ff2fb8" stroke-width="4"/><path d="%(EAR_R)s" stroke="#ff2fb8" stroke-width="4"/></g>
<g id="visor"><path d="%(EYE)s" fill="#25e6ff" filter="url(#glow)"/><circle cx="236" cy="488" r="9" fill="#ff2fb8" filter="url(#glow)"/></g>
</svg>
""" % dict(globals(), towers=towers, wins=wins, grid_h=grid_h, grid_v=grid_v)


# ---- 4. paper cut-out --------------------------------------------------------------------
def paper():
    return HDR + """<title id="t">Paper Fox</title><desc id="d">Paper cut-out: stacked flat sheets, no outlines, soft cast shadow under every layer, a little fibre texture.</desc>
<defs>
<filter id="sh" x="-10%%" y="-10%%" width="125%%" height="125%%"><feDropShadow dx="5" dy="9" stdDeviation="6" flood-color="#3b2a1a" flood-opacity=".38"/></filter>
<filter id="shs" x="-10%%" y="-10%%" width="125%%" height="125%%"><feDropShadow dx="3" dy="4" stdDeviation="3" flood-color="#3b2a1a" flood-opacity=".35"/></filter>
<linearGradient id="dusk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7d9a0"/><stop offset="1" stop-color="#f3efe2"/></linearGradient>
</defs>
<rect id="sheet" width="1024" height="1024" fill="url(#dusk)"/>
<g id="sun" filter="url(#shs)"><circle cx="780" cy="270" r="120" fill="#f4a259"/><circle cx="780" cy="270" r="78" fill="#f7c873"/></g>
<g id="clouds" fill="#fffaf0" filter="url(#shs)"><path d="M80 250h190a34 34 0 0 0 -22 -60a50 50 0 0 0 -92 -10a40 40 0 0 0 -76 70z"/><path d="M420 150h140a26 26 0 0 0 -16 -46a38 38 0 0 0 -70 -8a30 30 0 0 0 -54 54z"/></g>
<g id="hills"><path d="M0 610C160 540 300 580 440 640S760 700 1024 600V1024H0Z" fill="#7fb59a" filter="url(#sh)"/><path d="M0 730C180 690 330 720 500 770S820 800 1024 730V1024H0Z" fill="#4e8f7a" filter="url(#sh)"/><path d="M0 840C220 810 420 830 600 850S880 850 1024 830V1024H0Z" fill="#2f6b62" filter="url(#sh)"/></g>
<g id="trees" fill="#2f6b62" filter="url(#shs)"><path d="M90 640l46 -120l46 120z"/><path d="M104 590l32 -90l32 90z" fill="#3f8272"/><path d="M930 660l40 -104l40 104z"/></g>
<g id="fox" filter="url(#sh)">
<path d="%(TAIL)s" fill="#e0662c"/><path d="%(TAIL_TIP)s" fill="#fff4e0"/>
<path d="%(BODY)s" fill="#f07a35"/><path d="%(HAUNCH)s" fill="#e0662c" filter="url(#shs)"/>
<path d="%(LEG2)s" fill="#5a3324"/><path d="%(CHEST)s" fill="#fff4e0" filter="url(#shs)"/><path d="%(LEG)s" fill="#3a2019"/>
<path d="%(HEAD)s" fill="#f07a35"/><path d="%(CHEEK)s" fill="#fff4e0"/><path d="%(MUZZLE)s" fill="#fff4e0" filter="url(#shs)"/>
<path d="%(EAR_L)s" fill="#3a2019"/><path d="%(EAR_R)s" fill="#3a2019"/><path d="%(EYE)s" fill="#2b1a14"/>%(NOSE)s</g>
</svg>
""" % dict(globals(), NOSE=nose("#2b1a14"))


# ---- 5. blueprint ------------------------------------------------------------------------
def blueprint():
    ln = "#e8f1ff"
    return HDR + """<title id="t">Fox Drawing Sheet</title><desc id="d">Blueprint: white linework on cyan-blue grid paper, construction circles, centre lines, dimensions and a title block.</desc>
<defs>
<pattern id="grid-s" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="#5f9be0" stroke-width="1" opacity=".35"/></pattern>
<pattern id="grid-l" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="#7fb4ee" stroke-width="1.5" opacity=".5"/></pattern>
<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0V10" stroke="%(ln)s" stroke-width="1.2" opacity=".55"/></pattern>
<marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 1L10 5L0 9z" fill="%(ln)s"/></marker>
</defs>
<rect id="paper" width="1024" height="1024" fill="#0f3a6d"/>
<rect width="1024" height="1024" fill="url(#grid-s)"/><rect width="1024" height="1024" fill="url(#grid-l)"/>
<rect id="border" x="30" y="30" width="964" height="964" fill="none" stroke="%(ln)s" stroke-width="4"/>
<g id="construction" fill="none" stroke="#9cc8ff" stroke-width="1.5" stroke-dasharray="14 6 3 6">
<path d="M370 150V620M180 400H600"/><circle cx="370" cy="400" r="180"/><circle cx="370" cy="400" r="120"/><path d="M60 840H990"/><path d="M700 640 L980 640"/></g>
<g id="fox" fill="none" stroke="%(ln)s" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">
<path d="%(TAIL)s" stroke-width="4"/><path d="%(TAIL_TIP)s" fill="url(#hatch)"/>
<path d="%(BODY)s" stroke-width="4"/><path d="%(HAUNCH)s"/><path d="%(LEG2)s" fill="url(#hatch)"/><path d="%(CHEST)s"/><path d="%(LEG)s" fill="url(#hatch)"/>
<path d="%(HEAD)s" stroke-width="4"/><path d="%(CHEEK)s"/><path d="%(MUZZLE)s"/><path d="%(EAR_L)s" fill="url(#hatch)"/><path d="%(EAR_R)s" fill="url(#hatch)"/><path d="%(EYE)s"/><circle cx="236" cy="488" r="10" fill="%(ln)s"/></g>
<g id="dimensions" fill="none" stroke="%(ln)s" stroke-width="1.5" font-family="'Courier New',monospace" font-size="20">
<path d="M232 130V236M984 470V500M232 180H352M352 180H492" stroke-dasharray="none"/>
<path d="M232 180H492" marker-start="url(#arr)" marker-end="url(#arr)"/>
<path d="M60 222V840" marker-start="url(#arr)" marker-end="url(#arr)"/><path d="M60 222H340M60 840H300" stroke-dasharray="5 4"/>
<path d="M232 880H962" marker-start="url(#arr)" marker-end="url(#arr)"/><path d="M232 850V890M962 850V890"/>
<path d="M440 100L400 150" /><text x="446" y="98" fill="%(ln)s" stroke="none">A: EAR TIP</text>
<text x="264" y="170" fill="%(ln)s" stroke="none">260</text><text x="70" y="540" fill="%(ln)s" stroke="none" transform="rotate(-90 70 540)">618</text>
<text x="560" y="912" fill="%(ln)s" stroke="none">730</text>
<path d="M760 400H930L904 476" /><text x="760" y="390" fill="%(ln)s" stroke="none">B: BRUSH TIP</text>
</g>
<g id="title-block" fill="none" stroke="%(ln)s" stroke-width="2"><rect x="560" y="920" width="410" height="54"/><path d="M770 920V974"/>
<text x="572" y="944" fill="%(ln)s" stroke="none" font-family="'Courier New',monospace" font-size="18">VULPES VULPES</text><text x="572" y="965" fill="%(ln)s" stroke="none" font-family="'Courier New',monospace" font-size="14">SHEET 1/1  SCALE 1:8</text><text x="784" y="944" fill="%(ln)s" stroke="none" font-family="'Courier New',monospace" font-size="14">DWG NO. FX-001</text><text x="784" y="965" fill="%(ln)s" stroke="none" font-family="'Courier New',monospace" font-size="14">REV A</text></g>
</svg>
""" % dict(globals(), ln=ln)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in [("fox", base), ("fox-ukiyo-e", ukiyo), ("fox-cyberpunk-neon", cyber),
                     ("fox-paper-cutout", paper), ("fox-blueprint", blueprint)]:
        (out / (name + ".svg")).write_text(fn(), encoding="utf-8")
        print("wrote", out / (name + ".svg"))
