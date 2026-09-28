from engine import *  # engine.py beside this file

PAPER, INK, NIGHT = hx("F3E9D2"), hx("1A1410"), hx("101826")
LAPIS, SAFFRON, POMEGRANATE, JADE = hx("1F3A93"), hx("F4A300"), hx("C8102E"), hx("0F8A6B")

get_font("anton", "ofl/anton/Anton-Regular.ttf")
get_font("mono", "ofl/spacemono/SpaceMono-Regular.ttf")
get_font("fri", "ofl/fraunces/Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", [144, 380, 100, 1])
get_font("arabic", "ofl/notonaskharabic/NotoNaskhArabic[wght].ttf", [700])

for n, s in [("anton", "SILK ROAD"), ("mono", "c. 130 BCE · Chang'an → Samarkand → Antioch"), ("arabic", "طريق الحرير")]:
    assert not missing_glyphs(n, s), (n, missing_glyphs(n, s))

ROUTE = bezier((180, 700), (600, 300), (1200, 900), (1740, 420), 120)
ROUTE_CUM = cumlen(ROUTE)


def s_open(ctx, b, f):
    bg(ctx, NIGHT)
    w = wave_at(f).astype(float)
    ys = 540 + w / (abs(w).max() + .03) * (60 + 200 * env_at(f))
    rgba(ctx, SAFFRON); ctx.set_line_width(3)
    polyline(ctx, np.stack([np.linspace(0, W, len(ys)), ys], 1)); ctx.stroke()
    riso(ctx, lambda c: text(ctx, "SILK ROAD", "anton", 300, c, W / 2, 620, ax=.5, sc=back(ph(b, 4, .6))),
         PAPER, POMEGRANATE, dark=True, k=1.8)
    text(ctx, "طريق الحرير", "arabic", 90, SAFFRON, W / 2, 330, ax=.5, alpha=ph(b, 5, 1))
    return PAPER


def s_route(ctx, b, f):
    bg(ctx, PAPER)
    ctx.set_source(halftone(LAPIS, 10, 2.4)); ctx.rectangle(0, 760, W, 320); ctx.fill()
    rgba(ctx, POMEGRANATE); ctx.set_line_width(6)
    e = path_partial(ctx, ROUTE, ROUTE_CUM, eio(ph(b, 8, 6))); ctx.stroke()
    if e is not None:
        rgba(ctx, SAFFRON); ctx.arc(e[0], e[1], 12 + 5 * pulse(b), 0, 2 * PI); ctx.fill()
    for i, (x, y, name) in enumerate([(180, 700, "CHANG'AN"), (960, 620, "SAMARKAND"), (1740, 420, "ANTIOCH")]):
        text(ctx, name, "anton", 70, LAPIS, x, y - 30, ax=.5, sc=back(ph(b, 8 + i * 2.5, .5)))
    text_circle(ctx, "SILK · SPICE · PAPER · IDEAS · ", "mono", 16, INK, 1600, 850, 90, b * .3, alpha=ph(b, 9, 1))
    typewriter(ctx, "c. 130 BCE · Chang'an → Samarkand → Antioch", "mono", 22, INK, 120, 990, b, 9)
    return INK


def s_drop(ctx, b, f):
    pal = [(POMEGRANATE, PAPER), (LAPIS, SAFFRON)][int((b - 16) // 4) % 2]
    bg(ctx, pal[0])
    riso(ctx, lambda c: text(ctx, "6,400 km", "anton", fit_size("6,400 km", "anton", 1500, 400), c, W / 2, 560,
                             ax=.5, ay=.5, sc=1 + .04 * pulse(b, 8)), pal[1], JADE, dark=True, k=2)
    text(ctx, "of trade, carried on foot and hoof", "fri", 56, PAPER, W / 2, 820, ax=.5, alpha=ph(b, 17, 1))
    return PAPER


def s_end(ctx, b, f):
    bg(ctx, NIGHT)
    rgba(ctx, POMEGRANATE); ctx.arc(W / 2, H / 2, 18 + 8 * pulse(b), 0, 2 * PI); ctx.fill()
    return PAPER


def hud(ctx, b, fg):
    reg_marks(ctx, fg, (LAPIS, SAFFRON, POMEGRANATE, JADE))
    if 8 <= b < 24:
        text(ctx, "PLATE 0%d" % (1 + int(b >= 16)), "mono", 15, fg, W - 70, 86, ax=1)


SCENES = [(0, s_open), (8, s_route), (16, s_drop), (24, s_end)]
run(SCENES, 28, bpm=110, name="demo",
    wipes=[(8, POMEGRANATE, SAFFRON), (16, LAPIS, JADE, iris_wipe), (24, SAFFRON, POMEGRANATE)],
    glitches=[(15.5, 16.1)], flashes=[(16, WHITE, .5)], hud=hud, fade_out=25)
