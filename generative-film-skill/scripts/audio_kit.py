"""audio_kit.py — synthesise an original, licence-free soundtrack in numpy/scipy.

    from audio_kit import *
    T = Track(bpm=96, beats=136, root=138.59)          # root = tonic in Hz (C#3 here)
    T.add("drone", drone(T.hz(0)), T.tb(0), 0.3)      # bus, signal, time-in-seconds, gain, pan
    ...
    T.mixdown("music.wav")                            # also writes env.npy / wave.npy for visuals

Everything is placed in BEATS (T.tb(beat) -> seconds) so music and picture share one grid.
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
_rng = np.random.default_rng(7)

# semitone sets — pick one that belongs to the film's culture/mood
SCALES = {
    "raga_bhairavi": [0, 1, 3, 5, 7, 8, 10],
    "raga_yaman": [0, 2, 4, 6, 7, 9, 11],
    "minor_penta": [0, 3, 5, 7, 10],
    "major_penta": [0, 2, 4, 7, 9],
    "hijaz": [0, 1, 4, 5, 7, 8, 10],          # West Asia / Mediterranean
    "in_sen": [0, 1, 5, 7, 10],               # Japan
    "pelog": [0, 1, 3, 7, 8],                 # Indonesia (approx.)
    "dorian": [0, 2, 3, 5, 7, 9, 10],         # Celtic / folk
    "phrygian_dom": [0, 1, 4, 5, 7, 8, 10],   # flamenco / klezmer
    "whole_tone": [0, 2, 4, 6, 8, 10],        # dreamlike / space
}


def tt(d):
    return np.arange(int(d * SR)) / SR


def _bp(lo, hi, n):
    return signal.sosfilt(signal.butter(2, [lo, hi], "band", fs=SR, output="sos"), n)


# ------------------------------------------------------------------ instruments (each returns a mono np array)
def drone(f, dur=4.5):
    """Tanpura-like buzzing drone note; retrigger every beat cycling (5th, root, root, low root)."""
    t = tt(dur); y = np.zeros_like(t); ph = _rng.uniform(0, 2 * np.pi, 60)
    for k in range(1, 48):
        if f * k > 9000:
            break
        bloom = 0.55 + 0.45 * np.sin(2 * np.pi * t * (0.35 + 0.11 * k) + ph[k])
        env = k ** -0.55 * np.exp(-t / (3.2 / (1 + 0.025 * k))) * bloom
        y += env * (np.sin(2 * np.pi * f * k * t + ph[k]) + 0.5 * np.sin(2 * np.pi * f * k * 1.0015 * t))
    y *= 1 - np.exp(-t / 0.004)
    return y / np.max(np.abs(y))


def pluck(f0, dur=1.4, f1=None, g0=0.05, gd=0.18, bright=1.0, buzz=2.2):
    """Plucked string (sitar/oud/koto-ish). f1 = glide (meend) target. buzz=0 for a clean guitar/harp."""
    t = tt(max(dur, 0.6))
    if f1 is None:
        f = np.full_like(t, f0)
    else:
        s = np.clip((t - g0) / gd, 0, 1); s = s * s * (3 - 2 * s)
        f = f0 * (f1 / f0) ** s
    phase = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros_like(t)
    for k in range(1, 30):
        if f0 * k > 11000:
            break
        a = k ** -0.8 * ((1.6 * bright) if 3 <= k <= 8 else 1.0)
        y += a * np.sin(k * phase) * np.exp(-t * (1.2 + 0.55 * k))
    y /= np.max(np.abs(y))
    if buzz:
        y = np.tanh(buzz * y) / np.tanh(buzz)
    y += _rng.normal(0, 1, len(t)) * np.exp(-t / 0.002) * 0.3
    return y * np.exp(-t / (len(t) / SR * 0.7))


def bell(f, dur=2.2, idx=2.5, ratio=3.5):
    t = tt(dur)
    m = idx * np.exp(-t / 0.5) * np.sin(2 * np.pi * f * ratio * t)
    return np.sin(2 * np.pi * f * t + m) * np.exp(-t / (dur * 0.35)) * (1 - np.exp(-t / 0.002))


def voice(f, dur, vowel=(700, 1220, 2600), vib=0.006):
    """Formant 'aah' choir / chant. vowels: a=(700,1220,2600) o=(500,900,2400) u=(350,700,2500)."""
    t = tt(dur)
    v = 1 + vib * np.sin(2 * np.pi * 5.2 * t) * np.clip(t, 0, 1)
    saw = 2 * ((np.cumsum(f * v) / SR) % 1) - 1
    y = sum(g * _bp(fm * 0.85, fm * 1.15, saw) for fm, g in zip(vowel, (1, 0.5, 0.25)))
    a = np.clip(t / 1.2, 0, 1) * np.clip((dur - t) / 1.5, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def pad(freqs, dur, cutoff=1400):
    t = tt(dur); y = np.zeros_like(t)
    for f in freqs:
        for d in (-0.004, 0.0, 0.005):
            y += 2 * ((f * (1 + d) * t + _rng.uniform()) % 1) - 1
    y = signal.sosfilt(signal.butter(2, cutoff, "low", fs=SR, output="sos"), y)
    a = np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 2.0, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def sub(f, dur):
    t = tt(dur)
    y = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.3 * y) * (1 - np.exp(-t / 0.005)) * np.exp(-t / (dur * 1.5)) * np.clip((dur - t) / 0.03, 0, 1)


def kick():
    t = tt(0.5)
    y = np.sin(2 * np.pi * np.cumsum(48 + 120 * np.exp(-t / 0.035)) / SR) * np.exp(-t / 0.28)
    return np.tanh(1.6 * (y + 0.4 * _rng.normal(0, 1, len(t)) * np.exp(-t / 0.003)))


def clap():
    t = tt(0.4); n = _bp(900, 3000, _rng.normal(0, 1, len(t)))
    env = sum(np.where(t >= d, np.exp(-(t - d) / 0.008), 0) for d in (0, 0.011, 0.022))
    return n * (env + 0.6 * np.where(t > 0.03, np.exp(-(t - 0.03) / 0.11), 0)) * 0.8


def hat(open_=False):
    t = tt(0.3 if open_ else 0.06)
    n = signal.sosfilt(signal.butter(4, 7000, "high", fs=SR, output="sos"), _rng.normal(0, 1, len(t)))
    return n * np.exp(-t / (0.08 if open_ else 0.012)) * 0.35


def drum_tone(pitch=277, dec=0.32, bright=1.0):
    """Resonant hand-drum 'na/tin' (tabla, darbuka doum-tek, djembe tone by pitch)."""
    t = tt(0.9); y = np.zeros_like(t)
    for k, a in zip(range(1, 6), [1, .6, .45, .3, .2]):
        y += (a if k == 1 else a * bright) * np.sin(2 * np.pi * pitch * k * t) * np.exp(-t / (dec / (1 + .6 * (k - 1))))
    y += 0.6 * _bp(2500, 6000, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.006)
    return y * 0.5


def drum_bass(f0=68, f1=96, dec=0.75):
    """Pitch-bent bass stroke (tabla 'ge', frame drum 'dum')."""
    t = tt(1.2); s = np.clip(t / 0.28, 0, 1)
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * (1 - (1 - s) ** 2)) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t / dec) * (1 - np.exp(-t / 0.003)) * 0.9


def drum_slap():
    t = tt(0.12)
    return (0.5 * _bp(1500, 5000, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.018)
            + 0.3 * np.sin(2 * np.pi * 320 * t) * np.exp(-t / 0.03)) * 0.7


def drum_muted():
    t = tt(0.1)
    return _bp(150, 700, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.02) * 1.2


def riser(dur, f0=200, f1=2400):
    t = tt(dur); n = _rng.normal(0, 1, len(t)); out = np.zeros_like(t); seg = int(0.05 * SR)
    for i in range(0, len(t), seg):
        c = f0 * (f1 / f0) ** (i / len(t))
        out[i:i + seg] = _bp(c * 0.7, min(c * 1.6, 20000), n[i:i + seg])
    ph = np.cumsum(110 * 2 ** (3 * (t / dur) ** 2)) / SR
    return (out + 0.3 * (2 * (ph % 1) - 1)) * (t / dur) ** 2


def boom(dur=3.0):
    t = tt(dur)
    y = np.sin(2 * np.pi * np.cumsum(30 + 45 * np.exp(-t / 0.2)) / SR) * np.exp(-t / 0.9)
    n = signal.sosfilt(signal.butter(2, 900, "low", fs=SR, output="sos"), _rng.normal(0, 1, len(t)))
    return np.tanh(2 * y) + 0.5 * n * np.exp(-t / 0.35)


def rumble(dur):
    t = tt(dur)
    return signal.sosfilt(signal.butter(2, 180, "low", fs=SR, output="sos"), _rng.normal(0, 1, len(t))) * \
        np.clip(t / 0.3, 0, 1) * 3.5


# ------------------------------------------------------------------ track
class Track:
    SEND = {"drone": 0.35, "perc": 0.18, "kick": 0.02, "bass": 0.0, "mel": 0.45, "fx": 0.5, "pad": 0.5}
    GAIN = {"drone": 0.55, "perc": 0.8, "kick": 0.9, "bass": 0.75, "mel": 0.62, "fx": 0.6, "pad": 0.55}

    def __init__(self, bpm, beats, root=138.59, scale="raga_bhairavi", tail=2.0, fps=30):
        self.bpm, self.beat, self.beats, self.root, self.fps = bpm, 60 / bpm, beats, root, fps
        self.scale = SCALES[scale] if isinstance(scale, str) else scale
        self.dur = beats * self.beat + tail
        self.N = int(self.dur * SR)
        self.buses = {k: np.zeros((2, self.N)) for k in self.SEND}
        self.stutters = []
        self._cache = {}

    def tb(self, b):
        return b * self.beat

    def hz(self, semi, octv=0):
        return self.root * 2 ** (octv + semi / 12)

    def deg(self, d, octv=0):
        """Scale degree -> Hz (d may exceed scale length or be negative)."""
        n = len(self.scale)
        return self.hz(self.scale[d % n], octv + d // n)

    def add(self, bus, sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= self.N or i < 0:
            return
        sig = sig[: self.N - i]
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
        self.buses[bus][0, i:i + len(sig)] += sig * gain * l
        self.buses[bus][1, i:i + len(sig)] += sig * gain * r

    def at(self, bus, sig, beat, gain=1.0, pan=0.0):
        self.add(bus, sig, self.tb(beat), gain, pan)

    def cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # ---- pattern helpers
    def drone_bed(self, b0, b1, level=lambda b: 0.3):
        notes = [self.hz(7, -1), self.hz(0), self.hz(0), self.hz(0, -1)]
        sigs = [self.cached(("drone", i), lambda f=f: drone(f)) for i, f in enumerate(notes)]
        for b in range(int(b0), int(b1)):
            self.at("drone", sigs[b % 4], b, level(b), [-0.4, 0.3, -0.1, 0.4][b % 4])

    def melody(self, b0, notes, octv=1, gain=0.55, pan=0.1, **pk):
        """notes: [(beat_offset, scale_degree, dur_beats?, glide_degree?)]; degrees index T.scale."""
        for n in notes:
            f0 = self.deg(n[1], octv)
            f1 = self.deg(n[3], octv) if len(n) > 3 and n[3] is not None else None
            self.at("mel", pluck(f0, self.tb(n[2]) if len(n) > 2 else 1.4, f1, **pk), b0 + n[0], gain, pan)

    def hand_drum(self, b0, b1, pattern=("B", "b", "t", "s", "t", "m", "B", "t"), step=0.5, gain=1.0, fills=True):
        """B=bass+tone, b=bass, t=tone, T=long tone, s=slap, m=muted, '-'=rest. Default is keherwa-like."""
        S = {"b": self.cached("db", drum_bass), "t": self.cached("dt", drum_tone),
             "T": self.cached("dT", lambda: drum_tone(dec=0.55, bright=0.35)),
             "s": self.cached("ds", drum_slap), "m": self.cached("dm", drum_muted)}
        b, bar = b0, 0
        while b < b1 - 1e-6:
            for i, s in enumerate(pattern):
                bb = b + i * step
                if bb >= b1:
                    break
                g = gain * (1.0 if i % 2 == 0 else 0.8)
                if s == "B":
                    self.at("perc", S["b"], bb, g * 0.9, -0.15); self.at("perc", S["t"], bb, g, 0.15)
                elif s in S:
                    self.at("perc", S[s], bb, g, {"b": -.15, "t": .2, "T": .2, "s": .3, "m": -.3}[s])
            span = len(pattern) * step
            if fills and bar % 2 == 1:
                self.at("perc", S["s"], b + span - 0.75, gain * 0.7); self.at("perc", S["s"], b + span - 0.25, gain * 0.6)
            b += span; bar += 1

    def tihai(self, land, phrase="Bssb", step=0.25, gap=0.5):
        """Rhythmic cadence: phrase ×3 ending exactly ON `land` beat (pair with a visual hit)."""
        S = {"B": (drum_bass, drum_tone), "b": (drum_bass,), "s": (drum_slap,), "t": (drum_tone,)}
        L = len(phrase) * step
        start = land - (3 * L + 2 * gap) + step
        for r in range(3):
            for i, c in enumerate(phrase):
                for fn in S[c]:
                    self.at("perc", self.cached(("th", fn.__name__), fn), start + r * (L + gap) + i * step, 1.1)
        self.at("kick", self.cached("kick", kick), land, 0.8)

    def groove(self, b0, b1, claps=True, four=True, bass_roots=(0, -2, -7, -5), hats=True):
        K, C, Hh = self.cached("kick", kick), self.cached("clap", clap), self.cached("hat", hat)
        for b in np.arange(b0, b1, 1.0):
            if four or (b - b0) % 2 == 0:
                self.at("kick", K, b, 0.95)
            if claps and int(b - b0) % 2 == 1:
                self.at("perc", C, b, 0.55)
            if hats:
                self.at("perc", Hh, b + 0.5, 0.6, 0.3); self.at("perc", Hh, b + 0.75, 0.25, -0.3)
        for i, b in enumerate(np.arange(b0, b1, 4.0)):
            for s in np.arange(0, 4, 0.5):
                self.at("bass", sub(self.hz(bass_roots[i % len(bass_roots)], -1), self.tb(0.42)), b + s,
                        0.55 if s % 1 else 0.4)

    def riser_into(self, beat, length=4, gain=0.4):
        self.at("fx", riser(self.tb(length)), beat - length, gain)

    def stutter(self, beat, reps=4, div=0.125):
        self.stutters.append((beat, reps, div))

    # ---- mix
    def mixdown(self, path="music.wav", fade_beats=(None, None)):
        kick_env = signal.sosfilt(signal.butter(1, 8, "low", fs=SR, output="sos"), np.abs(self.buses["kick"][0]))
        kick_env /= kick_env.max() + 1e-9
        duck = 1 - 0.7 * np.clip(kick_env * 3, 0, 1)
        for k in ("bass", "drone", "pad"):
            self.buses[k] *= duck
        irt = tt(2.8)
        ir = np.stack([_rng.normal(0, 1, len(irt)), _rng.normal(0, 1, len(irt))]) * np.exp(-irt / 0.7)
        ir = signal.sosfilt(signal.butter(1, 5000, "low", fs=SR, output="sos"), ir)
        ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
        dry = sum(v * self.GAIN[k] for k, v in self.buses.items())
        wet_in = sum(v * self.GAIN[k] * self.SEND[k] for k, v in self.buses.items())
        mix = dry + np.stack([signal.fftconvolve(wet_in[c], ir[c])[:self.N] for c in range(2)]) * 0.55
        for b, reps, div in self.stutters:
            i0, L = int(self.tb(b) * SR), int(self.tb(div) * SR)
            seg = mix[:, i0:i0 + L].copy()
            for r in range(reps):
                mix[:, i0 + r * L:i0 + (r + 1) * L] = seg[:, :mix[:, i0 + r * L:i0 + (r + 1) * L].shape[1]] * (1 - .15 * r)
        mix = signal.sosfilt(signal.butter(2, 28, "high", fs=SR, output="sos"), mix)
        mix /= np.max(np.abs(mix)); mix = np.tanh(1.5 * mix) / np.tanh(1.5)
        fs_, fe_ = fade_beats
        if fs_ is not None:
            a, e = int(self.tb(fs_) * SR), int(self.tb(fe_) * SR)
            fade = np.ones(self.N); fade[a:e] = np.linspace(1, 0, e - a) ** 2; fade[e:] = 0
            mix *= fade
        mix *= 0.89 / np.max(np.abs(mix))
        wavfile.write(path, SR, (mix.T * 32767).astype(np.int16))
        # per-frame loudness + waveform snapshot for audio-reactive visuals
        mono, spf = mix.mean(0), SR // self.fps
        nf = int(self.dur * self.fps)
        env = np.array([np.sqrt(np.mean(mono[i * spf:(i + 1) * spf] ** 2)) for i in range(nf)])
        np.save("env.npy", env / (env.max() + 1e-9))
        wave = np.zeros((nf, 512), np.float32)
        for i in range(nf):
            seg = mono[i * spf:i * spf + 2048]
            if len(seg) == 2048:
                wave[i] = seg[::4]
        np.save("wave.npy", wave)
        print("wrote", path, "%.1fs" % self.dur)
        return mix
