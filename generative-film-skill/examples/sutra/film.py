"""SUTRA — a film in one thread. Every frame is drawn in code (cairo + PIL text)."""
import math, sys, subprocess
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw

W, H, FPS = 1920, 1080, 30
BEAT = 0.625
ENV = np.load("env.npy")
WAVE = np.load("wave.npy")
NF = len(ENV)
PI = math.pi


def hx(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


PAPER, INDIGO, SINDOOR, HALDI = hx("F1E6CF"), hx("1B2A6B"), hx("EE3B1E"), hx("FFB21A")
RANI, MOR, NIGHT, INK = hx("FF3E9A"), hx("00A38C"), hx("0A0D26"), hx("14121C")
WHITE = (1.0, 1.0, 1.0)

F = "fonts/"
FONT = {
    "anton": (F + "Anton-Regular.ttf", None),
    "tiro": (F + "TiroDevanagariSanskrit-Regular.ttf", None),
    "tiroi": (F + "TiroDevanagariSanskrit-Italic.ttf", None),
    "brahmi": (F + "NotoSansBrahmi-Regular.ttf", None),
    "mono": (F + "SpaceMono-Regular.ttf", None),
    "monob": (F + "SpaceMono-Bold.ttf", None),
    "frb": (F + "Fraunces.ttf", [144, 900, 100, 1]),
    "fri": (F + "Fraunces-Italic.ttf", [144, 380, 100, 1]),
    "tamil": (F + "Tamil.ttf", [700, 100]),
    "bengali": (F + "Bengali.ttf", [700, 100]),
    "thai": (F + "Thai.ttf", [700, 100]),
    "tibetan": (F + "Tibetan.ttf", [700]),
}

# ------------------------------------------------------------------ text
_fc, _tc = {}, {}


def font(name, size):
    k = (name, size)
    if k not in _fc:
        p, var = FONT[name]
        f = ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
        if var:
            f.set_variation_by_axes(var)
        _fc[k] = f
    return _fc[k]


def tsurf(txt, name, size, color, stroke=0):
    k = (txt, name, size, color, stroke)
    if k in _tc:
        return _tc[k]
    f = font(name, size)
    l, t, r, b = f.getbbox(txt, anchor="ls", stroke_width=stroke)
    p = 4
    w, h = int(r - l + 2 * p), int(b - t + 2 * p)
    img = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = tuple(int(c * 255) for c in color) + (255,)
    if stroke:
        d.text((p - l, p - t), txt, font=f, anchor="ls", fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=col)
    else:
        d.text((p - l, p - t), txt, font=f, anchor="ls", fill=col)
    a = np.asarray(img).astype(np.float32)
    al = a[..., 3] / 255
    buf = np.empty((h, w, 4), np.uint8)
    buf[..., 0] = a[..., 2] * al
    buf[..., 1] = a[..., 1] * al
    buf[..., 2] = a[..., 0] * al
    buf[..., 3] = a[..., 3]
    s = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, w, h, w * 4)
    res = (s, buf, p - l, p - t, l, t, r, b)
    _tc[k] = res
    return res


def text(ctx, txt, name, size, color, x, y, ax=0.0, ay=None, alpha=1.0, rot=0.0, sc=1.0, stroke=0, op=None):
    if alpha <= 0.003 or sc <= 0.001 or not txt:
        return 0
    s, buf, ox, oy, l, t, r, b = tsurf(txt, name, size, color, stroke)
    px = l + ax * (r - l)
    py = 0 if ay is None else t + ay * (b - t)
    ctx.save()
    if op is not None:
        ctx.set_operator(op)
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    if sc != 1:
        ctx.scale(sc, sc)
    ctx.set_source_surface(s, -(ox + px), -(oy + py))
    if alpha < 1:
        ctx.paint_with_alpha(alpha)
    else:
        ctx.paint()
    ctx.restore()
    return (r - l) * sc


def tw(txt, name, size):
    l, t, r, b = font(name, size).getbbox(txt, anchor="ls")
    return r - l


def text_circle(ctx, txt, name, size, color, cx, cy, R, ang0, alpha=1.0):
    f = font(name, size)
    widths = [f.getlength(c) for c in txt]
    a = ang0
    for c, w in zip(txt, widths):
        a += (w / 2) / R
        if c != " ":
            text(ctx, c, name, size, color, cx + R * math.cos(a), cy + R * math.sin(a), ax=0.5, ay=None,
                 rot=a + PI / 2, alpha=alpha)
        a += (w / 2) / R


# ------------------------------------------------------------------ utils
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back(x):
    x = cl(x); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ph(b, a, d):
    return cl((b - a) / d)


def pulse(b, k=5.0):
    return math.exp(-(b % 1) * k)


def lerp(a, b, t):
    return a + (b - a) * t


def bg(ctx, c):
    ctx.set_source_rgb(*c); ctx.paint()


def rgba(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


REG = [5.0, 4.0]


def riso(ctx, fn, main, off, dark=False, k=1.0):
    ctx.save()
    ctx.translate(REG[0] * k, REG[1] * k)
    ctx.set_operator(cairo.OPERATOR_SCREEN if dark else cairo.OPERATOR_MULTIPLY)
    fn(off)
    ctx.restore()
    fn(main)


_hp = {}


def halftone(color, step=11, r=2.8, ang=0.5):
    k = (color, step, r, ang)
    if k not in _hp:
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, step, step)
        c = cairo.Context(s)
        c.set_source_rgb(*color); c.arc(step / 2, step / 2, r, 0, 2 * PI); c.fill()
        pat = cairo.SurfacePattern(s); pat.set_extend(cairo.EXTEND_REPEAT)
        m = cairo.Matrix(); m.rotate(ang); pat.set_matrix(m)
        _hp[k] = (pat, s)
    return _hp[k][0]


def cumlen(pts):
    d = np.hypot(*np.diff(pts, axis=0).T)
    return np.concatenate([[0], np.cumsum(d)])


def path_partial(ctx, pts, cum, frac):
    L = cum[-1] * cl(frac)
    if L <= 0:
        return None
    i = int(np.searchsorted(cum, L))
    ctx.move_to(*pts[0])
    for p in pts[1:i]:
        ctx.line_to(p[0], p[1])
    if i < len(pts):
        a, b_ = pts[i - 1], pts[i]
        seg = cum[i] - cum[i - 1]
        t = (L - cum[i - 1]) / seg if seg > 0 else 0
        e = a + (b_ - a) * t
        ctx.line_to(e[0], e[1])
        return e
    return pts[-1]


DEV = "०१२३४५६७८९"


def dev(n):
    return "".join(DEV[int(c)] for c in str(n))


BRAHMI_DIG = "𑁦𑁧𑁨𑁩𑁪𑁫𑁬𑁭𑁮𑁯"

# ------------------------------------------------------------------ precomputed geometry
rng = np.random.default_rng(11)

# grain
def make_grain(seed):
    r = np.random.default_rng(seed)
    g = r.normal(128, 40, (H, W))
    low = np.asarray(Image.fromarray((r.random((27, 48)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                     np.float32)
    g = np.clip(g + (low - 128) * 0.5, 0, 255)
    a = 0.13
    buf = np.empty((H, W, 4), np.uint8)
    v = (g * a).astype(np.uint8)
    buf[..., 0] = v; buf[..., 1] = v; buf[..., 2] = v; buf[..., 3] = int(255 * a)
    return cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, W, H, W * 4), buf


GRAIN = [make_grain(s) for s in range(3)]

# Sindhu city grid (local coords)
G_COLS, G_ROWS, G_BW, G_BH, G_ST = 7, 4, 106, 96, 24
G_W = G_COLS * G_BW + (G_COLS + 1) * G_ST
G_H = G_ROWS * G_BH + (G_ROWS + 1) * G_ST
BLOCKS = []
for r_ in range(G_ROWS):
    for c_ in range(G_COLS):
        x0 = -G_W / 2 + G_ST + c_ * (G_BW + G_ST)
        y0 = -G_H / 2 + G_ST + r_ * (G_BH + G_ST)
        n = int(rng.integers(1, 4))
        cuts = sorted(rng.uniform(0.25, 0.75, n - 1).tolist())
        court = rng.random() < 0.45
        BLOCKS.append((x0, y0, cuts, court, r_, c_))
BATH = 9  # index of Great Bath block
spath = []
for r_ in range(G_ROWS + 1):
    y = -G_H / 2 + G_ST / 2 + r_ * (G_BH + G_ST)
    xs = [-G_W / 2 + G_ST / 2, G_W / 2 - G_ST / 2]
    if r_ % 2:
        xs = xs[::-1]
    spath += [(xs[0], y), (xs[1], y)]
for c_ in range(G_COLS + 1):
    x = G_W / 2 - G_ST / 2 - c_ * (G_BW + G_ST)
    ys = [G_H / 2 - G_ST / 2, -G_H / 2 + G_ST / 2]
    if c_ % 2:
        ys = ys[::-1]
    spath += [(x, ys[0]), (x, ys[1])]
SPATH = np.array(spath, float)
SPATH_CUM = cumlen(SPATH)


# Kolam mirror curve
def mirror_curve(a, b):
    x, y, dx, dy = 1, 0, 1, 1
    start = (x, y, dx, dy)
    pts = [(x, y)]
    while True:
        x += dx; y += dy
        if x == 0 or x == 2 * a:
            dx = -dx
        if y == 0 or y == 2 * b:
            dy = -dy
        pts.append((x, y))
        if (x, y, dx, dy) == start:
            break
    return np.array(pts[:-1], float)


def chaikin(P, it=4):
    for _ in range(it):
        P1 = np.roll(P, -1, axis=0)
        Q = np.empty((len(P) * 2, 2))
        Q[0::2] = 0.75 * P + 0.25 * P1
        Q[1::2] = 0.25 * P + 0.75 * P1
        P = Q
    return np.vstack([P, P[:1]])


KA, KB, KU = 7, 5, 58
KOL = chaikin(mirror_curve(KA, KB)) * KU + np.array([960 - KA * KU, 520 - KB * KU])
KOL_CUM = cumlen(KOL)
KOL_DOTS = [(960 - KA * KU + (2 * i + 1) * KU, 520 - KB * KU + (2 * j + 1) * KU) for j in range(KB) for i in range(KA)]
MINI_KOL = chaikin(mirror_curve(3, 2)) - np.array([3, 2])

# Stars
STARS = [(rng.uniform(70, 1150), rng.uniform(0, 2 * PI), rng.uniform(0.8, 2.6),
          [PAPER, PAPER, PAPER, HALDI, RANI][int(rng.integers(0, 5))]) for _ in range(300)]
SKY = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.2), rng.uniform(0, 6.28)) for _ in range(260)]

PI_DIGITS = ("3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706"
             "798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196")
PI_POS = []
_th, _r = 0.0, 205.0
for ch in PI_DIGITS:
    PI_POS.append((_r * math.cos(_th), _r * math.sin(_th), _th))
    _th += 21 / _r
    _r = 205 + 13 * _th

PASCAL = [[math.comb(r_, k) for k in range(r_ + 1)] for r_ in range(66)]

WORDS = [("SHAMPOO", "← chāmpo · 'press'"), ("BUNGALOW", "← baṅglā · 'Bengal-style house'"),
         ("PYJAMA", "← pāy-jāma · 'leg garment'"), ("JUNGLE", "← jaṅgal · 'wild land'"),
         ("LOOT", "← lūṭ · 'plunder'"), ("CALICO", "← Calicut · the port"), ("CHINTZ", "← chīṇṭ · 'spotted cloth'"),
         ("THUG", "← ṭhag · 'swindler'"), ("KHAKI", "← khākī · 'dust-coloured'"), ("AVATAR", "← avatāra · 'descent'"),
         ("GURU", "← guru · 'heavy, venerable'"), ("KARMA", "← karma · 'action'"),
         ("DUNGAREE", "← ḍuṅgrī · 'coarse cloth'"), ("CHUTNEY", "← caṭnī · 'to lick'"),
         ("CUMMERBUND", "← kamarband · 'waist-band'"), ("CASHMERE", "← Kashmir")]
_order = rng.permutation(16)
WORD_LAYOUT = []
for i in range(16):
    cell = int(_order[i])
    cx_ = 120 + (cell % 4) * 425 + 30 + rng.uniform(0, 40)
    cy_ = 380 + (cell // 4) * 160 + rng.uniform(-8, 8)
    WORD_LAYOUT.append((cx_, cy_, rng.uniform(-0.1, 0.1), [INDIGO, SINDOOR, RANI, MOR, INK][i % 5]))

CRATERS = [(rng.uniform(-900, 900), rng.uniform(20, 330), rng.uniform(20, 120)) for _ in range(38)]


# ------------------------------------------------------------------ drawing primitives
def chakra(ctx, cx, cy, R, ang, color):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang)
    rgba(ctx, color)
    ctx.set_line_width(R * 0.075); ctx.arc(0, 0, R * 0.96, 0, 2 * PI); ctx.stroke()
    ctx.arc(0, 0, R * 0.17, 0, 2 * PI); ctx.fill()
    for i in range(24):
        t = i * 2 * PI / 24
        ctx.move_to(R * 0.17 * math.cos(t), R * 0.17 * math.sin(t))
        for rr, dt in ((0.55, 0.035), (0.9, 0.0)):
            ctx.line_to(R * rr * math.cos(t + dt), R * rr * math.sin(t + dt))
        ctx.line_to(R * 0.55 * math.cos(t - 0.035), R * 0.55 * math.sin(t - 0.035))
        ctx.close_path(); ctx.fill()
        t2 = t + PI / 24
        ctx.arc(R * 0.9 * math.cos(t2), R * 0.9 * math.sin(t2), R * 0.035, 0, 2 * PI); ctx.fill()
    ctx.restore()


def spire_path(ctx, x, y, w, h):
    ctx.move_to(x - w / 2, y)
    ctx.curve_to(x - w / 2, y - 0.55 * h, x - 0.32 * w, y - 0.93 * h, x - 0.14 * w, y - h)
    ctx.line_to(x + 0.14 * w, y - h)
    ctx.curve_to(x + 0.32 * w, y - 0.93 * h, x + w / 2, y - 0.55 * h, x + w / 2, y)
    ctx.close_path()


def spire(ctx, x, y, w, h, fill, line):
    spire_path(ctx, x, y, w, h)
    rgba(ctx, fill); ctx.fill_preserve()
    rgba(ctx, line); ctx.set_line_width(max(1.2, w * 0.012)); ctx.stroke()
    ctx.save(); spire_path(ctx, x, y, w, h); ctx.clip()
    ctx.set_line_width(max(0.8, w * 0.007))
    for k in range(1, 12):
        yy = y - h * k / 12
        ctx.move_to(x - w, yy); ctx.line_to(x + w, yy)
    for dx in (-0.16, 0, 0.16):
        ctx.move_to(x + dx * w, y); ctx.line_to(x + dx * w * 0.6, y - h)
    ctx.stroke(); ctx.restore()
    ctx.save(); ctx.translate(x, y - h - 0.035 * h); ctx.scale(0.2 * w, 0.045 * h)
    ctx.arc(0, 0, 1, 0, 2 * PI); ctx.restore()
    rgba(ctx, fill); ctx.fill_preserve(); rgba(ctx, line); ctx.set_line_width(max(1, w * 0.01)); ctx.stroke()
    ctx.arc(x, y - h - 0.1 * h, 0.035 * w, 0, 2 * PI); rgba(ctx, line); ctx.fill()


def temple(ctx, x, y, w, h, depth, b, t0, maxd):
    """draw children (behind) then self; reveal by depth."""
    if depth < maxd:
        for side in (-1, 1):
            temple(ctx, x + side * w * 0.56, y, w * 0.6, h * 0.6, depth + 1, b, t0, maxd)
            temple(ctx, x + side * w * 0.33, y - h * 0.28, w * 0.44, h * 0.44, depth + 1, b, t0, maxd)
    g = eo(ph(b, t0 + depth * 2, 1.4))
    if g <= 0:
        return
    fills = [PAPER, HALDI, RANI, PAPER]
    spire(ctx, x, y, w * (0.6 + 0.4 * g), h * g, fills[depth], INDIGO)


def cube(ctx, x, y, s, alpha=1.0):
    d = s * 0.42
    faces = [([(x, y), (x + s, y), (x + s, y - s), (x, y - s)], HALDI),
             ([(x, y - s), (x + s, y - s), (x + s + d, y - s - d * 0.7), (x + d, y - s - d * 0.7)], hx("FFD98A")),
             ([(x + s, y), (x + s + d, y - d * 0.7), (x + s + d, y - s - d * 0.7), (x + s, y - s)], SINDOOR)]
    for pts, c in faces:
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        rgba(ctx, c, alpha); ctx.fill_preserve()
        rgba(ctx, INK, alpha); ctx.set_line_width(2); ctx.stroke()


def reg_marks(ctx, fg, a=0.6):
    rgba(ctx, fg, a); ctx.set_line_width(1.3)
    for (x, y) in ((36, 36), (W - 36, 36), (36, H - 36), (W - 36, H - 36)):
        ctx.arc(x, y, 9, 0, 2 * PI); ctx.stroke()
        ctx.move_to(x - 17, y); ctx.line_to(x + 17, y); ctx.move_to(x, y - 17); ctx.line_to(x, y + 17); ctx.stroke()
    for i, c in enumerate((INDIGO, SINDOOR, HALDI, RANI, MOR)):
        rgba(ctx, c); ctx.rectangle(29, 470 + i * 22, 14, 14); ctx.fill()


# ------------------------------------------------------------------ chapters / HUD
CH = [(0, "BINDU"), (12, "SINDHU"), (28, "ŚRUTI"), (40, "BRĀHMĪ"), (52, "ĀRYABHAṬA"), (64, "ŚŪNYA"),
      (80, "ŚIKHARA"), (92, "KOLAM"), (108, "CHANDRA"), (120, "SŪTRA")]
YEARS = [(12, -2600), (28, -1500), (40, -250), (52, 499), (64, 628), (80, 1030), (100, 1700), (108, 2023)]


def chapter(b):
    i = 0
    for k, (s, _) in enumerate(CH):
        if b >= s:
            i = k
    return i


def year_at(b):
    prev, cur = None, YEARS[0][1]
    for s, y in YEARS:
        if b >= s:
            cur = y if prev is None else int(round(lerp(prev, y, eio(ph(b, s, 1.0)))))
            prev = y
    return cur


def hud(ctx, b, fg):
    reg_marks(ctx, fg)
    if not (12 <= b < 120):
        return
    a = min(ph(b, 12, 1), 1 - ph(b, 119, 1))
    text(ctx, "सूत्र", "tiro", 38, fg, 72, 92, alpha=a)
    text(ctx, "SŪTRA — a film in one thread", "mono", 15, fg, 165, 86, alpha=a * 0.8)
    ci = chapter(b)
    text(ctx, BRAHMI_DIG[ci], "brahmi", 78, fg, W - 70, 118, ax=1, alpha=a)
    text(ctx, "PLATE 0%d / 08 · %s" % (ci, CH[ci][1]), "mono", 15, fg, W - 150, 86, ax=1, alpha=a * 0.8)
    # year
    if 92 <= b < 100:
        text(ctx, "प्रतिदिन", "tiro", 46, fg, 72, 1004, alpha=a)
        text(ctx, "EVERY DAWN, STILL", "mono", 15, fg, 74, 1032, alpha=a * 0.8)
    else:
        y = year_at(b)
        if y < 0:
            dv, lt = "ई.पू. " + dev(-y), "%d BCE" % -y
        else:
            dv, lt = dev(y) + " ई.", "%d CE" % y
        text(ctx, dv, "tiro", 46, fg, 72, 1004, alpha=a)
        text(ctx, "c. " + lt, "mono", 15, fg, 74, 1032, alpha=a * 0.8)
    # progress thread
    x0, x1, yy = 560, W - 70, 1030
    rgba(ctx, fg, 0.35 * a); ctx.set_line_width(1.5); ctx.move_to(x0, yy); ctx.line_to(x1, yy); ctx.stroke()
    px = lerp(x0, x1, (b - 12) / 108)
    rgba(ctx, SINDOOR, a); ctx.set_line_width(3.5); ctx.move_to(x0, yy); ctx.line_to(px, yy); ctx.stroke()
    for s, _ in CH[1:]:
        xx = lerp(x0, x1, (s - 12) / 108)
        rgba(ctx, fg, 0.6 * a); ctx.arc(xx, yy, 3.5, 0, 2 * PI); ctx.fill()
    rgba(ctx, SINDOOR, a); ctx.arc(px, yy, 7 + 3 * pulse(b, 6), 0, 2 * PI); ctx.fill()


def caption(ctx, s, fg, b, t0, x=560, y=985, size=21, alpha=1.0):
    n = int(len(s) * cl((b - t0) / 1.2))  # typewriter
    text(ctx, s[:n], "mono", size, fg, x, y, alpha=alpha)


# ------------------------------------------------------------------ scenes
def s_intro(ctx, b, f):
    bg(ctx, NIGHT)
    cx, cy = W / 2, H / 2
    if b < 4.6:
        for k in range(int(b) + 1):
            age = b - k
            if 0 <= age < 3:
                rgba(ctx, SINDOOR, 0.45 * (1 - age / 3)); ctx.set_line_width(2.5)
                ctx.arc(cx, cy, 30 + age * 260, 0, 2 * PI); ctx.stroke()
        rad = 14 + 12 * pulse(b, 4) + 5 * b
        st = eio(ph(b, 3.5, 1.0))
        half = rad + st * (W / 2 + 60)
        th = rad * (1 - st) + 3 * st
        rgba(ctx, SINDOOR)
        if st <= 0:
            ctx.arc(cx, cy, rad, 0, 2 * PI); ctx.fill()
        else:
            ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(2 * th)
            ctx.move_to(cx - half + th, cy); ctx.line_to(cx + half - th, cy); ctx.stroke()
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        a = ph(b, 1.0, 0.8) * (1 - ph(b, 3.3, 0.5))
        text(ctx, "बिन्दु", "tiro", 64, PAPER, cx, cy + 170, ax=0.5, alpha=a)
        text(ctx, "bindu — the point from which everything is drawn", "mono", 20, PAPER, cx, cy + 215, ax=0.5,
             alpha=a * 0.75)
        if b < 4:
            return PAPER
    # title
    amp = 30 + 140 * ENV[f]
    rgba(ctx, SINDOOR); ctx.set_line_width(4)
    for x in range(-20, W + 21, 12):
        y = cy + amp * math.sin(x * 0.009 + b * 2.4) * ph(b, 4.3, 1.5)
        (ctx.move_to if x == -20 else ctx.line_to)(x, y)
    ctx.stroke()
    a_dev = eo(ph(b, 8.3, 0.8))
    text(ctx, "सूत्र", "tiro", 230, HALDI, 150, 330 + 60 * (1 - a_dev), alpha=a_dev)
    letters = ["S", "Ū", "T", "R", "A"]
    cols = [PAPER, HALDI, RANI, PAPER, SINDOOR]
    size = 470
    ws = [tw(l_, "anton", size) for l_ in letters]
    gap = 24
    x = cx - (sum(ws) + gap * 4) / 2
    for i, (l_, w_) in enumerate(zip(letters, ws)):
        p = ph(b, 4 + i, 0.4)
        if p > 0:
            sc = back(p) * (1 + 0.035 * pulse(b, 7))
            rot = (0.09 if i % 2 else -0.07) * (1 - eo(ph(b, 4 + i, 1.2)))
            yy = cy + 175
            for (c, off, op) in ((RANI if i != 2 else HALDI, 9, cairo.OPERATOR_SCREEN), (cols[i], 0, None)):
                text(ctx, l_, "anton", size, c, x + w_ / 2 + off, yy + off * 0.7, ax=0.5, ay=None, sc=sc, rot=rot,
                     alpha=(0.75 if off else 1) * cl(p * 3), op=op)
        x += w_ + gap
    text(ctx, "sūtra (n.)   1. a thread   2. a rule   3. that which holds things together", "mono", 22, PAPER,
         cx, cy + 250, ax=0.5, alpha=ph(b, 9, 0.8) * 0.85)
    text(ctx, "five thousand years, one thread", "fri", 46, HALDI, cx, cy + 330, ax=0.5,
         alpha=ph(b, 10, 0.8))
    return PAPER


def s_sindhu(ctx, b, f):
    bg(ctx, PAPER)
    # vertical SINDHU
    sl = eo(ph(b, 12, 1.0))
    riso(ctx, lambda c: text(ctx, "SINDHU", "anton", 300, c, 250 - 300 * (1 - sl), 560, ax=0.5, ay=0.5, rot=-PI / 2),
         INDIGO, RANI)
    text(ctx, "सिन्धु", "tiro", 150, SINDOOR, 420, 330, alpha=eo(ph(b, 12.5, 1)), op=cairo.OPERATOR_MULTIPLY)
    text(ctx, "the river that named a subcontinent", "fri", 28, INK, 425, 385, alpha=ph(b, 13.5, 1))
    # city
    gs = 1 - 0.12 * eio(ph(b, 20, 1.2))
    ctx.save(); ctx.translate(1250, 430 - 40 * eio(ph(b, 20, 1.2))); ctx.rotate(-0.1); ctx.scale(gs, gs)
    for i, (x0, y0, cuts, court, r_, c_) in enumerate(BLOCKS):
        p = back(ph(b, 12.6 + i * 0.19, 0.5))
        if p <= 0:
            continue
        ctx.save(); ctx.translate(x0 + G_BW / 2, y0 + G_BH / 2); ctx.scale(p, p)
        ctx.rectangle(-G_BW / 2, -G_BH / 2, G_BW, G_BH)
        if i == BATH:
            rgba(ctx, MOR); ctx.fill_preserve()
        else:
            ctx.set_source(halftone(INDIGO, 9, 2.2, 0.6)); ctx.fill_preserve()
        rgba(ctx, INDIGO); ctx.set_line_width(2.5); ctx.stroke()
        for cu in cuts:
            xx = -G_BW / 2 + cu * G_BW
            ctx.move_to(xx, -G_BH / 2); ctx.line_to(xx, G_BH / 2)
        ctx.stroke()
        if court and i != BATH:
            rgba(ctx, PAPER); ctx.rectangle(-14, -14, 28, 28); ctx.fill_preserve(); rgba(ctx, INDIGO); ctx.stroke()
        if i == BATH:
            rgba(ctx, PAPER); ctx.rectangle(-30, -20, 60, 40); ctx.set_line_width(2); ctx.stroke()
        ctx.restore()
    # drains (dashed, flowing)
    da = ph(b, 15.5, 1.5)
    if da > 0:
        rgba(ctx, MOR, da); ctx.set_line_width(3); ctx.set_dash([12, 9], -(b * 40) % 21)
        for k in range(0, len(SPATH), 2):
            ctx.move_to(*SPATH[k]); ctx.line_to(*SPATH[k + 1])
        ctx.stroke(); ctx.set_dash([])
    # the thread walks the streets
    rgba(ctx, SINDOOR); ctx.set_line_width(5); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    e = path_partial(ctx, SPATH, SPATH_CUM, eio(ph(b, 12, 8)))
    ctx.stroke()
    if e is not None and b < 20.5:
        ctx.arc(e[0], e[1], 10 + 4 * pulse(b, 5), 0, 2 * PI); ctx.fill()
    bx = BLOCKS[BATH]
    la = ph(b, 16, 1)
    if la > 0:
        rgba(ctx, INK, la); ctx.set_line_width(1.5)
        ctx.move_to(bx[0] + G_BW / 2, bx[1]); ctx.line_to(bx[0] + G_BW / 2, -G_H / 2 - 30); ctx.stroke()
        text(ctx, "the Great Bath", "mono", 17, INK, bx[0] + G_BW / 2, -G_H / 2 - 38, ax=0.5, alpha=la)
    ctx.restore()
    text(ctx, "fig. 1 — a planned city: blocks, streets, covered drains (schematic)", "mono", 17, INK, 700, 740,
         alpha=ph(b, 16.5, 1) * 0.85)
    # stamp
    sp = ph(b, 13, 0.3)
    if sp > 0:
        ctx.save(); ctx.translate(560, 820); ctx.scale(1 + 1.2 * (1 - eo(sp)), 1 + 1.2 * (1 - eo(sp)))
        rgba(ctx, SINDOOR, 0.9 * eo(sp)); ctx.set_line_width(4); ctx.arc(0, 0, 98, 0, 2 * PI); ctx.stroke()
        ctx.set_line_width(1.5); ctx.arc(0, 0, 60, 0, 2 * PI); ctx.stroke()
        ctx.restore()
        text_circle(ctx, "SINDHU · SARASVATĪ · MOHENJO-DARO · HARAPPA · ", "monob", 13, SINDOOR, 560, 820, 72,
                    b * 0.25, alpha=eo(sp))
        text(ctx, "−2600", "anton", 34, SINDOOR, 560, 820, ax=0.5, ay=0.5, alpha=eo(sp))
    # weights
    x = 820
    for i in range(7):
        s = 36 * 2 ** (i / 3)
        p = ph(b, 20.2 + i, 0.45)
        if p > 0:
            yy = 950 - 260 * (1 - back(p)) if p < 1 else 950
            cube(ctx, x, yy, s, alpha=cl(p * 4))
            text(ctx, str(2 ** i), "monob", 24, INK, x + s / 2, 986, ax=0.5, alpha=cl(p * 4))
            if i:
                text(ctx, ":", "monob", 24, INK, x - 17, 986, ax=0.5, alpha=cl(p * 4))
        x += s + 34
    text(ctx, "Harappan stone weights — each one double the last", "mono", 20, INK, 820, 790,
         alpha=ph(b, 20, 1))
    return INK


PAIRS = [("A", "B"), ("B", "A"), ("A", "B"), ("B", "C"), ("C", "B"), ("B", "C"), ("C", "D"), ("D", "C"), ("C", "D")]
VED = {"A": ("अग्निम्", "agním"), "B": ("ईळे", "īḷe"), "C": ("पुरोहितं", "puróhitaṃ"), "D": ("यज्ञस्य", "yajñásya")}


def s_sruti(ctx, b, f):
    bg(ctx, INDIGO)
    text(ctx, "ŚRUTI", "anton", 560, PAPER, 960, 560, ax=0.5, ay=0.5, stroke=3, alpha=0.16,
         sc=1 + 0.06 * ph(b, 28, 12))
    # oscilloscope
    w = WAVE[min(f, NF - 1)].astype(float)
    w = np.convolve(w, np.ones(5) / 5, mode="same")
    m = np.max(np.abs(w)) + 0.03
    ys = 470 + w / m * (90 + 160 * ENV[f]) * ph(b, 28, 1.5)
    xs = np.linspace(-10, W + 10, len(ys))
    for c, lw, off, op in ((RANI, 6, (7, 6), cairo.OPERATOR_SCREEN), (HALDI, 4, (0, 0), None), (PAPER, 1.5, (-3, -2), None)):
        ctx.save()
        if op:
            ctx.set_operator(op)
        ctx.translate(*off); rgba(ctx, c); ctx.set_line_width(lw)
        ctx.move_to(xs[0], ys[0])
        for xx, yy in zip(xs[1:], ys[1:]):
            ctx.line_to(xx, yy)
        ctx.stroke(); ctx.restore()
    text(ctx, "श्रुति", "tiro", 130, HALDI, 150, 290, alpha=eo(ph(b, 28, 1)))
    text(ctx, "śruti — that which is heard", "fri", 36, PAPER, 470, 280, alpha=ph(b, 28.5, 1))
    # braid
    idx = int(cl(b - 30, 0, 8))
    slots = {0: (690, 800), 1: (1230, 800)}
    cur = PAIRS[idx] if b >= 30 else PAIRS[0]
    prev = PAIRS[idx - 1] if (b >= 31 and idx > 0) else None
    tp = eio(ph(b - int(b), 0, 0.45)) if (b >= 31 and b < 39) else 1.0
    appear = eo(ph(b, 28.8, 1.0))
    for word in set(cur) | (set(prev) if prev else set()):
        if word in cur:
            tx, ty = slots[cur.index(word)]
        else:
            tx, ty = slots[prev.index(word)][0], 1250
        if prev and word in prev:
            sx, sy = slots[prev.index(word)]
        elif prev:
            sx, sy = tx, 1250
        else:
            sx, sy = tx, ty + 400 * (1 - appear)
        x = lerp(sx, tx, tp)
        y = lerp(sy, ty, tp)
        if prev and word in prev and word in cur and sx != tx:
            y += (-110 if tx < sx else 110) * math.sin(PI * tp)
        ctx.save(); ctx.translate(REG[0] * 1.6, REG[1] * 1.6); ctx.set_operator(cairo.OPERATOR_SCREEN)
        rgba(ctx, RANI, 0.8); ctx.rectangle(x - 225, y - 78, 450, 156); ctx.fill(); ctx.restore()
        rgba(ctx, PAPER); ctx.rectangle(x - 225, y - 78, 450, 156); ctx.fill()
        dv, tr = VED[word]
        text(ctx, dv, "tiro", 72, INDIGO, x, y + 12, ax=0.5)
        text(ctx, tr, "tiroi", 30, SINDOOR, x, y + 58, ax=0.5)
    # ticker
    toks = ["ab", "ba", "ab", "bc", "cb", "bc", "cd", "dc", "cd"]
    tot = sum(tw(t_, "monob", 34) for t_ in toks) + 30 * 8
    x = 960 - tot / 2
    ta = ph(b, 29.5, 1)
    for i, t_ in enumerate(toks):
        on = b >= 30 and i == idx
        c = HALDI if on else PAPER
        ww = text(ctx, t_, "monob", 34, c, x, 640, alpha=ta * (1 if on else (0.85 if i < idx else 0.35)))
        if on:
            rgba(ctx, HALDI); ctx.rectangle(x, 652, ww, 4); ctx.fill()
        x += ww + 30
    text(ctx, "JAṬĀ-PĀṬHA · every pair recited forward, back, forward — a braid that lets no syllable slip",
         "mono", 18, PAPER, 960, 590, ax=0.5, alpha=ta * 0.8)
    caption(ctx, "Ṛgveda · c. 1500 BCE · carried by memory, not ink — for over 3,000 years", PAPER, b, 30,
            y=975)
    return PAPER


KA_DESC = [("क", "tiro", "DEVANAGARI"), ("க", "tamil", "TAMIL"), ("ক", "bengali", "BENGALI"), ("ก", "thai", "THAI"),
           ("ཀ", "tibetan", "TIBETAN")]
BRAHMI_LET = "𑀅𑀆𑀇𑀈𑀉𑀊𑀏𑀐𑀑𑀒𑀓𑀔𑀕𑀖𑀗𑀘𑀙𑀚𑀛𑀜𑀝𑀞𑀟𑀠"


def s_brahmi(ctx, b, f):
    bg(ctx, HALDI)
    lb = b - 40
    ang = 0.22 * lb + 0.035 * lb ** 2
    sc = eo(ph(b, 40, 1.0))
    riso(ctx, lambda c: chakra(ctx, 330, 570, 420 * sc, ang, c), INDIGO, RANI, k=1.6)
    text(ctx, "𑀥𑀁𑀫", "brahmi", 120, SINDOOR, 860, 210, alpha=eo(ph(b, 40.5, 1)), op=cairo.OPERATOR_MULTIPLY)
    text(ctx, "dhaṃma — cut into Aśoka's pillars and rocks", "mono", 19, INK, 1110, 180, alpha=ph(b, 41, 1))
    fade = 1 - 0.8 * ph(b, 46, 1)
    for i, ch in enumerate(BRAHMI_LET):
        p = ph(b, 40.5 + i * 0.22, 0.25)
        if p <= 0:
            continue
        x = 930 + (i % 6) * 150
        y = 340 + (i // 6) * 120
        text(ctx, ch, "brahmi", 84, INDIGO, x, y, ax=0.5, ay=0.5, sc=1 + 0.8 * (1 - eo(p)), alpha=cl(p * 2) * fade)
    # lineage
    kp = back(ph(b, 46, 0.5))
    if kp > 0:
        riso(ctx, lambda c: text(ctx, "𑀓", "brahmi", 330, c, 1110, 600, ax=0.5, ay=0.5, sc=kp), INDIGO, RANI, k=1.4)
        text(ctx, "ka — one letter, many scripts", "mono", 19, INK, 1110, 800, ax=0.5, alpha=ph(b, 46.5, 1))
        for k, (g, fn, lab) in enumerate(KA_DESC):
            ty = 250 + k * 150
            rp = ph(b, 46.6 + k * 0.9, 0.6)
            if rp <= 0:
                continue
            pts = []
            for s in np.linspace(0, 1, 40):
                x0, y0, x1, y1 = 1230, 600, 1500, ty
                bx_ = (1 - s) ** 3 * x0 + 3 * (1 - s) ** 2 * s * 1380 + 3 * (1 - s) * s ** 2 * 1380 + s ** 3 * x1
                by_ = (1 - s) ** 3 * y0 + 3 * (1 - s) ** 2 * s * y0 + 3 * (1 - s) * s ** 2 * y1 + s ** 3 * y1
                pts.append((bx_, by_))
            pts = np.array(pts)
            rgba(ctx, SINDOOR); ctx.set_line_width(4)
            path_partial(ctx, pts, cumlen(pts), eo(rp)); ctx.stroke()
            gp = back(ph(b, 46.6 + k * 0.9 + 0.5, 0.4))
            if gp > 0:
                text(ctx, g, fn, 96, INDIGO, 1575, ty, ax=0.5, ay=0.5, sc=gp)
                text(ctx, lab, "mono", 17, INK, 1650, ty + 8, alpha=cl(gp))
    caption(ctx, "c. 250 BCE · Aśoka's edicts in Brahmi — ancestor of most scripts of South & Southeast Asia",
            INK, b, 41, y=975)
    return INK


def s_arya(ctx, b, f):
    bg(ctx, NIGHT)
    lb = b - 52
    z = 1 + 0.35 * eio(ph(b, 60, 4))
    ctx.save(); ctx.translate(960, 540); ctx.scale(z, z); ctx.translate(-960, -540)
    trail = 0.06 + 0.1 * lb + 0.035 * lb ** 2
    rot = 0.05 * lb
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for (r, t0, lw, c) in STARS:
        rgba(ctx, c, 0.55); ctx.set_line_width(lw)
        ctx.arc(960, 540, r, t0 + rot, t0 + rot + min(trail, 6.2) * (0.6 + 0.4 * (lw / 2.6)))
        ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    # pi spiral
    n = int(len(PI_DIGITS) * eio(ph(b, 52.5, 9)))
    sp = -0.12 * lb
    cs, sn = math.cos(sp), math.sin(sp)
    for i in range(n):
        x, y, th = PI_POS[i]
        xx, yy = 960 + x * cs - y * sn, 540 + x * sn + y * cs
        text(ctx, PI_DIGITS[i], "monob", 21, HALDI if i % 7 == 0 else PAPER, xx, yy, ax=0.5, ay=0.5,
             rot=th + sp + PI / 2, alpha=0.9)
    # earth
    R = 150 * eo(ph(b, 52, 1))
    if R > 1:
        ctx.save(); ctx.translate(960, 540); ctx.rotate(math.radians(23.4))
        rgba(ctx, INDIGO); ctx.arc(0, 0, R, 0, 2 * PI); ctx.fill()
        er = 0.9 * lb + 0.12 * lb ** 2
        ctx.set_line_width(2)
        for k in range(12):
            lam = k * PI / 6 + er
            if math.cos(lam) <= 0:
                continue
            rgba(ctx, HALDI, 0.4 + 0.6 * math.cos(lam))
            for j, phi in enumerate(np.linspace(-PI / 2, PI / 2, 30)):
                x, y = R * math.cos(phi) * math.sin(lam), -R * math.sin(phi)
                (ctx.move_to if j == 0 else ctx.line_to)(x, y)
            ctx.stroke()
        rgba(ctx, HALDI, 0.7)
        for phi in (-PI / 3, -PI / 6, 0, PI / 6, PI / 3):
            yy = -R * math.sin(phi); hw = R * math.cos(phi)
            ctx.move_to(-hw, yy); ctx.line_to(hw, yy)
        ctx.stroke()
        rgba(ctx, PAPER); ctx.set_line_width(3); ctx.arc(0, 0, R, 0, 2 * PI); ctx.stroke()
        ctx.set_dash([8, 8]); ctx.move_to(0, -R - 90); ctx.line_to(0, R + 90); ctx.stroke(); ctx.set_dash([])
        ctx.restore()
    ctx.restore()
    ctx.set_source(cairo.LinearGradient(0, 780, 0, 1080))
    g_ = cairo.LinearGradient(0, 760, 0, 1000); g_.add_color_stop_rgba(0, *NIGHT, 0); g_.add_color_stop_rgba(0.45, *NIGHT, 0.92)
    g_.add_color_stop_rgba(1, *NIGHT, 0.95); ctx.set_source(g_); ctx.rectangle(0, 760, W, 320); ctx.fill()
    text(ctx, "आर्यभट", "tiro", 120, PAPER, 150, 300, alpha=eo(ph(b, 52.5, 1)))
    text(ctx, "Āryabhaṭa", "fri", 40, HALDI, 155, 355, alpha=ph(b, 53, 1))
    riso(ctx, lambda c: text(ctx, "π ≈ 3.1416", "anton", 120, c, W - 110, 880, ax=1, alpha=ph(b, 55, 1)),
         HALDI, RANI, dark=True, k=1.5)
    text(ctx, "62832 ÷ 20000 — his value, correct to four places", "mono", 19, PAPER, W - 110, 920, ax=1,
         alpha=ph(b, 55.5, 1))
    caption(ctx, "Āryabhaṭīya · 499 CE · the stars stand still — it is the Earth that turns", PAPER, b, 53,
            y=975)
    fl = ph(b, 63.2, 0.8)
    if fl > 0:
        rgba(ctx, WHITE, fl ** 2); ctx.paint()
    return PAPER


SUNYA_PAL = [(RANI, INDIGO, HALDI, INDIGO), (INDIGO, HALDI, RANI, PAPER), (HALDI, INDIGO, SINDOOR, INDIGO),
             (NIGHT, RANI, HALDI, PAPER)]


def s_sunya(ctx, b, f):
    bar = int((b - 64) // 4) % 4
    bgc, zc, acc, tc = SUNYA_PAL[bar]
    bg(ctx, bgc)
    dark = bgc in (INDIGO, NIGHT)
    kick = pulse(b, 9)
    ctx.save()
    ctx.translate(7 * kick * math.sin(f * 1.7), 6 * kick * math.cos(f * 2.3))
    # sierpinski / meru-prastara
    nrf = 2 + (b - 64) * 4.2
    nr = int(min(64, nrf))
    spc = 720 / max(min(nrf, 64), 6)
    ax_, ay_ = 1330, 170
    for r_ in range(nr):
        rp = ph(nrf, r_, 1.0)
        for k in range(r_ + 1):
            v = PASCAL[r_][k]
            x = ax_ + (k - r_ / 2) * spc
            y = ay_ + r_ * spc * 0.866
            rad = spc * 0.44 * back(rp)
            if rad <= 0.3:
                continue
            ctx.arc(x, y, rad, 0, 2 * PI)
            if v % 2:
                rgba(ctx, acc); ctx.fill()
            else:
                rgba(ctx, zc, 0.45); ctx.set_line_width(max(0.6, spc * 0.03)); ctx.stroke()
            if spc > 44:
                text(ctx, str(v), "monob", int(spc * 0.3), bgc if v % 2 else zc, x, y, ax=0.5, ay=0.5, alpha=cl(rp))
    text(ctx, "MERU-PRASTĀRA · 'the staircase of Mount Meru' — odd numbers lit", "mono", 18, tc, ax_, 120,
         ax=0.5, alpha=ph(b, 65, 1))
    # zero
    zs = (1 + 1.6 * (1 - eo(ph(b, 64, 0.5)))) * (1 + 0.04 * kick)
    riso(ctx, lambda c: text(ctx, "0", "frb", 860, c, 560, 560, ax=0.5, ay=0.5, sc=zs,
                             rot=0.04 * math.sin(b * PI / 2)), zc, acc, dark=dark, k=2.2)
    text(ctx, "शून्य", "tiro", 140, acc if not dark else PAPER, 770, 930, ax=0.5, rot=-0.08,
         alpha=eo(ph(b, 64.5, 0.6)))
    ctx.restore()
    # pingala
    n = int(b - 64) % 16
    pa = ph(b, 66, 1)
    text(ctx, "PIṄGALA · c. 200 BCE · metres as long/short syllables — a binary count", "mono", 18, tc, 1000,
         860, alpha=pa)
    for i in range(4):
        bit = (n >> (3 - i)) & 1
        x = 1030 + i * 95
        text(ctx, "।" if bit else "ऽ", "tiro", 78, tc, x, 945, ax=0.5, alpha=pa)
        text(ctx, str(bit), "monob", 24, acc if not dark else HALDI, x, 985, ax=0.5, alpha=pa)
    text(ctx, "= %d" % n, "anton", 64, tc, 1440, 960, alpha=pa)
    caption(ctx, "628 CE · Brahmagupta writes the rules of zero:  a − a = 0,  a × 0 = 0", tc, b, 66, x=110, y=178, size=21)
    return tc


def s_sikhara(ctx, b, f):
    bg(ctx, SINDOOR)
    flash = 0.0
    for s in (89.5, 90.75):
        if b >= s:
            flash = max(flash, math.exp(-(b - s) * 6))
    ctx.save()
    sc = 1 + 0.03 * flash
    ctx.translate(960, 800); ctx.scale(sc, sc); ctx.translate(-960, -800)
    temple(ctx, 960, 800, 360, 560, 0, b, 80.2, 3)
    ctx.restore()
    # ground + stepwell
    rgba(ctx, INDIGO); ctx.rectangle(0, 800, W, 4); ctx.fill()
    for k in range(7):
        p = ph(b, 85.5 + k * 0.3, 0.3)
        if p <= 0:
            continue
        wdt = 820 - k * 105
        y0 = 812 + k * 30
        rgba(ctx, PAPER, p); ctx.rectangle(960 - wdt / 2, y0, wdt, 28); ctx.fill()
        rgba(ctx, INDIGO, p); ctx.set_line_width(2)
        n = int(wdt // 48)
        for i in range(n):
            x = 960 - wdt / 2 + i * wdt / n
            ctx.move_to(x, y0 + 26); ctx.line_to(x + wdt / n / 2, y0 + 3); ctx.line_to(x + wdt / n, y0 + 26)
        ctx.stroke()
    wp = ph(b, 87.6, 0.5)
    if wp > 0:
        rgba(ctx, MOR, wp); ctx.rectangle(960 - 90, 812 + 7 * 30, 180, 22); ctx.fill()
    if flash > 0:
        ctx.set_operator(cairo.OPERATOR_SCREEN); rgba(ctx, HALDI, 0.55 * flash); ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
    text(ctx, "शिखर", "tiro", 160, PAPER, 140, 370, alpha=eo(ph(b, 80, 1)))
    riso(ctx, lambda c: text(ctx, "ŚIKHARA", "anton", 96, c, 145, 480, alpha=eo(ph(b, 80.5, 1))), INDIGO, HALDI)
    text(ctx, "a tower built of", "fri", 40, PAPER, 148, 560, alpha=ph(b, 81.5, 1))
    text(ctx, "smaller towers", "fri", 40, PAPER, 148, 606, alpha=ph(b, 82, 1))
    text(ctx, "built of smaller towers…", "fri", 40, PAPER, 148, 652, alpha=ph(b, 84, 1))
    text(ctx, "fractal geometry,", "fri", 44, HALDI, W - 120, 300, ax=1, alpha=ph(b, 86, 1))
    text(ctx, "cut in stone", "fri", 44, HALDI, W - 120, 350, ax=1, alpha=ph(b, 86.3, 1))
    text(ctx, "↓ Chand Baori, c. 800 CE", "mono", 19, PAPER, 1420, 880, alpha=ph(b, 87, 1))
    text(ctx, "13 storeys of steps down to water", "mono", 19, PAPER, 1420, 910, alpha=ph(b, 87.3, 1))
    caption(ctx, "Khajuraho · c. 1030 CE", PAPER, b, 81, x=148, y=730, size=19)
    return PAPER


def s_kolam(ctx, b, f):
    if b < 100:
        bg(ctx, INDIGO)
        for i, (x, y) in enumerate(KOL_DOTS):
            p = back(ph(b, 92 + i * 0.03, 0.4))
            if p > 0:
                rgba(ctx, PAPER); ctx.arc(x, y, 7 * p, 0, 2 * PI); ctx.fill()
        fr = eio(ph(b, 92.6, 6.8))
        ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        done = ph(b, 99.4, 0.4)
        for c, lw, off, op in ((RANI, 7, 1.6, cairo.OPERATOR_SCREEN), (PAPER if done == 0 else HALDI, 6, 0, None)):
            ctx.save()
            if op:
                ctx.set_operator(op)
            ctx.translate(REG[0] * off, REG[1] * off)
            rgba(ctx, c, 0.85 if op else 1); ctx.set_line_width(lw)
            e = path_partial(ctx, KOL, KOL_CUM, fr); ctx.stroke(); ctx.restore()
        if e is not None and fr < 1:
            rgba(ctx, HALDI); ctx.arc(e[0], e[1], 12 + 5 * pulse(b, 5), 0, 2 * PI); ctx.fill()
            rgba(ctx, HALDI, 0.25); ctx.arc(e[0], e[1], 30, 0, 2 * PI); ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        text(ctx, "கோலம்", "tamil", 96, HALDI, 110, 330, alpha=eo(ph(b, 92.3, 1)))
        text(ctx, "kolam", "fri", 44, PAPER, 115, 395, alpha=ph(b, 93, 1))
        text(ctx, "7 × 5 dots", "mono", 20, PAPER, W - 110, 400, ax=1, alpha=ph(b, 95, 1))
        text(ctx, "gcd(7, 5) = 1", "mono", 20, PAPER, W - 110, 430, ax=1, alpha=ph(b, 95.5, 1))
        text(ctx, "→ a single closed line", "mono", 20, HALDI, W - 110, 460, ax=1, alpha=ph(b, 96, 1))
        caption(ctx, "one unbroken line around a field of dots — drawn in rice flour at the threshold, every dawn",
                PAPER, b, 93, y=975, size=20)
        return PAPER
    bg(ctx, PAPER)
    text(ctx, "…and the world kept the words", "fri", 54, INK, 110, 215, alpha=ph(b, 100, 0.6))
    for i, ((wd, ety), (x, y, rot, col)) in enumerate(zip(WORDS, WORD_LAYOUT)):
        p = ph(b, 100 + i * 0.45, 0.22)
        if p <= 0:
            continue
        size = int(min(118, 118 * 350 / tw(wd, "anton", 118)))
        s = 1 + 0.6 * (1 - eo(p))
        riso(ctx, lambda c: text(ctx, wd, "anton", size, c, x, y, rot=rot, sc=s, alpha=cl(p * 2)), col, HALDI, k=1.4)
        text(ctx, ety, "mono", 17, INK, x + 4, y + 30, rot=rot, alpha=cl(p * 2) * 0.85)
    caption(ctx, "c. 1700 · Indian cottons — calico, chintz — traded across three continents", INK, b, 100.5,
            y=985)
    return INK


def orbit_pts(C, a, q, ang, t0=0.0, t1=2 * PI, n=140):
    e = 1 - q / a
    th = np.linspace(t0, t1, n)
    r = a * (1 - e * e) / (1 + e * np.cos(th))
    return np.stack([C[0] + r * np.cos(ang + th), C[1] + r * np.sin(ang + th)], 1)


EARTH = np.array([430.0, 650.0]); MOON = np.array([1480.0, 390.0])
_phi = math.atan2(*(MOON - EARTH)[::-1])
_segs = []
for a in (150, 215, 300, 400):
    _segs.append(orbit_pts(EARTH, a, 92, _phi + PI))
_D = np.hypot(*(MOON - EARTH))
_segs.append(orbit_pts(EARTH, (92 + _D - 70) / 2, 92, _phi + PI, 0, PI * 0.985, 120))
_P = _segs[-1][-1]
_d = math.atan2(*(_P - MOON)[::-1])
for Ra in (np.hypot(*(_P - MOON)), 170, 140):
    qm = 104
    a = (Ra + qm) / 2
    _segs.append(orbit_pts(MOON, a, qm, _d + PI, PI, 3 * PI, 120))
_last = _segs[-1][-1]
_segs.append(np.linspace(_last, MOON + np.array([0, 90]), 20))
TRAJ = np.vstack(_segs)
TRAJ_CUM = cumlen(TRAJ)


def lander(ctx, x, y, s=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rgba(ctx, INDIGO); ctx.set_line_width(4)
    for dx in (-48, 48):
        ctx.move_to(dx * 0.5, -30); ctx.line_to(dx, 0); ctx.stroke()
        ctx.move_to(dx - 12, 0); ctx.line_to(dx + 12, 0); ctx.stroke()
    ctx.rectangle(-38, -78, 76, 50); rgba(ctx, HALDI); ctx.fill_preserve(); rgba(ctx, INDIGO); ctx.stroke()
    ctx.move_to(0, -78); ctx.line_to(0, -104); ctx.stroke()
    ctx.arc(0, -108, 6, 0, 2 * PI); rgba(ctx, SINDOOR); ctx.fill()
    ctx.set_source(halftone(INDIGO, 7, 1.6, 0.3)); ctx.rectangle(-30, -70, 60, 34); ctx.fill()
    ctx.restore()


def s_chandra(ctx, b, f):
    bg(ctx, NIGHT)
    for (x, y, r, p0) in SKY:
        rgba(ctx, PAPER, 0.35 + 0.35 * math.sin(b * 2 + p0)); ctx.arc(x, y, r, 0, 2 * PI); ctx.fill()
    if b < 112:
        i = int(b - 108)
        fr = b - 108 - i
        d = "४३२१"[i]
        riso(ctx, lambda c: text(ctx, d, "tiro", 640, c, 960, 560, ax=0.5, ay=0.5, sc=1.25 - 0.25 * eo(fr),
                                 alpha=1 - 0.3 * fr), HALDI, RANI, dark=True, k=2)
        text(ctx, "T − %d" % (4 - i), "monob", 28, PAPER, 960, 900, ax=0.5)
        return PAPER
    if b < 115.5:
        rgba(ctx, PAPER, 0.12); ctx.set_line_width(1.5)
        ctx.move_to(*TRAJ[0])
        for p in TRAJ[1:]:
            ctx.line_to(*p)
        ctx.stroke()
        rgba(ctx, MOR); ctx.arc(*EARTH, 64, 0, 2 * PI); ctx.fill()
        rgba(ctx, PAPER); ctx.set_line_width(3); ctx.arc(*EARTH, 64, 0, 2 * PI); ctx.stroke()
        rgba(ctx, PAPER); ctx.arc(*MOON, 90, 0, 2 * PI); ctx.fill()
        ctx.set_source(halftone(INDIGO, 9, 2.0)); ctx.arc(MOON[0] + 25, MOON[1] + 5, 88, 0, 2 * PI); ctx.fill()
        fr = eio(ph(b, 112, 3.5))
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        rgba(ctx, SINDOOR); ctx.set_line_width(4)
        e = path_partial(ctx, TRAJ, TRAJ_CUM, fr); ctx.stroke()
        if e is not None:
            rgba(ctx, HALDI, 0.3); ctx.arc(e[0], e[1], 26, 0, 2 * PI); ctx.fill()
            rgba(ctx, HALDI); ctx.arc(e[0], e[1], 10, 0, 2 * PI); ctx.fill()
        text(ctx, "orbit-raising burns", "mono", 18, PAPER, 250, 880, alpha=ph(b, 112.3, 0.5))
        text(ctx, "trans-lunar injection →", "mono", 18, PAPER, 820, 700, alpha=ph(b, 114.2, 0.5))
        text(ctx, "lunar capture", "mono", 18, PAPER, 1580, 580, alpha=ph(b, 114.8, 0.5))
        text(ctx, "चन्द्रयान-३", "tiro", 90, HALDI, 110, 300, alpha=ph(b, 112, 0.6))
        text(ctx, "(not to scale)", "mono", 15, PAPER, W - 110, 960, ax=1, alpha=0.6)
        return PAPER
    # surface
    ctx.save()
    rgba(ctx, PAPER); ctx.arc(960, 2250, 1500, 0, 2 * PI); ctx.fill()
    ctx.arc(960, 2250, 1500, 0, 2 * PI); ctx.clip()
    for (x, y, r) in CRATERS:
        ctx.save(); ctx.translate(960 + x, 750 + y + r * 0.2); ctx.scale(1, 0.32)
        ctx.arc(0, 0, r, 0, 2 * PI); ctx.restore()
        ctx.set_source(halftone(INDIGO, 8, 1.9, 0.2)); ctx.fill_preserve()
        rgba(ctx, INDIGO, 0.6); ctx.set_line_width(2); ctx.stroke()
    ctx.restore()
    rgba(ctx, MOR); ctx.arc(1640, 200, 42, 0, 2 * PI); ctx.fill()
    rgba(ctx, NIGHT); ctx.arc(1662, 190, 40, 0, 2 * PI); ctx.fill()
    ly = lerp(260, 752, eo(ph(b, 115.5, 0.5)))
    if b < 116:
        rgba(ctx, HALDI, 0.5); ctx.move_to(930, ly); ctx.line_to(960, ly + 60); ctx.line_to(990, ly); ctx.fill()
    lander(ctx, 960, ly)
    if b >= 116:
        age = b - 116
        rx = 60 + age * 520
        rgba(ctx, PAPER, max(0, 0.8 - age * 0.5)); ctx.set_line_width(6)
        ctx.save(); ctx.translate(960, 756); ctx.scale(1, 0.16); ctx.arc(0, 0, rx, 0, 2 * PI); ctx.restore()
        ctx.stroke()
        p = back(ph(b, 116.1, 0.5))
        riso(ctx, lambda c: text(ctx, "23 · 08 · 2023", "anton", 180, c, 960, 330, ax=0.5, sc=p),
             HALDI, RANI, dark=True, k=1.8)
        text(ctx, "चन्द्रयान-३", "tiro", 80, PAPER, 960, 440, ax=0.5, alpha=ph(b, 116.5, 0.6))
        text(ctx, "Chandrayaan-3 — the first soft landing near the Moon's south pole", "mono", 24, PAPER, 960,
             500, ax=0.5, alpha=ph(b, 117, 0.8))
        fl = 1 - ph(b, 116, 0.35)
        if fl > 0:
            rgba(ctx, WHITE, fl); ctx.paint()
    return PAPER


BEAD_C = [INDIGO, HALDI, SINDOOR, MOR, RANI, INDIGO, HALDI, NIGHT]
BEAD_L = ["−2600", "−1500", "−250", "499", "628", "1030", "every dawn", "2023"]


def bead_icon(ctx, i, x, y, fg):
    rgba(ctx, fg); ctx.set_line_width(3)
    if i == 0:
        for a_ in range(3):
            for c_ in range(3):
                ctx.rectangle(x - 33 + c_ * 24, y - 33 + a_ * 24, 18, 18)
        ctx.fill()
    elif i == 1:
        for k, xx in enumerate(range(-40, 41, 4)):
            (ctx.move_to if k == 0 else ctx.line_to)(x + xx, y + 22 * math.sin(xx * 0.16))
        ctx.stroke()
    elif i == 2:
        chakra(ctx, x, y, 44, 0, fg)
    elif i == 3:
        ctx.arc(x, y, 40, 0, 2 * PI); ctx.stroke()
        ctx.save(); ctx.translate(x, y); ctx.scale(0.45, 1); ctx.arc(0, 0, 40, 0, 2 * PI); ctx.restore(); ctx.stroke()
        ctx.move_to(x - 40, y); ctx.line_to(x + 40, y); ctx.stroke()
    elif i == 4:
        text(ctx, "0", "frb", 110, fg, x, y, ax=0.5, ay=0.5)
    elif i == 5:
        spire(ctx, x, y + 38, 60, 72, HALDI, fg)
    elif i == 6:
        ctx.move_to(x + MINI_KOL[0][0] * 13, y + MINI_KOL[0][1] * 13)
        for p in MINI_KOL[1:]:
            ctx.line_to(x + p[0] * 13, y + p[1] * 13)
        ctx.stroke()
    elif i == 7:
        rgba(ctx, PAPER); ctx.arc(x, y, 40, 0, 2 * PI); ctx.fill()
        rgba(ctx, NIGHT); ctx.arc(x + 18, y - 8, 36, 0, 2 * PI); ctx.fill()


def s_outro(ctx, b, f):
    if b < 132:
        bg(ctx, PAPER)
        wa = eo(ph(b, 120, 1.2))
        xe = lerp(-20, W + 20, wa)

        def ty(x):
            return 460 + 20 * math.sin(x * 0.008 + b * 1.1)
        rgba(ctx, SINDOOR); ctx.set_line_width(5)
        for k, x in enumerate(np.arange(-20, xe, 10)):
            (ctx.move_to if k == 0 else ctx.line_to)(x, ty(x))
        ctx.stroke()
        for i in range(8):
            p = ph(b, 120.3 + i * 0.95, 0.5)
            if p <= 0:
                continue
            x = 205 + i * 216
            y = ty(x) - 260 * (1 - back(p))
            rgba(ctx, INK, 0.15); ctx.arc(x + 6, y + 8, 70, 0, 2 * PI); ctx.fill()
            rgba(ctx, BEAD_C[i]); ctx.arc(x, y, 70, 0, 2 * PI); ctx.fill()
            bead_icon(ctx, i, x, y, INK if BEAD_C[i] in (HALDI,) else PAPER)
            text(ctx, BEAD_L[i], "mono", 17, INK, x, y + 108, ax=0.5, alpha=cl(p * 2))
            text(ctx, CH[i + 1][1], "monob", 15, SINDOOR, x, y - 92, ax=0.5, alpha=cl(p * 2))
        tp = back(ph(b, 128, 0.6))
        riso(ctx, lambda c: text(ctx, "सूत्र", "tiro", 230, c, 960, 850, ax=0.5, sc=tp), INDIGO, RANI, k=1.5)
        text(ctx, "five thousand years · one unbroken thread", "fri", 44, INK, 960, 935, ax=0.5,
             alpha=ph(b, 129, 1))
        return INK
    bg(ctx, NIGHT)
    age = b - 132
    for k in range(3):
        a_ = age - k * 0.6
        if 0 <= a_ < 3:
            rgba(ctx, SINDOOR, 0.4 * (1 - a_ / 3)); ctx.set_line_width(2.5)
            ctx.arc(960, 540, 30 + a_ * 300, 0, 2 * PI); ctx.stroke()
    rgba(ctx, SINDOOR); ctx.arc(960, 540, 16 + 6 * math.exp(-age * 3), 0, 2 * PI); ctx.fill()
    text(ctx, "SŪTRA — a film in one thread", "mono", 20, PAPER, 960, 660, ax=0.5, alpha=ph(b, 133, 1) * 0.85)
    text(ctx, "every frame and every note made in code", "mono", 15, PAPER, 960, 695, ax=0.5,
         alpha=ph(b, 133.6, 1) * 0.55)
    return PAPER


SCENES = [(0, s_intro), (12, s_sindhu), (28, s_sruti), (40, s_brahmi), (52, s_arya), (64, s_sunya),
          (80, s_sikhara), (92, s_kolam), (108, s_chandra), (120, s_outro)]
WIPES = [(12, SINDOOR, HALDI), (28, HALDI, SINDOOR), (40, INDIGO, RANI), (52, RANI, INDIGO), (80, INDIGO, HALDI),
         (92, HALDI, INDIGO), (108, SINDOOR, INDIGO), (120, HALDI, SINDOOR)]
GLITCH = [(51.5, 52.15), (107.5, 108.15), (63.5, 63.8)]


def wipe(ctx, b, B, c1, c2):
    p = b - (B - 0.5)
    if p < 0 or p > 1:
        return
    step = 54

    def edge(X, down):
        pts = []
        ys = range(0, H + step, step)
        for yi in ys:
            off = 34 * abs(((yi // step) % 10) - 5)
            pts += [(X + off, yi), (X + off, yi + step)]
        return pts if down else pts[::-1]
    for c, lag in ((c1, 0.0), (c2, 0.14)):
        q = cl((p - lag) / 0.86)
        R = -400 + (W + 800) * eio(min(q * 2, 1))
        L = -400 + (W + 800) * eio(max(q * 2 - 1, 0))
        if R - L < 1:
            continue
        pts = edge(R, True) + edge(L, False)
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.close_path(); rgba(ctx, c); ctx.fill()


def glitch(surf, f):
    arr = np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())
    r = np.random.default_rng(f)
    for _ in range(9):
        y0 = int(r.integers(0, H - 40)); hh = int(r.integers(8, 90))
        arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(r.integers(-160, 160)), axis=1)
    ch = int(r.integers(0, 3))
    arr[..., ch] = np.roll(arr[..., ch], 14, axis=1)
    surf.mark_dirty()


def render(f, surf):
    T = f / FPS
    b = T / BEAT
    r = np.random.default_rng(f // 3)
    REG[0], REG[1] = 4 + 3 * r.random(), 3 + 3 * r.random()
    ctx = cairo.Context(surf)
    fn = SCENES[0][1]
    for s, fn_ in SCENES:
        if b >= s:
            fn = fn_
    fg = fn(ctx, b, min(f, NF - 1))
    ctx = cairo.Context(surf)
    for B, c1, c2 in WIPES:
        wipe(ctx, b, B, c1, c2)
    # drop flash
    if 64 <= b < 64.5:
        rgba(ctx, WHITE, 1 - ph(b, 64, 0.5)); ctx.paint()
    if 100 <= b < 100.3:
        rgba(ctx, HALDI, 1 - ph(b, 100, 0.3)); ctx.paint()
    hud(ctx, b, fg)
    g = GRAIN[(f // 2) % 3][0]
    ctx.set_operator(cairo.OPERATOR_OVERLAY); ctx.set_source_surface(g, 0, 0); ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    if b > 134.6:
        rgba(ctx, (0, 0, 0), ph(b, 134.6, 3.0)); ctx.paint()
    surf.flush()
    for g0, g1 in GLITCH:
        if g0 <= b < g1:
            glitch(surf, f)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "png":
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        for fr in map(int, sys.argv[2:]):
            render(fr, surf)
            surf.write_to_png("frames/f%05d.png" % fr)
    else:
        a, bnd, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s",
                              "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                              "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", out], stdin=subprocess.PIPE)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        for fr in range(a, bnd):
            render(fr, surf)
            p.stdin.write(bytes(surf.get_data()))
            if fr % 150 == 0:
                print(out, fr, flush=True)
        p.stdin.close(); p.wait()
