#!/usr/bin/env python3
"""stylecut.py - STYLE-CUT mode: one composition, many visual styles, cut on the beat grid.

The same scene is rendered in several style/motion combinations and spliced together frame-accurately, so the
choreography never stops while the look (palette, type, textures, background, motion language) changes on every cut.
The soundtrack can follow: each style's own music genre is generated on the same BPM grid (and key) and cut in,
quantized to the beat so drums never stutter by accident.

  stylecut.py PROJECT CUTS.json [--name NAME] [--workers 3] [--no-qc] [--music follow|base]

CUTS.json
  {"cuts": [
     {"t0": 12, "t1": 14, "style": "cyberpunk"},                    # motion defaults to the style's own motion language
     {"t0": 14, "t1": 14.5, "style": "anime", "motion": "energetic"},
     {"t0": 27, "t1": 28, "grid": ["vhs", "anime", "blueprint", "luxury"], "cols": 2, "audio": "roll"},  # split screen
     {"t0": 0, "t1": 3, "audio_only": true, "music_style": "corporate", "level": 0.45, "end": "tapestop"}   # re-score a window only
   ],
   "audio_quant": 0.5,      # seconds; shorter cuts inherit the audio of the style that starts each block (default: 1 beat)
   "music": "follow"}       # follow = genre follows the style ; base = keep the base soundtrack

Pipeline: base render (render.py, full video + audio) -> per style: one browser renders only the frames of its windows
-> frames spliced (grid cuts tiled) -> video re-assembled around the window -> audio slices generated per style,
gain-matched to the base and cross-faded (5 ms) on the grid; "roll" = DJ beat-roll build from the previous beat
-> loudness-normalised mux -> QC (style cuts are declared as transitions, so they are not flagged as glitches).
The composition can read window.MS_SPEC.stylecut.cuts (e.g. to print "STYLE 07/28" in a HUD).
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mslib  # noqa: E402

SR = 44100


def vkey(style, motion=None):
    """Variant id; no motion = the style's own motion language (not the project's)."""
    return f"{style}::{motion or mslib.styles()[style]['motion_default']}"


def capture(job):
    """Worker process: render the frames of one style/motion variant (only its windows) as JPEGs; return its meta."""
    from playwright.sync_api import sync_playwright
    import render
    project, resolved, frames, outdir, fps = Path(job["project"]), job["resolved"], job["frames"], Path(job["outdir"]), job["fps"]
    outdir.mkdir(parents=True, exist_ok=True)
    srv, url = mslib.serve(project, resolved)
    with sync_playwright() as pw:
        b, pg, errors = render.open_page(pw, url, resolved["width"], resolved["height"])
        meta = pg.evaluate("window.__ms.meta()")
        cdp = pg.context.new_cdp_session(pg)
        for f in frames:
            pg.evaluate("t => window.__ms.render(t)", f / fps)
            data = cdp.send("Page.captureScreenshot", dict(format="jpeg", quality=93, optimizeForSpeed=True))["data"]
            (outdir / f"f{f:06d}.jpg").write_bytes(base64.b64decode(data))
        b.close()
    srv.shutdown()
    return job["key"], meta, errors[:5]


def read_wav(p):
    from scipy.io import wavfile
    sr, x = wavfile.read(p)
    x = x.astype(np.float64) / 32768.0
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return x


def fade_splice(dst, src, i0, i1, gain, fade):
    """Replace dst[i0:i1] by src[i0:i1]*gain with short equal-power crossfades at both edges."""
    seg = src[i0:i1] * gain
    n = i1 - i0
    f = min(fade, n // 2)
    if f > 0:
        r = np.sin(np.linspace(0, np.pi / 2, f))[:, None]
        seg[:f] = seg[:f] * r + dst[i0:i0 + f] * r[::-1]
        seg[n - f:] = seg[n - f:] * r[::-1] + dst[i1 - f:i1] * r
    dst[i0:i1] = seg


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)) + 1e-9)


def beat_roll(mix, t0, t1, beat):
    """DJ roll: retrigger the previous beat in shrinking slices (1/2, 1/2, 1/4 x2, 1/8 x4 ... beats) + a noise sweep."""
    i0, i1 = int(t0 * SR), int(t1 * SR)
    src = mix[int((t0 - beat) * SR):i0].copy()
    out, pos, k = np.zeros_like(mix[i0:i1]), 0, 0
    pattern = [.5, .5, .25, .25, .25, .25] + [.125] * 64
    while pos < len(out):
        L = int(pattern[min(k, len(pattern) - 1)] * beat * SR)
        piece = src[:L].copy()
        ramp = min(len(piece) // 2, int(.004 * SR))
        piece[:ramp] *= np.linspace(0, 1, ramp)[:, None]
        piece[len(piece) - ramp:] *= np.linspace(1, 0, ramp)[:, None]
        n = min(L, len(out) - pos)
        out[pos:pos + n] = piece[:n] * (.75 + .5 * pos / len(out))
        pos += n
        k += 1
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((len(out), 2))
    from scipy.signal import butter, sosfilt
    sweep = np.zeros_like(noise)
    blocks = 16
    for j in range(blocks):
        a, b = j * len(out) // blocks, (j + 1) * len(out) // blocks
        fc = 400 * (12 ** (j / blocks))
        sweep[a:b] = sosfilt(butter(2, [fc, min(fc * 2.5, SR * .45)], "band", fs=SR, output="sos"), noise[a:b], axis=0)
    sweep *= np.linspace(0, 1, len(out))[:, None] ** 2
    out += sweep / (np.abs(sweep).max() + 1e-9) * .35 * np.abs(out).max()
    mix[i0:i1] = out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("cuts")
    ap.add_argument("--name")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--no-qc", action="store_true")
    ap.add_argument("--music", choices=["follow", "base"])
    ap.add_argument("--skip-base", action="store_true", help="reuse an existing base render in out/")
    a = ap.parse_args()
    t_start = time.time()
    project = Path(a.project).resolve()
    doc = json.loads(Path(a.cuts).read_text())
    allcuts = sorted(doc["cuts"], key=lambda c: c["t0"])
    cuts = [c for c in allcuts if not c.get("audio_only")]                          # video cuts (contiguous)
    rescore = [c for c in allcuts if c.get("audio_only")]                           # audio-only windows (any time)
    music = a.music or doc.get("music", "follow")
    spec = mslib.load_spec(project)
    spec["stylecut"] = {"cuts": [dict(c) for c in cuts]}         # the composition can read its cut list
    (project / "spec.json").write_text(json.dumps(spec, indent=1))
    base = spec["name"]
    name = a.name or f"{base}__stylecut"
    out = project / "out"
    out.mkdir(exist_ok=True)
    R = Path(__file__).resolve().parent

    # 1 base render (full video + soundtrack)
    if not (a.skip_base and (out / f"{base}.mp4").exists() and (out / f"{base}.wav").exists()):
        subprocess.run([sys.executable, str(R / "render.py"), str(project), "--no-qc"], check=True)
    base_meta = json.loads((out / f"{base}.meta.json").read_text())
    base_res = mslib.resolve(spec)
    fps = base_res["fps"]
    beat = 60 / base_res["bpm"]
    quant = doc.get("audio_quant", beat)
    fr = lambda t: int(math.floor(t * fps + .5))                                   # one rounding rule for every frame decision

    # 2 which frames does each variant have to render?
    jobs = {}

    def need(style, motion, f0, f1):
        k = vkey(style, motion)
        if k not in jobs:
            mo = k.split("::")[1]
            res = mslib.resolve(spec, {"style": style, "motion": mo})
            res["style"]["sound"]["key"] = base_res["style"]["sound"].get("key", "A")      # one key + one tempo: cuts stay musical
            jobs[k] = dict(key=k, style=style, motion=mo, resolved=res, frames=set(), outdir=str(out / "_stylecut" / mslib.variant_name(style, mo)),
                           project=str(project), fps=fps)
        jobs[k]["frames"].update(range(f0, f1))
        return k

    F0, F1 = fr(cuts[0]["t0"]), fr(max(c["t1"] for c in cuts))
    for c in cuts:                                                                  # single cuts first ...
        if not c.get("grid"):
            c["_key"] = need(c["style"], c.get("motion"), fr(c["t0"]), fr(c["t1"]))
    for c in cuts:                                                                  # ... grid tiles reuse a variant of the same style
        if c.get("grid"):
            c["_keys"] = []
            for st in c["grid"]:
                k = next((k for k, j in jobs.items() if j["style"] == st), None) or vkey(st)
                c["_keys"].append(need(st, k.split("::")[1], fr(c["t0"]), fr(c["t1"])))
    for c in rescore:                                                               # music only: no frames to render
        c["_key"] = need(c["music_style"], c.get("motion"), 0, 0)
    shutil.rmtree(out / "_stylecut", ignore_errors=True)
    print(f"stylecut: {len(cuts)} cuts, {len(jobs)} style variants, {F1 - F0} frames ({cuts[0]['t0']}-{F1 / fps}s)")
    metas = {}
    with cf.ProcessPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = [ex.submit(capture, dict(j, frames=sorted(j["frames"]))) for j in jobs.values() if j["frames"]]
        for fu in cf.as_completed(futs):
            k, meta, errs = fu.result()
            metas[k] = meta
            print(f"  rendered {k:34s} {len(jobs[k]['frames']):4d} frames" + (f"  page errors: {errs}" if errs else ""), flush=True)

    # 3 splice frames (grid cuts tiled) -> segment
    from PIL import Image
    W, H = base_res["width"], base_res["height"]
    seq = out / "_stylecut" / "_seq"
    seq.mkdir(parents=True, exist_ok=True)
    for f in range(F0, F1):
        t = f / fps
        c = next((c for c in cuts if fr(c["t0"]) <= f < fr(c["t1"])), None)
        dst = seq / f"{f - F0:06d}.jpg"
        if c is None:
            raise SystemExit(f"stylecut: no cut covers {t:.3f}s (cuts must be contiguous)")
        if c.get("grid"):
            cols = c.get("cols") or math.ceil(math.sqrt(len(c["grid"])))
            rows = math.ceil(len(c["grid"]) / cols)
            tw, th = W // cols, H // rows
            canvas = Image.new("RGB", (W, H), (0, 0, 0))
            for i, k in enumerate(c["_keys"]):
                im = Image.open(Path(jobs[k]["outdir"]) / f"f{f:06d}.jpg").convert("RGB").resize((tw, th), Image.LANCZOS)
                canvas.paste(im, ((i % cols) * tw, (i // cols) * th))
            canvas.save(dst, quality=93)
        else:
            shutil.copy(Path(jobs[c["_key"]]["outdir"]) / f"f{f:06d}.jpg", dst)
    seg = out / "_stylecut" / "_seg.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(seq / "%06d.jpg"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-r", str(fps), str(seg)], check=True)
    silent = out / f"_{name}.silent.mp4"
    T0, T1 = F0 / fps, F1 / fps
    fc = (f"[0:v]split=2[p][q];[p]trim=start=0:end={T0},setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];"
          f"[q]trim=start={T1},setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0,fps={fps},format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{base}.mp4"), "-i", str(seg), "-filter_complex", fc, "-map", "[v]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M", "-an", str(silent)], check=True)

    # 4 soundtrack
    import audio as audiomod
    mix = read_wav(out / f"{base}.wav")
    if music == "follow" or rescore:
        # schedule: long cuts keep their own audio; short ones are grouped into quant-sized blocks (style at block start)
        sched, t = [], cuts[0]["t0"] if music == "follow" else T1
        while t < T1 - 1e-6:
            c = next(c for c in cuts if c["t0"] - 1e-6 <= t < c["t1"] - 1e-6)
            if c.get("audio") == "roll":
                sched.append((t, c["t1"], "roll"))
                t = c["t1"]
                continue
            key = c["_keys"][0] if c.get("grid") else c["_key"]
            end = c["t1"] if c["t1"] - t >= quant - 1e-6 else min(T1, t + quant)
            # never let a quantized block swallow a following "roll"
            nxt = next((d for d in cuts if d.get("audio") == "roll" and t < d["t0"] < end), None)
            end = nxt["t0"] if nxt else end
            if sched and sched[-1][2] == key and abs(sched[-1][1] - t) < 1e-6:
                sched[-1] = (sched[-1][0], end, key)
            else:
                sched.append((t, end, key))
            t = end
        needed = {k for _, _, k in sched} | {c["_key"] for c in rescore}
        wavs = {}
        for k, j in jobs.items():
            if k not in needed:                                                     # only styles that are actually heard
                continue
            m = dict(base_meta, cues=metas.get(k, {}).get("cues", base_meta["cues"]))
            for c in rescore:                                                       # a re-scored window plays even over a deliberate silence
                if c["_key"] == k:
                    m["scenes"] = [dict(sc, energy=c.get("energy", .6)) if sc["start"] < c["t1"] and sc["end"] > c["t0"] else sc for sc in m["scenes"]]
            p = out / "_stylecut" / f"{mslib.variant_name(j['style'], j['motion'])}.wav"
            audiomod.build(project, m, j["resolved"], p)
            wavs[k] = read_wav(p)
        fade = int(.005 * SR)
        ref = mix.copy()
        for t0, t1, key in sched:
            i0, i1 = int(round(t0 * SR)), int(round(t1 * SR))
            if key == "roll":
                beat_roll(mix, t0, t1, beat)
                continue
            src = wavs[key]
            g = float(np.clip(rms(ref[i0:i1]) / rms(src[i0:i1]), .5, 2.0))
            fade_splice(mix, src, i0, i1, g, fade)
        body = rms(ref[int(T0 * SR):])
        for c in rescore:
            i0, i1 = int(round(c["t0"] * SR)), int(round(c["t1"] * SR))
            src = wavs[c["_key"]]
            fade_splice(mix, src, i0, i1, c.get("level", .5) * body / rms(src[i0:i1]), fade)
            if c.get("end") == "tapestop":                                          # the record grinds to a halt at t1
                L = int(.45 * SR)
                seg = mix[i1 - L:i1].copy()
                rate = np.linspace(1, 0, L) ** 1.6
                pos = np.cumsum(rate)
                pos = np.clip(pos, 0, L - 1)
                mix[i1 - L:i1] = np.stack([np.interp(pos, np.arange(L), seg[:, ch]) for ch in range(2)], 1) * np.linspace(1, .2, L)[:, None]
            sched.append((c["t0"], c["t1"], c["_key"] + " (re-score)"))
        print("audio schedule: " + " | ".join(f"{t0:.2f}-{t1:.2f} {k.split('::')[0]}" for t0, t1, k in sched))
    from scipy.io import wavfile
    pk = np.abs(mix).max()
    wav = out / f"{name}.wav"
    wavfile.write(wav, SR, (mix / max(pk, 1e-9) * .89 * 32767).astype(np.int16))
    import render
    final = out / f"{name}.mp4"
    render.mux(silent, wav, final, base_res["audio"].get("lufs", -14))
    silent.unlink()

    # 5 QC (cuts are declared, the layout audit is the base render's)
    meta = dict(base_meta)
    meta["transitions"] = list(base_meta["transitions"]) + [{"from": "stylecut", "to": "stylecut", "at": c["t0"], "dur": 0, "type": "stylecut"} for c in cuts]
    meta["stylecut"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cuts]
    (out / f"{name}.meta.json").write_text(json.dumps(meta, indent=1))
    if (out / f"{base}.layout.json").exists():
        shutil.copy(out / f"{base}.layout.json", out / f"{name}.layout.json")
    shutil.rmtree(out / "_stylecut", ignore_errors=True)
    print(f"video : {final}  ({time.time() - t_start:.0f}s)")
    if not a.no_qc:
        import qc
        rep = qc.run(final, project, name, meta)
        print(qc.summary(rep))


if __name__ == "__main__":
    main()
