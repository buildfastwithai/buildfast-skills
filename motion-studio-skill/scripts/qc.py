#!/usr/bin/env python3
"""qc.py - automated quality control for a rendered Motion Studio video.

  qc.py PROJECT/out/NAME.mp4              (needs NAME.meta.json / NAME.layout.json next to it; render.py runs this automatically)
  qc.py --compare A.benchmark.json B.benchmark.json      determinism check for benchmark mode

Checks (see reference/qa.md): file, duration, resolution, fps, audio stream + loudness, black frames, frozen frames,
unexpected hard changes (glitches), text clipping / off-frame / unsafe / too small (from the in-browser layout audit),
missing fonts / assets / page errors, transitions present, scene timing & reading speed, audio-cue sync,
and a contact sheet of representative frames extracted from the FINAL file (look at it!).
Exit code 1 when any error is found.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np


def ffprobe(p):
    return json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)], capture_output=True, text=True).stdout)


def ff_filter(p, vf, extra=None):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p)] + (extra or []) + ["-vf", vf, "-an", "-f", "null", "-"], capture_output=True, text=True)
    return r.stderr


def intervals(text, key):
    starts = [float(x) for x in re.findall(key + r"_start:\s*([\d.]+)", text)]
    ends = [float(x) for x in re.findall(key + r"_end:\s*([\d.]+)", text)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def onset_env(p, sr=22050, hop=128):
    """Spectral-flux style onset envelopes (full band, >2 kHz and <250 Hz), frames of hop/sr seconds."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    if not len(x):
        return None
    from scipy.signal import butter, sosfilt
    xh = sosfilt(butter(4, 2000, "high", fs=sr, output="sos"), x)
    xl = sosfilt(butter(4, 250, "low", fs=sr, output="sos"), x)          # booms/kicks survive under noisy risers here
    n = len(x) // hop
    out = []
    for sig in (x, xh, xl):
        e = np.sqrt((sig[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-10)
        le = np.log(e)
        out.append(np.maximum(0, np.diff(le, prepend=le[0])))
    return out, hop / sr


def cue_onset(envs, step, t, win=.08, ctx=.6):
    """Is there an audible attack within +-win of t, standing out from the local context? Returns offset (s) or None."""
    best = None
    for fl in envs:
        i0, i1 = max(0, int((t - win) / step)), min(len(fl) - 1, int((t + win) / step) + 1)
        c0, c1 = max(0, int((t - ctx) / step)), min(len(fl), int((t + ctx) / step))
        if i1 <= i0 or c1 - c0 < 8:
            continue
        seg = fl[i0:i1]
        j = int(np.argmax(seg))
        base = fl[c0:c1]
        med = np.median(base)
        mad = np.median(np.abs(base - med)) + 1e-6
        if seg[j] > med + 6 * mad and seg[j] > .08:
            off = (i0 + j) * step - t
            if best is None or abs(off) < abs(best):
                best = off
    return best


def stem_hit(envs, step, t, win=.03, thr=2.5):
    """Attack in an SFX-only stem within +-win of t. Score = local flux peak / 99th percentile of the whole stem
    (calibrated on 3 projects: true cues score >= 3.8, random instants <= 2.3). Returns offset in seconds or None."""
    best, off = 0, None
    for fl in envs:
        i0, i1 = max(0, int((t - win) / step)), min(len(fl), int((t + win) / step) + 1)
        if i1 <= i0:
            continue
        ref = np.percentile(fl, 99) + 1e-9
        j = int(np.argmax(fl[i0:i1]))
        sc = fl[i0 + j] / ref
        if sc > best:
            best, off = sc, (i0 + j) * step - t
    return off if best >= thr else None


def rms_env(p, sr=22050, hop=128):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12), hop / sr


def level_hit(e, step, t, thr=2.2):
    """Second opinion for dense stems (a hit riding on another sound's tail): the level within -25..+40 ms of t
    jumps >= thr x above the median of the 25-90 ms before it and is loud relative to the stem (random instants: <3 %)."""
    i = lambda s: max(0, min(len(e), int(s / step)))
    pre, post = e[i(t - .09):i(t - .025)], e[i(t - .025):i(t + .04)]
    if len(pre) < 3 or not len(post):
        return False
    return post.max() >= .15 * np.percentile(e, 99) and post.max() / (np.median(pre) + 1e-6) >= thr


def has_content(video, t, w=480, h=270):
    """True if the frame at t has bright detail (text/shapes): >= 0.15 % of pixels with luma > 110."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    if not raw:
        return False
    y = np.frombuffer(raw, dtype=np.uint8)
    return (y > 110).mean() >= .0015


def xcorr_lag(ref_wav, video, sr=8000, secs=12):
    """Lag (s) of the video's audio relative to the reference wav, via cross-correlation of the first seconds."""
    def pcm(p):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(sr), "-t", str(secs), "-f", "f32le", "-"], capture_output=True).stdout
        return np.frombuffer(raw, dtype=np.float32).astype(float)
    a, b = pcm(ref_wav), pcm(video)
    n = min(len(a), len(b))
    if n < sr:
        return 0.0
    from scipy.signal import fftconvolve
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    c = fftconvolve(b, a[::-1], mode="full")
    lags = np.arange(-n + 1, n)
    w = np.abs(lags) <= int(.25 * sr)
    return float(lags[w][np.argmax(c[w])] / sr)


def run(video, project, name, meta=None):
    video, project = Path(video), Path(project)
    out = video.parent
    meta = meta or json.loads((out / f"{name}.meta.json").read_text())
    layout = json.loads((out / f"{name}.layout.json").read_text()) if (out / f"{name}.layout.json").exists() else []
    F = []   # findings

    def add(sev, check, msg, **kw):
        F.append(dict(severity=sev, check=check, msg=msg, **kw))

    # 1-5 container checks
    if not video.exists() or video.stat().st_size < 1000:
        add("error", "file", f"{video} missing or empty")
        return dict(findings=F)
    pr = ffprobe(video)
    vs = [s for s in pr["streams"] if s["codec_type"] == "video"]
    as_ = [s for s in pr["streams"] if s["codec_type"] == "audio"]
    dur = float(pr["format"]["duration"])
    v = vs[0]
    fps = eval(v["r_frame_rate"])
    exp_dur = meta["duration"]
    if abs(dur - exp_dur) > 1.5 / fps + .05:
        add("error", "duration", f"duration {dur:.3f}s != expected {exp_dur:.3f}s")
    exp_w, exp_h = meta["width"], meta["height"]
    if (v["width"], v["height"]) != (exp_w, exp_h):
        sev = "info" if abs(v["width"] / v["height"] - exp_w / exp_h) < .01 else "error"
        add(sev, "resolution", f"{v['width']}x{v['height']} (composition {exp_w}x{exp_h}){' - preview scale' if sev == 'info' else ' - aspect mismatch'}")
    if abs(fps - meta["fps"]) > .01 and "preview" not in name:
        add("warn", "fps", f"{fps:.2f} fps, spec {meta['fps']}")
    if v.get("pix_fmt") != "yuv420p":
        add("warn", "pix_fmt", f"pix_fmt {v.get('pix_fmt')} (yuv420p plays everywhere)")
    audio_expected = meta.get("audio", {}).get("music") not in (False, "none") or meta.get("audio", {}).get("sfx")
    if audio_expected and not as_ and "preview" not in name:
        add("warn", "audio", "no audio stream although audio was expected")
    loud = None
    if as_:
        t = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        m = re.search(r"I:\s*(-?[\d.]+) LUFS", t[t.rfind("Summary"):])
        pk = re.search(r"Peak:\s*(-?[\d.]+) dBFS", t[t.rfind("Summary"):])
        loud = dict(lufs=float(m.group(1)) if m else None, true_peak=float(pk.group(1)) if pk else None)
        if loud["lufs"] is not None and not (-18 <= loud["lufs"] <= -10):
            add("warn", "loudness", f"integrated loudness {loud['lufs']} LUFS (social target about -14)")
        if loud["true_peak"] is not None and loud["true_peak"] > -0.5:
            add("warn", "clipping", f"true peak {loud['true_peak']} dBFS")
    # 6 black frames (ignore intended fades / black holds)
    allow = [(tr["at"] - tr["dur"] / 2 - .05, tr["at"] + tr["dur"] / 2 + .05) for tr in meta["transitions"] if tr["type"] in ("fade", "iris", "cut", "flash", "shape", "morph", "match")]
    allow += [(s["start"], s["end"]) for s in meta["scenes"] if s.get("hold") == "black"]
    allow += [(0, .35), (exp_dur - 1.3, exp_dur + 1)]
    bl = intervals(ff_filter(video, "blackdetect=d=0.12:pix_th=0.06:pic_th=0.97"), "black")
    for a, b in bl:
        b = b if b is not None else dur
        if not any(a >= x - .02 and b <= y + .02 for x, y in allow):
            if has_content(video, (a + b) / 2):      # dark design frame (e.g. title card on black), not an empty frame
                add("info", "dark", f"mostly-black frames {a:.2f}-{b:.2f}s contain visible content (title card on black?)", t=a)
            else:
                add("warn", "black", f"black frames {a:.2f}-{b:.2f}s not explained by a fade/hold", t=a)
    # 7 frozen frames
    fz = intervals(ff_filter(video, "freezedetect=n=0.0008:d=1.2"), "freeze")
    for a, b in fz:
        b = b if b is not None else dur
        hold = any(s.get("hold") and s["start"] - .1 <= a and b <= s["end"] + .1 for s in meta["scenes"])
        if b - a >= 3.0 and not hold:
            add("warn", "frozen", f"no visible change {a:.2f}-{b:.2f}s ({b - a:.1f}s) - deliberate stillness? mark the scene hold:true, else add subtle motion", t=a)
        elif b - a >= 1.2:
            add("info", "stillness", f"still {a:.2f}-{b:.2f}s ({b - a:.1f}s){' (declared hold)' if hold else ''}", t=a)
    # 8 unexpected hard changes (possible glitches)
    txt = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf", "scdet=threshold=20,metadata=print", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    times, scores = [], []
    for blk in re.split(r"frame:\d+", txt):
        mt = re.search(r"lavfi\.scd\.time=([\d.]+)", blk)
        if mt:
            times.append(float(mt.group(1)))
            ms = re.search(r"lavfi\.scd\.score=([\d.]+)", blk)
            scores.append(float(ms.group(1)) if ms else 0.0)
    expected = [s["start"] for s in meta["scenes"]] + [tr["at"] for tr in meta["transitions"]] + [c["t"] for c in meta.get("cues", []) if c["type"] in ("impact", "flash", "glitch", "hit", "static", "boom", "stinger")]
    glitchy = any(k in "".join(meta.get("motion_ids", [])) for k in ("glitch", "energetic")) or any(k in "".join(meta.get("style_ids", [])) for k in ("glitch", "vhs"))
    unexpected = []
    for t, s in zip(times, scores):
        near = min((abs(t - e) for e in expected), default=9)
        tr_win = any(tr["at"] - tr["dur"] / 2 - .1 <= t <= tr["at"] + tr["dur"] / 2 + .1 for tr in meta["transitions"])
        if near > .25 and not tr_win:
            unexpected.append((t, s))
    for t, s in unexpected[:12]:
        add("info" if glitchy else "warn", "hard-change", f"abrupt full-frame change at {t:.2f}s (score {s:.0f}) not at a scene/transition/cue - intended?", t=t)
    # 9-10 layout audit
    seen = set()
    for it in layout:
        key = (it["kind"], it["text"])
        if key in seen:
            continue
        sev = it.get("severity", "warn")
        in_tr = any(tr["dur"] > 0 and tr["at"] - tr["dur"] / 2 - .05 <= it["t"] <= tr["at"] + tr["dur"] / 2 + .05 for tr in meta["transitions"])
        if in_tr and it["kind"] in ("offframe", "unsafe"):
            continue                                   # text is expected to move off-frame while a transition carries it out
        seen.add(key)
        msg = {"offframe": "text leaves the frame", "unsafe": "text outside the title-safe area", "small-text": f"text too small ({it.get('px')}px < {it.get('min')}px)",
               "overflow": "text overflows its box (clipped)"}[it["kind"]]
        add(sev, "layout", f"{msg}: '{it['text']}' at {it['t']:.2f}s", t=it["t"])
    # missing fonts / assets / page errors
    if meta.get("missingFonts"):
        add("error", "fonts", f"fonts not loaded: {meta['missingFonts']}")
    for e in meta.get("pageErrors", [])[:10]:
        add("error" if "404" in e or "Failed to load" in e or "Error" in e else "warn", "page", e[:200])
    # 11 transitions
    kinds = [tr["type"] for tr in meta["transitions"]]
    if len(meta["scenes"]) >= 4 and kinds and len(set(kinds)) == 1 and kinds[0] in ("fade", "dissolve"):
        add("warn", "transitions", f"every transition is '{kinds[0]}' - vary transitions (reference/transitions.md)")
    # 12 scene timing / reading speed
    words = {}
    for tx in meta.get("textList", []):
        words[tx["scene"]] = words.get(tx["scene"], 0) + tx["words"]
    for s in meta["scenes"]:
        d = s["end"] - s["start"]
        w = words.get(s["id"], 0)
        if w and w / max(d, .1) > 4.5:
            add("warn", "reading", f"scene '{s['id']}' shows {w} words in {d:.1f}s (> 4.5 words/s) - too fast to read")
        if d < .4:
            add("warn", "timing", f"scene '{s['id']}' lasts only {d:.2f}s")
    # 13 audio sync
    sync = None
    if as_ and meta.get("cues"):
        strong = [c for c in meta["cues"] if c["type"] in ("impact", "hit", "click", "pop", "tick", "boom", "flash", "stinger", "chime", "ding", "notify")]
        stem = out / f"{name}.sfx.wav"
        wav = out / f"{name}.wav"
        sync = {}
        # (a) every percussive cue must produce an attack in the SFX stem within 30 ms (music cannot mask this test)
        if stem.exists() and strong:
            envs = onset_env(stem)
            cues = sorted(meta["cues"], key=lambda c: c["t"])

            def stacked(c):   # another hit just before it: the two blur into one sound
                for d in cues:
                    if d is c or d["type"] in ("type", "click"):
                        continue
                    dt = c["t"] - d["t"]
                    win = .45 if d["type"] in ("impact", "boom", "drop", "braam", "hit", "stinger", "flash") else .25
                    if 0 < dt < win or (dt == 0 and cues.index(d) < cues.index(c)):
                        return True
                return False
            iso = [c for c in strong if not stacked(c)]
            lev = rms_env(stem)
            miss = [c for c in iso if stem_hit(envs[0], envs[1], c["t"]) is None and not level_hit(lev[0], lev[1], c["t"])]
            offs = [o for o in (stem_hit(envs[0], envs[1], c["t"]) for c in iso) if o is not None]
            sync.update(cues=len(iso), matched=len(iso) - len(miss), stacked=len(strong) - len(iso), median_offset_ms=round(float(np.median(offs)) * 1000, 1) if offs else None)
            if miss:
                add("warn", "sync", f"{len(miss)}/{len(iso)} percussive cues produced no distinct attack within 30 ms: " + ", ".join(f"{c['type']}@{c['t']:.2f}s" for c in miss[:6]))
            if len(strong) > len(iso):
                add("info", "sync", f"{len(strong) - len(iso)} hits are stacked within 0.25-0.45 s of an earlier hit (they blur into one sound; drop duplicates or space them)")
        # (b) the muxed track must line up with the generated mix (catches encoder priming / mux offsets)
        if wav.exists():
            lag = xcorr_lag(wav, video)
            sync["mux_offset_ms"] = round(lag * 1000, 1)
            if abs(lag) > 1 / fps:
                add("error", "sync", f"audio in the MP4 is shifted {lag * 1000:.0f} ms against the rendered soundtrack")
        if not sync:
            sync = None
    # 14 representative frames from the FINAL file
    sheet = out / f"{name}.qc-sheet.png"
    ts = []
    for s in meta["scenes"]:
        d = s["end"] - s["start"]
        ts += [s["start"] + min(.4, d * .25), s["start"] + d * .7]
        n = int(d / 1.5)                                             # long scenes (logo reveals, holds): one frame per ~1.5 s
        ts += [s["start"] + d * (k + .5) / n for k in range(n)] if n > 2 else []
    for tr in meta["transitions"]:
        if tr["dur"] > 0:
            ts.append(tr["at"])
    ts.append(dur - .1)                                              # always show the final frame (end card / thumbnail)
    ts = sorted({round(min(max(0, t), dur - .05), 2) for t in ts})
    if len(ts) > 28:                                                 # thin evenly - never drop the ending
        ts = [ts[round(i * (len(ts) - 1) / 27)] for i in range(28)]
    frames_dir = out / "qc-frames" / name
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in ts:
        p = frames_dir / f"f{t:07.2f}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=640:-2", str(p)])
        if p.exists():
            paths.append(p)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from render import contact_sheet
        labels = [f"{float(p.stem[1:]):.2f}s " + next((s["id"] for s in meta["scenes"] if s["start"] <= float(p.stem[1:]) < s["end"]), "") for p in paths]
        contact_sheet(paths, labels, sheet, cols=4, tile_w=440)
    except Exception as e:  # pragma: no cover
        add("warn", "sheet", f"contact sheet failed: {e}")
    rep = dict(video=str(video), duration=dur, size=[v["width"], v["height"]], fps=fps, audio=bool(as_), loudness=loud, sync=sync,
               black=bl, frozen=fz, scene_changes=len(times), transitions=kinds, findings=F, sheet=str(sheet),
               counts={k: sum(1 for f in F if f["severity"] == k) for k in ("error", "warn", "info")})
    (out / f"{name}.qc.json").write_text(json.dumps(rep, indent=1))
    return rep


def summary(rep):
    c = rep.get("counts", {})
    status = "FAIL" if c.get("error") else ("WARN" if c.get("warn") else "PASS")
    lines = [f"QC {status}: {c.get('error', 0)} errors, {c.get('warn', 0)} warnings, {c.get('info', 0)} info  |  {rep.get('size')} @ {rep.get('fps', 0):.0f}fps {rep.get('duration', 0):.2f}s"
             + (f"  |  {rep['loudness']['lufs']} LUFS" if rep.get("loudness") and rep["loudness"].get("lufs") is not None else "")
             + (f"  |  sync {rep['sync'].get('matched', '-')}/{rep['sync'].get('cues', '-')} cues, mux offset {rep['sync'].get('mux_offset_ms')} ms" if rep.get("sync") else "")]
    for f in rep.get("findings", []):
        if f["severity"] != "info":
            lines.append(f"  {f['severity'].upper():5s} {f['check']:12s} {f['msg']}")
    lines.append(f"  contact sheet (inspect it): {rep.get('sheet')}")
    return "\n".join(lines)


def compare(a, b):
    A, B = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    diff = [t for t in A["frames_md5"] if B["frames_md5"].get(t) != A["frames_md5"][t]]
    same_audio = A.get("audio_md5") == B.get("audio_md5")
    print(f"frames compared: {len(A['frames_md5'])}, differing: {len(diff)} {diff[:10]}")
    print(f"audio identical: {same_audio}")
    print("DETERMINISTIC" if not diff and same_audio else "NOT DETERMINISTIC")
    return not diff and same_audio


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--compare":
        sys.exit(0 if compare(sys.argv[2], sys.argv[3]) else 1)
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__ + "\nusage: qc.py PROJECT/out/NAME.mp4   |   qc.py --compare A.mp4 B.mp4")
    v = Path(sys.argv[1]).resolve()
    rep = run(v, v.parent.parent, v.stem)
    print(summary(rep))
    sys.exit(1 if rep.get("counts", {}).get("error") else 0)
