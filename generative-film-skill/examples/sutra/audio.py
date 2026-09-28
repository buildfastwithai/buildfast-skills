"""SUTRA soundtrack — fully synthesised. Tanpura drone, tabla, sitar-like plucks,
electronic drop, rocket riser. 96 BPM, Sa = C#, raga-flavoured minor pentatonic."""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
BPM = 96
BEAT = 60 / BPM
TOTAL_BEATS = 136
DUR = TOTAL_BEATS * BEAT + 2.0
N = int(DUR * SR)
SA = 138.59  # C#3
rng = np.random.default_rng(7)

buses = {k: np.zeros((2, N)) for k in ["drone", "perc", "kick", "bass", "mel", "fx", "pad"]}
send = {"drone": 0.35, "perc": 0.18, "kick": 0.02, "bass": 0.0, "mel": 0.45, "fx": 0.5, "pad": 0.5}


def tb(b):
    return b * BEAT


def add(bus, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l = np.cos((pan + 1) * np.pi / 4) * 1.414
    r = np.sin((pan + 1) * np.pi / 4) * 1.414
    buses[bus][0, i:i + len(sig)] += sig * gain * l
    buses[bus][1, i:i + len(sig)] += sig * gain * r


def tt(d):
    return np.arange(int(d * SR)) / SR


def hz(semi, octv=0, base=SA):
    return base * 2 ** (octv + semi / 12)


# ---------------------------------------------------------------- instruments
def tanpura(f, dur=4.5):
    t = tt(dur)
    y = np.zeros_like(t)
    ph = rng.uniform(0, 2 * np.pi, 60)
    for k in range(1, 48):
        fk = f * k
        if fk > 9000:
            break
        bloom = 0.55 + 0.45 * np.sin(2 * np.pi * t * (0.35 + 0.11 * k) + ph[k])
        env = k ** -0.55 * np.exp(-t / (3.2 / (1 + 0.025 * k))) * bloom
        y += env * (np.sin(2 * np.pi * fk * t + ph[k]) + 0.5 * np.sin(2 * np.pi * fk * 1.0015 * t))
    y *= 1 - np.exp(-t / 0.004)
    return y / np.max(np.abs(y))


def sitar(f0, dur=1.6, f1=None, g0=0.05, gd=0.18, vel=1.0):
    t = tt(dur)
    if f1 is None:
        f = np.full_like(t, f0)
    else:
        s = np.clip((t - g0) / gd, 0, 1)
        s = s * s * (3 - 2 * s)
        f = f0 * (f1 / f0) ** s
    phase = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros_like(t)
    for k in range(1, 30):
        if f0 * k > 11000:
            break
        a = k ** -0.8 * (1.6 if 3 <= k <= 8 else 1.0)
        y += a * np.sin(k * phase) * np.exp(-t * (1.2 + 0.55 * k))
    y = np.tanh(2.2 * y / np.max(np.abs(y))) / np.tanh(2.2)
    click = rng.normal(0, 1, len(t)) * np.exp(-t / 0.002) * 0.3
    y = (y + click) * np.exp(-t / (dur * 0.7)) * vel
    # sympathetic shimmer (taraf)
    sh = 0.05 * np.sin(2 * np.pi * f0 * 2 * t) * np.exp(-t / 1.2) * (1 - np.exp(-t / 0.3))
    return y + sh


def na(pitch=hz(0, 1), dec=0.32, bright=1.0):
    t = tt(0.9)
    y = np.zeros_like(t)
    for k, a in zip([1, 2, 3, 4, 5], [1, 0.6 * bright, 0.45 * bright, 0.3 * bright, 0.2 * bright]):
        y += a * np.sin(2 * np.pi * pitch * k * t) * np.exp(-t / (dec / (1 + 0.6 * (k - 1))))
    n = signal.sosfilt(signal.butter(2, [2500, 6000], "band", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    y += 0.6 * n * np.exp(-t / 0.006)
    return y * 0.5


def tin():
    return na(dec=0.55, bright=0.35)


def te():
    t = tt(0.12)
    n = signal.sosfilt(signal.butter(2, [1500, 5000], "band", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    return (0.5 * n * np.exp(-t / 0.018) + 0.3 * np.sin(2 * np.pi * 320 * t) * np.exp(-t / 0.03)) * 0.7


def ge(f0=68, f1=96, dec=0.75):
    t = tt(1.2)
    s = np.clip(t / 0.28, 0, 1)
    f = f0 + (f1 - f0) * (1 - (1 - s) ** 2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t / dec) * (1 - np.exp(-t / 0.003))
    return y * 0.9


def ka():
    t = tt(0.1)
    n = signal.sosfilt(signal.butter(2, [150, 700], "band", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    return n * np.exp(-t / 0.02) * 1.2


def kick():
    t = tt(0.5)
    f = 48 + 120 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.28)
    y += 0.4 * rng.normal(0, 1, len(t)) * np.exp(-t / 0.003)
    return np.tanh(1.6 * y)


def clap():
    t = tt(0.4)
    n = signal.sosfilt(signal.butter(2, [900, 3000], "band", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    env = np.zeros_like(t)
    for d in [0, 0.011, 0.022]:
        env += np.where(t >= d, np.exp(-(t - d) / 0.008), 0)
    env += 0.6 * np.where(t > 0.03, np.exp(-(t - 0.03) / 0.11), 0)
    return n * env * 0.8


def hat(open_=False):
    t = tt(0.3 if open_ else 0.06)
    n = signal.sosfilt(signal.butter(4, 7000, "high", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    return n * np.exp(-t / (0.08 if open_ else 0.012)) * 0.35


def sub(f, dur):
    t = tt(dur)
    y = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    env = (1 - np.exp(-t / 0.005)) * np.exp(-t / (dur * 1.5))
    rel = np.clip((dur - t) / 0.03, 0, 1)
    return np.tanh(1.3 * y) * env * rel


def bell(f, dur=2.5, idx=2.5):
    t = tt(dur)
    m = idx * np.exp(-t / 0.5) * np.sin(2 * np.pi * f * 3.5 * t)
    return np.sin(2 * np.pi * f * t + m) * np.exp(-t / (dur * 0.35)) * (1 - np.exp(-t / 0.002))


def chant(f, dur, vowel=(700, 1220, 2600)):
    t = tt(dur)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 1.0, 0, 1)
    ph = np.cumsum(f * vib) / SR
    saw = 2 * (ph % 1) - 1
    y = np.zeros_like(t)
    for fm, g in zip(vowel, [1.0, 0.5, 0.25]):
        y += g * signal.sosfilt(signal.butter(2, [fm * 0.85, fm * 1.15], "band", fs=SR, output="sos"), saw)
    a = np.clip(t / 1.2, 0, 1) * np.clip((dur - t) / 1.5, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def pad(freqs, dur):
    t = tt(dur)
    y = np.zeros_like(t)
    for f in freqs:
        for d in (-0.004, 0.0, 0.005):
            ph = (f * (1 + d) * t + rng.uniform()) % 1
            y += 2 * ph - 1
    y = signal.sosfilt(signal.butter(2, 1400, "low", fs=SR, output="sos"), y)
    a = np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 2.0, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def riser(dur, f0=200, f1=2400):
    t = tt(dur)
    n = rng.normal(0, 1, len(t))
    out = np.zeros_like(t)
    seg = int(0.05 * SR)
    for i in range(0, len(t), seg):
        c = f0 * (f1 / f0) ** (i / len(t))
        sos = signal.butter(2, [c * 0.7, min(c * 1.6, 20000)], "band", fs=SR, output="sos")
        out[i:i + seg] = signal.sosfilt(sos, n[i:i + seg])
    f = 110 * 2 ** (3 * (t / dur) ** 2)
    ph = np.cumsum(f) / SR
    tone = 0.3 * (2 * (ph % 1) - 1)
    return (out + tone) * (t / dur) ** 2


def boom(dur=3.0):
    t = tt(dur)
    f = 30 + 45 * np.exp(-t / 0.2)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    n = signal.sosfilt(signal.butter(2, 900, "low", fs=SR, output="sos"), rng.normal(0, 1, len(t)))
    return np.tanh(2 * y) + 0.5 * n * np.exp(-t / 0.35)


# pre-baked strokes
TP = {"P": tanpura(hz(7, -1)), "S": tanpura(hz(0)), "L": tanpura(hz(0, -1))}
STK = {"na": na(), "tin": tin(), "te": te(), "ge": ge(), "ka": ka(), "kick": kick(), "clap": clap(),
       "hat": hat(), "ohat": hat(True)}


def stroke(name, b, g=1.0, pan=0.0):
    t = tb(b)
    if name == "dha":
        add("perc", STK["ge"], t, g * 0.9, -0.15); add("perc", STK["na"], t, g, 0.15)
    elif name == "dhin":
        add("perc", STK["ge"], t, g * 0.9, -0.15); add("perc", STK["tin"], t, g, 0.15)
    elif name in ("na", "ta"):
        add("perc", STK["na"], t, g, 0.2)
    elif name in ("tin", "te", "ka", "ge"):
        add("perc", STK[name], t, g, {"tin": 0.2, "te": 0.3, "ka": -0.3, "ge": -0.15}[name])
    elif name == "-":
        pass


KEHERWA = ["dha", "ge", "na", "te", "na", "ka", "dhin", "na"]  # one cycle per bar (8ths)


def keherwa(b0, b1, g=1.0, fills=True):
    b = b0
    while b < b1 - 1e-6:
        bar_i = int(round((b - b0) / 4))
        for i, s in enumerate(KEHERWA):
            bb = b + i * 0.5
            if bb >= b1:
                break
            stroke(s, bb, g * (1.0 if i % 2 == 0 else 0.8))
        if fills and bar_i % 2 == 1:
            stroke("te", b + 3.25, g * 0.7); stroke("te", b + 3.75, g * 0.6)
        b += 4


def sitar_line(b0, notes, octv=1, g=1.0, pan=0.1):
    for n in notes:
        b, semi = n[0], n[1]
        dur = n[2] if len(n) > 2 else 1.4
        glide = n[3] if len(n) > 3 else None
        f0 = hz(semi, octv)
        f1 = hz(glide, octv) if glide is not None else None
        add("mel", sitar(f0, dur=max(dur, 0.6), f1=f1), tb(b0 + b), g * 0.55, pan)


# ---------------------------------------------------------------- arrangement
# Tanpura cycle on every beat
for b in range(0, 132):
    lvl = 0.30
    if 12 <= b < 28 or 40 <= b < 52 or 64 <= b < 108 or 116 <= b < 120:
        lvl = 0.16
    if b >= 124:
        lvl = 0.30 * max(0.0, (132 - b) / 8)
    add("drone", TP["PSSL"[b % 4]], tb(b), lvl, [-0.4, 0.3, -0.1, 0.4][b % 4])

# Intro: low swell + letter hits
t = tt(tb(12))
swell = np.sin(2 * np.pi * hz(0, -2) * t) * np.clip(t / tb(12), 0, 1) ** 2 * 0.35
add("pad", swell, 0, 1.0)
for i, b in enumerate([4, 5, 6, 7, 8]):
    add("fx", bell(hz([0, 3, 5, 7, 10][i], 2), 2.0), tb(b), 0.18, -0.5 + 0.25 * i)
    stroke("tin", b, 0.7)
add("fx", riser(tb(3), 300, 3000), tb(9), 0.25)
stroke("dha", 12, 1.2)

# SINDHU 12-28
keherwa(12, 28, 0.9)
sitar_line(12, [(2, 7, 1), (3, 10, 1.2, 12), (4, 12, 2.2), (6.5, 10, 0.6), (7, 7, 0.6), (7.5, 5, 0.6),
                (8, 3, 1.8), (10, 0, 0.6), (10.5, 3, 0.6), (11, 5, 0.6), (11.5, 7, 0.6), (12, 10, 1.4, 12),
                (13, 7, 1.0), (14, 3, 1.0), (15, 0, 1.2)])

# SRUTI 28-40 — chant, soft
add("pad", chant(hz(0, 0), tb(12.5)), tb(28), 0.28, -0.2)
add("pad", chant(hz(7, -1), tb(12.5), (500, 900, 2400)), tb(28), 0.2, 0.25)
for b in range(28, 40, 4):
    stroke("dhin", b, 0.6)
for b in range(32, 40):
    stroke("te", b + 0.5, 0.35)
sitar_line(28, [(1, 12, 2.5, 10), (4, 7, 1.5), (5, 5, 1.2, 7), (7, 3, 2.0), (9, 5, 0.8), (9.5, 3, 0.8), (10, 0, 2.2)],
           g=0.8)
add("fx", riser(tb(2), 400, 5000), tb(38), 0.2)

# BRAHMI 40-52 — busier
keherwa(40, 52, 1.0)
for b in np.arange(40, 48, 1):
    add("kick", STK["kick"], tb(b), 0.45 if b % 2 == 0 else 0.0)
for b in np.arange(48, 51.5, 0.25):
    stroke("te" if (b * 4) % 2 else "na", b, 0.5 + 0.12 * (b - 48))
sitar_line(40, [(0, 12, 0.6), (0.5, 10, 0.6), (1, 12, 0.8), (1.75, 7, 0.8), (3, 10, 1.4, 12),
                (4, 5, 0.6), (4.5, 7, 0.6), (5, 10, 0.6), (5.5, 7, 0.6), (6, 5, 0.6), (6.5, 3, 0.6), (7, 0, 1.6, 0)])
add("fx", riser(tb(3.5)), tb(48), 0.28)

# ARYABHATA 52-64 — space
add("pad", pad([hz(0, 0), hz(7, 0), hz(3, 1), hz(10, 0)], tb(12)), tb(52), 0.3)
arp = [12, 10, 7, 3, 15, 12, 10, 7]
for i, b in enumerate(np.arange(52, 62, 0.5)):
    add("fx", bell(hz(arp[i % 8], 2), 1.6, 1.8), tb(b), 0.1, np.sin(i) * 0.7)
for b in (52, 54, 56, 58):
    add("kick", STK["kick"], tb(b), 0.6)
    stroke("ge", b + 0.75, 0.5)
add("fx", riser(tb(4), 150, 6000), tb(60), 0.45)
for b in np.arange(62, 63.75, 0.125):
    add("perc", STK["clap"], tb(b), 0.12 + 0.25 * (b - 62) / 2, 0)

# SUNYA DROP 64-80 & WORDS 100-108 & CHANDRA celebration 116-120
HOOK = [(0, 12, 0.6), (0.5, 10, 0.5), (1, 12, 0.7), (1.5, 15, 0.6), (2, 12, 0.6), (2.75, 10, 0.6), (3.25, 7, 0.8),
        (4, 5, 0.5), (4.5, 7, 0.5), (5, 10, 0.6), (5.5, 7, 0.5), (6, 5, 0.6), (6.5, 3, 0.6), (7, 0, 1.4, 0)]
BASS = [0, -2, -7, -5]


def groove(b0, b1, claps=True, hook=True, fourfloor=True):
    for b in np.arange(b0, b1, 1.0):
        if fourfloor or (b - b0) % 2 == 0:
            add("kick", STK["kick"], tb(b), 0.95)
        if claps and int(b - b0) % 2 == 1:
            add("perc", STK["clap"], tb(b), 0.55)
        add("perc", STK["hat"], tb(b + 0.5), 0.6, 0.3)
        add("perc", STK["hat"], tb(b + 0.75), 0.25, -0.3)
    for i, b in enumerate(np.arange(b0, b1, 4.0)):
        root = BASS[i % 4]
        for s in np.arange(0, 4, 0.5):
            add("bass", sub(hz(root, -1), tb(0.42)), tb(b + s), 0.55 if s % 1 else 0.4)
    keherwa(b0, b1, 0.8)
    if hook:
        for b in np.arange(b0, b1, 8.0):
            sitar_line(b, HOOK, g=1.0)


groove(64, 80)
add("fx", boom(2.5), tb(64), 0.55)

# SIKHARA 80-92 — half-time, tabla featured, tihai landing on 92
groove(80, 88, claps=False, hook=False, fourfloor=False)
sitar_line(80, [(0, 7, 1.0), (1, 10, 0.8), (2, 12, 1.4, 15), (4, 12, 0.8), (5, 10, 0.8), (6, 7, 1.4)], g=0.9)
for b in np.arange(88, 88.75, 0.25):
    stroke("te", b, 0.6)
for s in (88.75, 90.0, 91.25):
    stroke("dha", s, 1.1); stroke("te", s + 0.25, 0.8); stroke("te", s + 0.5, 0.8); stroke("dha", s + 0.75, 1.2)
    add("kick", STK["kick"], tb(s + 0.75), 0.8)
add("fx", boom(2.0), tb(92), 0.35)

# KOLAM 92-100 soft groove, WORDS 100-108 full
groove(92, 100, claps=False, hook=False, fourfloor=False)
sitar_line(92, [(0, 0, 1.0), (1, 3, 1.0), (2, 5, 1.0), (3, 7, 1.2, 10), (4, 7, 1.0), (5, 5, 1.0), (6, 3, 1.0),
                (7, 0, 1.2)], g=0.9)
groove(100, 108)
for b in np.arange(100, 108, 0.5):
    stroke("ka", b, 0.6)

# CHANDRA 108-120 — countdown, launch, landing, celebration
for i, b in enumerate([108, 109, 110, 111]):
    add("fx", bell(hz([12, 10, 7, 3][i], 2), 1.2, 1.2), tb(b), 0.25)
    add("kick", STK["kick"], tb(b), 0.4)
add("fx", riser(tb(4), 80, 4000), tb(112), 0.6)
t = tt(tb(4))
rumble = signal.sosfilt(signal.butter(2, 180, "low", fs=SR, output="sos"), rng.normal(0, 1, len(t))) * np.clip(t / 0.3, 0, 1)
add("fx", rumble * 3.5, tb(112), 0.5)
add("fx", boom(3.0), tb(116), 0.8)
groove(116, 120)
add("fx", riser(tb(1), 400, 4000), tb(119), 0.15)

# OUTRO 120-136
add("pad", chant(hz(0, 0), tb(14)), tb(120), 0.25, -0.2)
add("pad", pad([hz(0, 0), hz(7, 0), hz(3, 1)], tb(14)), tb(120), 0.22)
for i, b in enumerate(range(120, 128)):
    add("fx", bell(hz([0, 3, 5, 7, 10, 12, 15, 19][i], 2), 2.2, 1.5), tb(b), 0.15, -0.7 + 0.2 * i)
sitar_line(120, [(8, 12, 1.6, 10), (9.5, 7, 1.0), (10, 5, 1.0), (10.5, 3, 1.4), (12, 0, 3.0)], g=0.9)
stroke("dha", 132, 1.1)
add("fx", boom(3.0), tb(132), 0.35)

# ---------------------------------------------------------------- mix
# sidechain duck from kick onto bass & drone
kick_env = np.abs(buses["kick"][0])
kick_env = signal.sosfilt(signal.butter(1, 8, "low", fs=SR, output="sos"), kick_env)
kick_env /= kick_env.max() + 1e-9
duck = 1 - 0.7 * np.clip(kick_env * 3, 0, 1)
for k in ("bass", "drone", "pad"):
    buses[k] *= duck

# reverb IR
ir_t = tt(2.8)
ir = np.stack([rng.normal(0, 1, len(ir_t)), rng.normal(0, 1, len(ir_t))]) * np.exp(-ir_t / 0.7)
ir = signal.sosfilt(signal.butter(1, 5000, "low", fs=SR, output="sos"), ir)
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))

gains = {"drone": 0.55, "perc": 0.8, "kick": 0.9, "bass": 0.75, "mel": 0.62, "fx": 0.6, "pad": 0.55}
dry = np.zeros((2, N))
wet_in = np.zeros((2, N))
for k, v in buses.items():
    dry += v * gains[k]
    wet_in += v * gains[k] * send[k]
wet = np.stack([signal.fftconvolve(wet_in[c], ir[c])[:N] for c in range(2)]) * 0.55
mix = dry + wet

# glitch stutters at a few seams
for b, reps in ((51.5, 4), (107.5, 4), (63.5, 2)):
    i0 = int(tb(b) * SR)
    L = int(tb(0.125) * SR)
    seg = mix[:, i0:i0 + L].copy()
    for r in range(reps):
        mix[:, i0 + r * L:i0 + (r + 1) * L] = seg * (1 - 0.15 * r)

# low cut + master
mix = signal.sosfilt(signal.butter(2, 28, "high", fs=SR, output="sos"), mix)
mix /= np.max(np.abs(mix))
mix = np.tanh(1.5 * mix) / np.tanh(1.5)
fade = np.ones(N)
fs_, fe_ = int(tb(133) * SR), int(tb(136) * SR + 1.5 * SR)
fade[fs_:fe_] = np.linspace(1, 0, fe_ - fs_) ** 2
fade[fe_:] = 0
mix *= fade
mix *= 0.89 / np.max(np.abs(mix))
wavfile.write("music.wav", SR, (mix.T * 32767).astype(np.int16))

# per-frame envelope for visuals
FPS = 30
nf = int(DUR * FPS)
spf = SR // FPS
mono = mix.mean(0)
env = np.array([np.sqrt(np.mean(mono[i * spf:(i + 1) * spf] ** 2)) for i in range(nf)])
env /= env.max()
np.save("env.npy", env)
# waveform snapshots for oscilloscope (downsampled 1024 pts per frame)
wave = np.zeros((nf, 512), np.float32)
for i in range(nf):
    seg = mono[i * spf:i * spf + 2048]
    if len(seg) == 2048:
        wave[i] = seg[::4]
np.save("wave.npy", wave)
print("done", DUR, "s", nf, "frames")
