#!/usr/bin/env python3
"""audio.py - procedural score + sound design synced to a composition's scenes and cues.

Music follows the project's BPM grid (the same grid the composition uses via C.beat()), its arrangement follows
each scene's `energy` (0..1), and every cue exported by the composition (C.cue(t, type) or automatic cues from
transitions, typewriters, particles, logo reveals...) becomes a synthesized sound effect at exactly that time.

Genres (style registry sound.music): ambient, cinematic, synthwave, corporate, chiptune, lofi, glitch, horror,
trailer, whimsical, documentary, none.  SFX: impact boom whoosh swoosh riser click pop tick ding chime glitch type
notify shimmer stinger braam heartbeat zap beep static drop reverse hit.

A user track (spec.audio.file) replaces the generated music; a voice-over (spec.audio.voiceover) is mixed on top
with automatic ducking.  Usually called by render.py; standalone:  audio.py PROJECT/out/NAME.meta.json OUT.wav

Music visualizer / lyric video:  audio.py --analyze song.mp3 PROJECT
  -> PROJECT/assets/audio-features.json (fps-rate RMS, 4 bands, onsets, bpm, beat offset) and sets spec.audio.features
     + spec.audio.file, so the composition can read C.audio.level(t), C.audio.band(t, i), C.audio.onsetNear(t), C.audio.beatPhase(t).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
SFX_TYPES = ["impact", "boom", "whoosh", "swoosh", "riser", "click", "pop", "tick", "ding", "chime", "glitch", "type", "notify", "shimmer",
             "stinger", "braam", "heartbeat", "zap", "beep", "static", "drop", "reverse", "hit", "flash"]


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, o=2):
    return sosfilt(butter(o, min(fc, SR * .45), "low", fs=SR, output="sos"), x)


def hp(x, fc, o=2):
    return sosfilt(butter(o, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [max(20, lo), min(hi, SR * .45)], "band", fs=SR, output="sos"), x)


def env(n, a=.002, d=.2, s=0., r=.02):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-6), 1.0) * (s + (1 - s) * np.exp(-np.maximum(0, t - a) / max(d, 1e-6)))
    k = int(r * SR)
    if 0 < k < n:
        e[-k:] *= np.linspace(1, 0, k)
    return e


def saw(f, n, det=0.):
    t = np.arange(n) / SR
    o = 2 * ((t * f) % 1) - 1
    return o if not det else .5 * o + .5 * (2 * ((t * f * (1 + det)) % 1) - 1)


def sq(f, n, duty=.5):
    t = np.arange(n) / SR
    return np.where((t * f) % 1 < duty, 1.0, -1.0)


def tri(f, n):
    t = np.arange(n) / SR
    return 2 * np.abs(2 * ((t * f) % 1) - 1) - 1


def sine(f, n, ph=0.):
    return np.sin(2 * np.pi * f * np.arange(n) / SR + ph)


def sweep_noise(n, f0, f1, rng, q=2.5):
    x, out, blk = rng.standard_normal(n), np.zeros(n), 1024
    for k in range(0, n, blk):
        c = f0 * (f1 / f0) ** (k / max(1, n))
        out[k:k + blk] = bp(x[k:k + blk], c, c * q)
    return out


class Mixer:
    def __init__(self, dur, seed=7):
        self.N = int(dur * SR) + SR * 3
        self.bus = {k: np.zeros((self.N, 2)) for k in ("drums", "music", "sfx", "send")}
        self.rng = np.random.default_rng(seed)

    def add(self, bus, t, sig, gain=1., pan=0., rev=0.):
        i = int(round(t * SR))
        if i >= self.N or len(sig) == 0:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        j = min(self.N, i + len(sig))
        s = sig[:j - i] * gain
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
        self.bus[bus][i:j, 0] += s * l
        self.bus[bus][i:j, 1] += s * r
        if rev:
            self.bus["send"][i:j, 0] += s * l * rev
            self.bus["send"][i:j, 1] += s * r * rev


# ------------------------------------------------------------------ instruments
class Inst:
    def __init__(self, mx: Mixer, palette="clean"):
        self.m, self.rng, self.pal = mx, mx.rng, palette

    def kick(self, t, g=1., kind="punch"):
        n = int(.45 * SR)
        tt = np.arange(n) / SR
        if kind == "chip":
            s = sq(60, n) * env(n, .001, .06)
            s = lp(s, 900)
        else:
            f0, f1, d = (150, 44, .28) if kind == "punch" else (90, 42, .5) if kind == "808" else (110, 50, .18)
            f = f1 + (f0 - f1) * np.exp(-tt / .035)
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, d) + .2 * self.rng.standard_normal(n) * env(n, .0005, .004)
            s = np.tanh(s * (1.6 if kind != "soft" else 1.0))
        self.m.add("drums", t, s, .9 * g)

    def snare(self, t, g=1., kind="clap"):
        n = int(.4 * SR)
        if kind == "chip":
            s = self.rng.standard_normal(n) * env(n, .001, .07)
            s = np.sign(s) * (np.abs(s) > .6)
            self.m.add("drums", t, hp(s, 1000), .25 * g)
            return
        if kind == "clap":
            s = np.zeros(n)
            for k, dt in enumerate((0, .011, .022)):
                i = int(dt * SR)
                s[i:] += self.rng.standard_normal(n - i) * env(n - i, .0005, .012 if k < 2 else .15)
            s = bp(s, 900, 5500)
        elif kind == "rim":
            s = bp(self.rng.standard_normal(n), 1800, 6000) * env(n, .0005, .02) + .5 * sine(820, n) * env(n, .0005, .03)
        else:  # snare / gated
            s = bp(self.rng.standard_normal(n), 1200, 8000) * env(n, .001, .12 if kind == "snare" else .25) + .5 * sine(190, n) * env(n, .001, .06)
        self.m.add("drums", t, s, .45 * g, 0, rev=.25 if kind == "gated" else .12)

    def hat(self, t, g=1., open_=False, pan=.15, kind="hat"):
        n = int((.3 if open_ else .06) * SR)
        x = self.rng.standard_normal(n)
        if kind == "chip":
            x = np.sign(x)
        s = hp(x, 7000) * env(n, .0005, .12 if open_ else .018)
        self.m.add("drums", t, s, .2 * g, pan)

    def tom(self, t, g=1., f=70):
        n = int(1.2 * SR)
        tt = np.arange(n) / SR
        s = np.sin(2 * np.pi * np.cumsum(f * (1 + .6 * np.exp(-tt / .05))) / SR) * env(n, .002, .45) + .3 * lp(self.rng.standard_normal(n), 300) * env(n, .001, .08)
        self.m.add("drums", t, np.tanh(s * 1.4), .8 * g, 0, rev=.4)

    def bass(self, t, m, dur, g=1., kind="saw", cutoff=900):
        n = int(dur * SR)
        f = midi(m)
        if kind == "sub":
            s = sine(f, n) + .2 * sine(2 * f, n)
        elif kind == "chip":
            s = tri(f, n)
        elif kind == "pluck":
            s = lp(saw(f, n) * .7 + .5 * sine(f / 2, n), cutoff) * env(n, .002, .18)
            self.m.add("music", t, s, .3 * g)
            return
        else:
            s = lp(saw(f, n, .004) + .6 * sine(f / 2, n), cutoff)
        self.m.add("music", t, s * env(n, .004, dur * .9, .55, .012), .3 * g)

    def pluck(self, t, m, g=1., pan=0., kind="saw", bright=4000, dur=.4, rev=.3):
        n = int(dur * SR)
        f = midi(m)
        if kind == "bell":
            s = sine(f, n, 0) * (1 + .0) + .35 * sine(f * 2.76, n) * env(n, .001, .15) + .2 * sine(f * 5.4, n) * env(n, .001, .06)
            s = s * env(n, .002, .45)
        elif kind == "marimba":
            s = (sine(f, n) + .3 * sine(f * 4, n) * env(n, .001, .03)) * env(n, .001, .16)
        elif kind == "chip":
            s = sq(f, n, .25) * env(n, .001, .09, .2)
        elif kind == "piano":
            s = sum(a * sine(f * h, n) * env(n, .002, .9 / h) for h, a in ((1, 1), (2, .4), (3, .18), (4, .08)))
        else:
            s = lp(saw(f, n, .006) * .6 + .4 * sq(f, n), bright) * env(n, .002, .12)
        self.m.add("music", t, s, .15 * g, pan, rev)

    def pad(self, t, notes, dur, g=1., cutoff=2200, kind="saw", wobble=0.):
        n = int(dur * SR)
        L, R = np.zeros(n), np.zeros(n)
        tt = np.arange(n) / SR
        for m in notes:
            f = midi(m) * (1 + wobble * .004 * np.sin(2 * np.pi * .7 * tt))
            ph = 2 * np.pi * np.cumsum(f) / SR
            if kind == "warm":
                L += np.sin(ph) + .3 * np.sin(2 * ph)
                R += np.sin(ph * 1.002) + .3 * np.sin(2 * ph)
            else:
                L += 2 * ((ph / (2 * np.pi)) % 1) - 1
                R += 2 * ((ph * 1.003 / (2 * np.pi)) % 1) - 1
        e = env(n, min(.6, dur * .3), 99, 1.0, min(.8, dur * .35))
        L, R = lp(L, cutoff) * e, lp(R, cutoff) * e
        i = int(t * SR)
        j = min(self.m.N, i + n)
        for b, gg in (("music", .05), ("send", .035)):
            self.m.bus[b][i:j, 0] += L[:j - i] * gg * g
            self.m.bus[b][i:j, 1] += R[:j - i] * gg * g

    def drone(self, t, m, dur, g=1.):
        n = int(dur * SR)
        s = lp(saw(midi(m), n, .003) + saw(midi(m + 7), n, -.002) * .5, 380) + .25 * lp(self.rng.standard_normal(n), 200)
        self.m.add("music", t, s * env(n, 1.2, 99, 1.0, 1.0), .22 * g, 0, rev=.3)

    def texture(self, t, dur, kind="vinyl", g=1.):
        n = int(dur * SR)
        if kind == "vinyl":
            s = hp(self.rng.standard_normal(n), 3000) * .02 + (self.rng.random(n) > .9993) * self.rng.standard_normal(n) * .6
        else:  # air
            s = bp(self.rng.standard_normal(n), 2000, 9000) * .03
        self.m.add("music", t, s, g)


# ------------------------------------------------------------------ sfx
def sfx(inst: Inst, t, kind, g=1., dur=None, pal="clean"):
    m, rng = inst.m, inst.rng
    soft = pal in ("soft", "paper")
    chip = pal == "chip"
    if kind in ("impact", "hit", "flash"):
        n = int(2.2 * SR)
        tt = np.arange(n) / SR
        boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-tt / .08)) / SR) * env(n, .001, .55)
        crash = hp(rng.standard_normal(n), 2500) * env(n, .001, .7 if kind != "flash" else .3) * .35
        s = np.tanh(boom * 1.5) * .8 + crash
        if chip:
            s = np.sign(s) * np.minimum(1, np.abs(s) * 2) * env(n, .001, .2)
        m.add("sfx", t, s, (.35 if soft else .6) * g, 0, rev=.45)
    elif kind == "boom" or kind == "drop":
        n = int(2.5 * SR)
        tt = np.arange(n) / SR
        f = 55 * np.exp(-tt / (1.2 if kind == "drop" else .4)) + 25
        m.add("sfx", t, np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * 1.6) * env(n, .003, .9), .7 * g, 0, rev=.3)
    elif kind in ("whoosh", "swoosh", "reverse"):
        d = dur or (.7 if kind == "whoosh" else .35)
        n = int(d * SR)
        s = sweep_noise(n, 300, 7000 if kind != "reverse" else 5000, rng)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5 if kind != "reverse" else np.linspace(0, 1, n) ** 3
        m.add("sfx", t - (d if kind == "reverse" else 0), s * e, (.35 if kind == "whoosh" else .22) * g * (.6 if soft else 1), 0, rev=.3)
    elif kind == "riser":
        d = dur or 1.5
        n = int(d * SR)
        tt = np.arange(n) / SR
        s = sweep_noise(n, 400, 9000, rng, 3) + .3 * np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * tt / d)) / SR)
        m.add("sfx", t, s * (tt / d) ** 2, .3 * g, 0, rev=.4)
    elif kind in ("click", "type"):
        n = int(.03 * SR)
        s = bp(rng.standard_normal(n), 2500 if kind == "click" else 3500, 9000) * env(n, .0003, .005)
        if kind == "click":
            s += .4 * sine(1800, n) * env(n, .0003, .006)
        m.add("sfx", t, s, (.3 if kind == "click" else .16) * g, float(rng.uniform(-.3, .3)))
    elif kind in ("pop", "notify", "beep", "zap"):
        n = int((.18 if kind != "notify" else .45) * SR)
        tt = np.arange(n) / SR
        if kind == "pop":
            f = 420 * (1 + 1.6 * np.exp(-tt / .015))
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .05)
        elif kind == "notify":
            s = (sine(midi(81), n) * env(n, .002, .12) + sine(midi(88), n) * np.where(tt > .09, 1, 0) * env(n, .002, .2))
        elif kind == "beep":
            s = (sq(midi(84), n) if chip else sine(midi(84), n)) * env(n, .002, .08, .3, .02) * .6
        else:
            f = 2400 * np.exp(-tt / .05) + 200
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .09)
        m.add("sfx", t, s, .28 * g, 0, rev=.2)
    elif kind in ("tick", "ding", "chime"):
        n = int((.12 if kind == "tick" else 1.4) * SR)
        base = {"tick": 96, "ding": 88, "chime": 81}[kind]
        if kind == "chime":
            s = sum(sine(midi(base + k), n) * env(n, .002 + .03 * i, .7) for i, k in enumerate((0, 7, 12, 16)))
        else:
            s = (sine(midi(base), n) + .3 * sine(midi(base + 19), n)) * env(n, .001, .03 if kind == "tick" else .25)
        if chip:
            s = np.sign(s) * env(n, .001, .05)
        m.add("sfx", t, s, (.13 if kind == "tick" else .16) * g, float(rng.uniform(-.2, .2)), rev=.4)
    elif kind in ("glitch", "static"):
        d = dur or (.25 if kind == "glitch" else .5)
        n = int(d * SR)
        s = np.zeros(n)
        k = 0
        while k < n:
            L = int(rng.uniform(.01, .05) * SR)
            f = rng.uniform(80, 2400)
            chunk = sq(f, min(L, n - k)) if rng.random() > .5 else rng.standard_normal(min(L, n - k))
            s[k:k + L] = chunk[:len(s[k:k + L])] * (rng.random() > .25)
            k += L
        s = np.round(s * 4) / 4
        if kind == "static":
            s = hp(rng.standard_normal(n), 1500) * env(n, .002, d, .6, .05)
        m.add("sfx", t, s, .16 * g)
    elif kind == "shimmer":
        n = int(1.2 * SR)
        s = sum(sine(midi(96 + k), n) * env(n, .01 + .02 * i, .35) for i, k in enumerate((0, 4, 7, 12, 16)))
        m.add("sfx", t, s * .5, .13 * g, 0, rev=.6)
    elif kind == "braam":
        n = int(3.0 * SR)
        tt = np.arange(n) / SR
        s = sum(saw(midi(m0), n, .01) for m0 in (33, 40, 45))
        s = np.tanh(lp(s, 180 + 1400 * np.exp(-tt / .5).mean()) * 1.5)
        m.add("sfx", t, s * env(n, .03, 1.2), .5 * g, 0, rev=.5)
    elif kind == "stinger":
        n = int(1.6 * SR)
        tt = np.arange(n) / SR
        s = sum(saw(midi(m0), n, .02) for m0 in (73, 74, 79, 80)) * (1 + .5 * np.sin(2 * np.pi * 14 * tt))
        m.add("sfx", t, lp(s, 5000) * env(n, .005, .5), .18 * g, 0, rev=.6)
        sfx(inst, t, "impact", .8 * g, pal=pal)
    elif kind == "heartbeat":
        for dt, gg in ((0, 1), (.18, .7)):
            inst.kick(t + dt, .8 * g * gg, kind="soft")


# ------------------------------------------------------------------ genres & arrangement
PROG = {"minor": [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]], "major": [[0, 4, 7], [7, 11, 14], [9, 12, 16], [5, 9, 12]],
        "dark": [[0, 3, 7], [1, 5, 8], [0, 3, 7], [-1, 3, 6]], "modal": [[0, 3, 7], [5, 9, 12], [3, 7, 10], [5, 9, 12]]}
GENRES = {
    "ambient": dict(prog="major", kick=None, pad="warm", bass="sub", arp="bell", arp_div=2, hats=None, snare=None, texture="air"),
    "cinematic": dict(prog="minor", kick=None, pad="saw", bass="sub", arp=None, toms=True, drone=True, hats=None, snare=None, ticking=True),
    "synthwave": dict(prog="minor", kick="punch", snare="gated", pad="saw", bass="saw", arp="saw", arp_div=4, hats="hat"),
    "corporate": dict(prog="major", kick="soft", snare="clap", pad="warm", bass="pluck", arp="saw", arp_div=4, hats="hat", bright=5500),
    "chiptune": dict(prog="major", kick="chip", snare="chip", pad=None, bass="chip", arp="chip", arp_div=4, hats="chip"),
    "lofi": dict(prog="modal", kick="soft", snare="rim", pad="warm", bass="sub", arp="piano", arp_div=2, hats="hat", swing=.12, texture="vinyl", wobble=1),
    "glitch": dict(prog="minor", kick="punch", snare="clap", pad=None, bass="saw", arp="chip", arp_div=4, hats="hat", stutter=True),
    "horror": dict(prog="dark", kick=None, pad="saw", bass=None, arp=None, drone=True, heartbeat=True, hats=None, snare=None),
    "trailer": dict(prog="minor", kick="punch", snare="clap", pad="saw", bass="saw", arp="saw", arp_div=4, hats="hat", stabs=True),
    "whimsical": dict(prog="major", kick="soft", snare="rim", pad="warm", bass="pluck", arp="marimba", arp_div=4, hats="hat"),
    "documentary": dict(prog="modal", kick=None, pad="warm", bass="sub", arp="piano", arp_div=2, hats=None, snare=None, texture="air"),
}
KEY = {"C": 48, "C#": 49, "D": 50, "D#": 51, "E": 52, "F": 53, "F#": 54, "G": 55, "G#": 56, "A": 57, "A#": 58, "B": 59}


def energy_at(meta, t):
    for s in meta["scenes"]:
        if s["start"] <= t < s["end"]:
            return s.get("energy") if s.get("energy") is not None else .6
    return .4


def arrange(inst: Inst, meta, genre, key, bpm, dur):
    G = GENRES[genre]
    beat, bar = 60 / bpm, 240 / bpm
    root = KEY.get(key, 57)
    prog = PROG[G["prog"]]
    nbar = int(np.ceil(dur / bar)) + 1
    for b in range(nbar):
        t0 = b * bar
        if t0 >= dur:
            break
        e = max(energy_at(meta, min(dur - .01, t0 + q * beat)) for q in range(4))
        ch = [root + x for x in prog[b % 4]]
        rt = root - 12 + prog[b % 4][0]
        if G.get("pad") and (e < .95 or genre in ("cinematic", "ambient", "horror", "documentary", "synthwave")):
            inst.pad(t0, [n + 12 for n in ch] if genre != "horror" else [n + 12 for n in ch] + [ch[0] + 13], bar, 1.0 if e < .5 else .7,
                     kind=G["pad"], wobble=G.get("wobble", 0), cutoff=1400 + 2200 * e)
        if G.get("drone"):
            inst.drone(t0, root - 24 + prog[b % 4][0], bar, .8 + .4 * e)
        if G.get("texture"):
            inst.texture(t0, bar, G["texture"], .8)
        for q in range(4):
            tq = t0 + q * beat
            if tq >= dur:
                break
            eq = energy_at(meta, tq)
            sw = G.get("swing", 0) * beat
            if G.get("kick") and eq >= .5 and (q in (0, 2) or eq >= .65):
                inst.kick(tq, 1.0 if eq >= .65 else .8, G["kick"])
            if G.get("snare") and eq >= .55 and q in (1, 3):
                inst.snare(tq, 1.0, G["snare"])
            if G.get("hats") and eq >= .35:
                inst.hat(tq + beat / 2 + sw, .9, open_=eq >= .85 and q % 2 == 1, kind=G["hats"])
                if eq >= .75:
                    inst.hat(tq + beat / 4, .4, pan=-.2, kind=G["hats"])
                    inst.hat(tq + 3 * beat / 4 + sw, .4, pan=-.2, kind=G["hats"])
            if G.get("bass") and eq >= .3:
                if G["bass"] in ("saw", "chip", "pluck"):
                    for k in range(2):
                        inst.bass(tq + k * beat / 2 + (sw if k else 0), rt + (12 if k and eq > .7 else 0), beat / 2 * .9, 1.0, G["bass"], 500 + 900 * eq)
                elif q == 0:
                    inst.bass(tq, rt, bar * .98, .9, "sub")
            if G.get("arp") and eq >= (.25 if genre in ("ambient", "documentary", "lofi", "whimsical") else .55):
                div = G.get("arp_div", 4)
                for s16 in range(div):
                    m = ch[(q * div + s16) % 3] + 12 * ((s16 + q) % 2) + (12 if genre == "chiptune" else 0)
                    inst.pluck(tq + s16 * beat / div + (sw if s16 % 2 else 0), m, .8 + .3 * eq, pan=.35 * (1 if s16 % 2 else -1), kind=G["arp"], bright=G.get("bright", 2500 + 2500 * eq))
            if G.get("toms") and eq >= .6 and (q == 0 or (eq >= .85 and q == 2)):
                inst.tom(tq, .8 + .4 * eq, 62 if q == 0 else 78)
            if G.get("ticking") and .4 <= eq < .85:
                inst.hat(tq, .5, kind="hat")
                inst.hat(tq + beat / 2, .35, kind="hat")
            if G.get("heartbeat") and .3 <= eq and q in (0, 2):
                sfx(inst, tq, "heartbeat", .6 + .4 * eq)
            if G.get("stabs") and eq >= .85 and q == 0:
                inst.pad(tq, [n + 12 for n in ch] + [ch[0] + 24], beat * .9, 2.2, cutoff=4000)
            if G.get("stutter") and eq >= .6 and inst.rng.random() > .6:
                for k in range(4):
                    inst.hat(tq + beat / 2 + k * beat / 16, .5, kind="chip")


def load_audio_file(path, dur):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", str(dur + .5), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(out, dtype=np.float32).reshape(-1, 2).astype(float)
    return x


def build(project, meta, resolved, out_wav):
    project = Path(project)
    cfg = resolved.get("audio", {})
    snd = resolved["style"]["sound"]
    dur = meta["duration"]
    bpm = resolved.get("bpm", snd.get("bpm", 110))
    mx = Mixer(dur, seed=resolved.get("seed", 1234) % 100000)
    pal = snd.get("sfx", "clean")
    inst = Inst(mx, pal)
    genre = cfg.get("music", "auto")
    if genre in ("auto", True, None):
        genre = snd.get("music_alt") if snd.get("music_alt") and "horror" in snd.get("mood", "") else snd.get("music", "ambient")
    user_bed = None
    if cfg.get("file"):
        user_bed = load_audio_file(project / cfg["file"], dur)
    elif genre not in (False, "none") and genre in GENRES:
        arrange(inst, meta, genre, snd.get("key", "A"), bpm, dur)
    if cfg.get("sfx", True):
        for c in meta.get("cues", []):
            kind = c["type"]
            if kind not in SFX_TYPES:
                continue
            g = c.get("gain", 1.0) * (.7 if c.get("auto") else 1.0)
            sfx(inst, c["t"], kind, g, c.get("dur"), pal)
    # scenes with energy <= .1 are deliberate silences (e.g. the breath before a trailer title): gate music + drums
    gate = np.ones(mx.N)
    for sc in meta.get("scenes", []):
        if sc.get("energy") is not None and sc["energy"] <= .1:
            i0, i1 = int(sc["start"] * SR), int(sc["end"] * SR)
            r = int(.04 * SR)
            gate[i0:i1] = 0
            gate[max(0, i0 - r):i0] = np.minimum(gate[max(0, i0 - r):i0], np.linspace(1, 0, i0 - max(0, i0 - r)))
            gate[i1:i1 + r] = np.minimum(gate[i1:i1 + r], np.linspace(0, 1, len(gate[i1:i1 + r])))
    for k in ("music", "drums"):
        mx.bus[k] *= gate[:, None]
    # sidechain duck music under kicks (drum bus onsets)
    d = np.abs(mx.bus["drums"]).sum(1)
    if d.max() > 0:
        k = lp(d, 8)
        k = k / (k.max() + 1e-9)
        mx.bus["music"] *= (1 - .45 * np.clip(k, 0, 1))[:, None]
    ir_n = int(2.0 * SR)
    ir = mx.rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / (.5 * SR))[:, None]
    ir = np.stack([lp(ir[:, c], 6500) for c in range(2)], 1)
    ir /= np.sqrt((ir ** 2).sum(0))
    wet = np.stack([fftconvolve(mx.bus["send"][:, c], ir[:, c])[:mx.N] for c in range(2)], 1)
    mix = mx.bus["drums"] * .55 + mx.bus["music"] * 1.0 + mx.bus["sfx"] * .9 + wet * .8
    if user_bed is not None:
        bed = np.zeros_like(mix)
        n = min(len(bed), len(user_bed))
        bed[:n] = user_bed[:n]
        mix = mix * .8 + bed * 1.0
    if cfg.get("voiceover"):
        vo = load_audio_file(project / cfg["voiceover"], dur)
        v = np.zeros_like(mix)
        n = min(len(v), len(vo))
        v[:n] = vo[:n]
        venv = lp(np.abs(v).sum(1), 4)
        venv = np.clip(venv / (venv.max() + 1e-9) * 3, 0, 1)
        mix = mix * (1 - .55 * venv)[:, None] + v * 1.2
    for c in range(2):
        mix[:, c] = hp(mix[:, c], 30)
        mix[:, c] = mix[:, c] - .25 * lp(mix[:, c], 90) + .2 * bp(mix[:, c], 1500, 5000)
    n_end = int(dur * SR)
    fo = int(min(1.2, dur * .1) * SR)
    mix[n_end - fo:n_end] *= np.linspace(1, 0, fo)[:, None]
    mix = mix[:n_end]
    pk = np.abs(mix).max()
    if pk > 0:
        mix = np.tanh(mix / pk * 1.5) / np.tanh(1.5) * .89
    wavfile.write(out_wav, SR, (mix * 32767).astype(np.int16))
    stem = mx.bus["sfx"][:n_end].sum(1)                  # SFX-only stem: lets QC verify every cue actually sounds on time
    if np.abs(stem).max() > 0:
        wavfile.write(Path(out_wav).with_suffix(".sfx.wav"), SR, (stem / np.abs(stem).max() * .9 * 32767).astype(np.int16))
    print(f"audio : {out_wav}  (genre={genre if user_bed is None else 'user file'}, {len(meta.get('cues', []))} cues, bpm={bpm})")
    return out_wav


def analyze(path, fps=30):
    """Audio features for audio-reactive scenes: per-frame rms, 4 band energies, onsets (s), bpm, beat offset."""
    x = load_audio_file(path, 3600).mean(1)
    hop = SR // fps
    n = len(x) // hop
    fr = x[:n * hop].reshape(n, hop)
    rms = np.sqrt((fr ** 2).mean(1))
    spec = np.abs(np.fft.rfft(fr * np.hanning(hop), axis=1))
    freqs = np.fft.rfftfreq(hop, 1 / SR)
    edges = [(20, 150), (150, 800), (800, 4000), (4000, 16000)]
    bands = np.stack([spec[:, (freqs >= a) & (freqs < b)].mean(1) for a, b in edges], 1)
    bands = bands / (np.percentile(bands, 98, axis=0) + 1e-9)
    flux = np.maximum(0, np.diff(np.log(spec.sum(1) + 1e-9), prepend=0))
    thr = np.median(flux) + 2 * flux.std()
    onsets = [i / fps for i in range(1, n - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    env = flux - flux.mean()
    ac = np.correlate(env, env, "full")[n - 1:]
    lags = np.arange(len(ac)) / fps
    ok = (lags > 60 / 180) & (lags < 60 / 70)
    period = lags[ok][np.argmax(ac[ok])] if ok.any() else .5
    bpm = round(60 / period, 1)
    k = max(1, int(round(period * fps)))
    offset = int(np.argmax([flux[i::k].sum() for i in range(k)])) / fps
    return dict(fps=fps, duration=n / fps, rms=[round(float(v / (rms.max() + 1e-9)), 4) for v in rms],
                bands=[[round(float(min(1.5, v)), 3) for v in row] for row in bands], onsets=[round(o, 3) for o in onsets],
                bpm=bpm, beat_offset=round(offset, 3))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--analyze":
        src, project = Path(sys.argv[2]), Path(sys.argv[3])
        feats = analyze(src)
        (project / "assets").mkdir(parents=True, exist_ok=True)
        (project / "assets" / "audio-features.json").write_text(json.dumps(feats))
        if src.resolve().parent != (project / "assets").resolve():
            import shutil
            shutil.copy(src, project / "assets" / src.name)
        sp = project / "spec.json"
        if sp.exists():
            spec = json.loads(sp.read_text())
            spec.setdefault("audio", {}).update(features="assets/audio-features.json", file="assets/" + src.name)
            spec["bpm"] = feats["bpm"]
            spec["duration"] = min(spec.get("duration") or feats["duration"], feats["duration"])
            sp.write_text(json.dumps(spec, indent=1))
        print(f"features -> {project / 'assets/audio-features.json'}: {feats['duration']:.1f}s, bpm {feats['bpm']}, {len(feats['onsets'])} onsets")
        sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    meta_p = Path(sys.argv[1])
    meta = json.loads(meta_p.read_text())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mslib
    project = meta_p.parent.parent
    build(project, meta, mslib.resolve(mslib.load_spec(project)), sys.argv[2])
