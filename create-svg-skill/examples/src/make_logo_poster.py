#!/usr/bin/env python3
"""Generates two non-illustration examples: an Art Deco hotel logo and a vintage travel poster.
Usage: python3 make_logo_poster.py OUTDIR
Text is live (fonts not embedded; generic fallbacks given) - convert to outlines before print.
"""
import math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "scripts"))
from text_to_path import text_path, text_group  # noqa: E402  (text is outlined: no font dependency)

F = HERE / "fonts"
ANTON, SERIF, GROT = (str(F / n) for n in ("anton-latin-400-normal.woff2", "instrument-serif-latin-400-normal.woff2",
                                          "space-grotesk-latin-500-normal.woff2"))


def tg(font, text, size, x, y, width=None, attrs=""):
    return text_group(font, text, size=size, x=x, y=y, anchor="middle", width=width, attrs=attrs)


def deco_logo():
    cx, cy = 512, 520
    rays = "".join('<use href="#ray" transform="rotate(%d %d %d)"/>' % (a, cx, cy) for a in range(-80, 81, 10))
    arcs = "".join('<path d="M%d %d a%d %d 0 0 1 %d 0"/>' % (cx - r, cy - 10, r, r, 2 * r) for r in (112, 148, 184))
    flutes = "".join('<path d="M%d 340V548"/>' % x for x in (480, 512, 544))
    diamonds = "".join('<path d="M%d 618l10 10l-10 10l-10 -10z"/>' % x for x in (452, 512, 572))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-labelledby="t d">
<title id="t">The Meridian Hotel</title><desc id="d">Art Deco luxury hotel logo: gold sunburst, stepped tower, chamfered frame, spaced serif lettering on midnight navy.</desc>
<defs>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6e2a0"/><stop offset=".45" stop-color="#d7a94a"/><stop offset=".7" stop-color="#f1d78c"/><stop offset="1" stop-color="#a87422"/></linearGradient>
<path id="ray" d="M{cx} {cy} L{cx-9} {cy-300} H{cx+9} Z"/>
</defs>
<rect id="ground" width="1024" height="1024" fill="#0c1a2b"/>
<g id="frame" fill="none" stroke="url(#gold)">
<path d="M110 70H914L954 110V914L914 954H110L70 914V110Z" stroke-width="7"/>
<path d="M126 92H898L932 126V898L898 932H126L92 898V126Z" stroke-width="2.5"/>
<path d="M70 190H92M932 190H954M70 834H92M932 834H954" stroke-width="5"/></g>
<g id="sunburst" fill="url(#gold)" opacity=".92">{rays}</g>
<g id="halo" fill="none" stroke="url(#gold)" stroke-width="4">{arcs}</g>
<g id="tower" stroke="url(#gold)" stroke-width="5" stroke-linejoin="miter">
<path d="M440 560V400H470V330H554V400H584V560Z" fill="#0c1a2b"/>
<path d="M486 330V270H538V330" fill="#0c1a2b"/>
<path d="M500 270L512 190L524 270Z" fill="url(#gold)"/>
<g fill="none" stroke-width="3">{flutes}</g></g>
<g id="plinth" fill="url(#gold)"><rect x="400" y="560" width="224" height="16"/><rect x="360" y="588" width="304" height="8"/><rect x="330" y="608" width="364" height="4"/></g>
<g id="ornament" fill="url(#gold)">{diamonds.replace('<path','<path fill="url(#gold)"')}</g>
<g id="wordmark" fill="url(#gold)">
{tg(SERIF, 'THE MERIDIAN', 96, 512, 726, 640)}
{tg(GROT, 'HOTEL & RESIDENCES', 26, 512, 790, 440)}
{tg(GROT, 'EST · 1928', 20, 512, 868, 190)}</g>
<g id="rules" stroke="url(#gold)" stroke-width="2"><path d="M206 812H430M594 812H818"/><path d="M256 828H430M594 828H768" stroke-width="1"/></g>
</svg>
"""


def poster():
    rays = "".join('<path d="M400 470 L%.1f %.1f L%.1f %.1f Z"/>' % (
        400 + 900 * math.cos(math.radians(a)), 470 - 900 * math.sin(math.radians(a)),
        400 + 900 * math.cos(math.radians(a + 4)), 470 - 900 * math.sin(math.radians(a + 4)))
        for a in range(5, 180, 12))
    pines = "".join('<use href="#pine" transform="translate(%d %d) scale(%s)"/>' % (x, y, s) for x, y, s in [
        (60, 790, 1.5), (130, 815, 1.15), (215, 800, 1.3), (620, 800, 1.4), (700, 780, 1.7), (760, 822, 1.1), (555, 830, .9)])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1120" role="img" aria-labelledby="t d">
<title id="t">Visit the Highlands</title><desc id="d">Vintage travel poster: sunburst over layered mountains and a lake, pines in the foreground, bold condensed title band, cream paper border.</desc>
<defs>
<clipPath id="art"><rect x="50" y="50" width="700" height="800"/></clipPath>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4b24a"/><stop offset="1" stop-color="#f7dfa6"/></linearGradient>
<path id="pine" d="M0 -150L-18 -95H-10L-30 -45H-18L-44 0H-6V20H6V0H44L18 -45H30L10 -95H18Z"/>
<pattern id="grain" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r=".8" fill="#5b3a1e" opacity=".22"/><circle cx="4.5" cy="4.5" r=".6" fill="#5b3a1e" opacity=".18"/></pattern>
</defs>
<rect id="paper" width="800" height="1120" fill="#f1e6cc"/>
<g id="scene" clip-path="url(#art)">
<rect x="50" y="50" width="700" height="800" fill="url(#sky)"/>
<g id="sunburst" fill="#f7dfa6" opacity=".55">{rays}</g>
<circle cx="400" cy="470" r="112" fill="#d9482b"/><circle cx="400" cy="470" r="82" fill="#e9713a"/>
<g id="far-range"><path d="M50 560L170 430L250 510L340 400L470 560Z" fill="#c9a89a"/><path d="M400 560L520 420L610 500L680 440L750 520V600H400Z" fill="#c9a89a"/></g>
<g id="mid-range"><path d="M50 640L200 470L300 590L420 500L560 640Z" fill="#3f7f86"/><path d="M200 470L245 545L215 560L180 520Z" fill="#2f666d"/><path d="M420 500L470 570L440 590L400 540Z" fill="#2f666d"/><path d="M420 500L455 545L433 553Z" fill="#f1e6cc"/><path d="M200 470L228 507L207 512Z" fill="#f1e6cc"/><path d="M460 650L620 500L750 610V700H460Z" fill="#2d5f7a"/><path d="M620 500L665 570L640 585L600 540Z" fill="#234c63"/></g>
<g id="lake"><rect x="50" y="660" width="700" height="190" fill="#1f4e6b"/><g fill="#d9482b" opacity=".85"><rect x="350" y="674" width="100" height="6"/><rect x="368" y="690" width="64" height="5"/><rect x="384" y="704" width="32" height="4"/></g><g fill="#6fa3a6" opacity=".7"><rect x="120" y="720" width="120" height="3"/><rect x="520" y="752" width="150" height="3"/><rect x="230" y="790" width="90" height="3"/></g></g>
<path id="shore" d="M50 780C160 745 260 770 330 800S520 830 750 770V850H50Z" fill="#2c5a3e"/>
<g id="pines" fill="#173b2c">{pines}</g>
<rect id="grain-overlay" x="50" y="50" width="700" height="800" fill="url(#grain)"/>
</g>
<rect id="frame" x="50" y="50" width="700" height="800" fill="none" stroke="#173b2c" stroke-width="8"/>
<g id="titleband">
{tg(ANTON, 'HIGHLANDS', 128, 406, 1050, 690, 'fill="#d9482b"')}
{tg(ANTON, 'HIGHLANDS', 128, 400, 1044, 690, 'fill="#173b2c"')}
{tg(ANTON, 'VISIT THE', 44, 400, 922, 400, 'fill="#173b2c"')}
{tg(SERIF, 'RAIL & STEAMER · EVERY SUMMER', 28, 400, 1088, 600, 'fill="#3f7f86"')}</g>
<g id="rules" fill="#173b2c"><rect x="50" y="868" width="700" height="4"/></g>
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "."); out.mkdir(parents=True, exist_ok=True)
    (out / "logo-art-deco-hotel.svg").write_text(deco_logo(), encoding="utf-8")
    (out / "poster-vintage-highlands.svg").write_text(poster(), encoding="utf-8")
    print("wrote logo + poster to", out)
