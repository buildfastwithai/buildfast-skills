#!/usr/bin/env python3
"""render.py - render a Motion Studio project (composition.html + spec.json) to stills, previews or a final MP4.

  render.py PROJECT --stills auto              contact sheet of representative frames (out/stills/, out/sheet.png)
  render.py PROJECT --stills 0.5,2,4.25        specific times
  render.py PROJECT --preview                  half-res, 15 fps, no QC gate - fast look at timing
  render.py PROJECT                            final: frames -> H.264 + generated audio -> out/<name>.mp4, then QC
  render.py PROJECT --style cyberpunk --motion cinematic      one-off restyle (variant file name)
  render.py PROJECT --variants "cyberpunk:cinematic;minimal:calm;vhs:glitch" [--preview]   multi-version + comparison grid
  render.py PROJECT --benchmark                deterministic render + out/benchmark.json (frame/audio hashes)
  render.py PROJECT --serve                    live preview with a scrub bar (open the printed URL)

Options: --workers N (parallel browsers, default 2) --range A:B (seconds) --no-audio --fps N --scale F --name NAME
         --format 9:16 (re-layout for another aspect) --jpeg (faster frames, slight compression)
Needs: python playwright (+Chromium), ffmpeg/ffprobe. Everything else is in the skill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mslib  # noqa: E402

CHROME_ARGS = ["--font-render-hinting=none", "--disable-lcd-text",
               "--force-color-profile=srgb", "--autoplay-policy=no-user-gesture-required"]


def open_page(pw, url, W, H, scale=1.0):
    b = pw.chromium.launch(args=CHROME_ARGS)
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
    pg.add_init_script("window.__MS_RENDER = true;")
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(url + "/composition.html", wait_until="load")
    try:
        pg.wait_for_function("window.__ms && window.__ms.ready", timeout=60000)
    except Exception:
        raise SystemExit("composition did not become ready:\n  " + "\n  ".join(errors[-8:] or ["(no errors captured)"]))
    return b, pg, errors


def frame_times(fps, dur, rng=None):
    n = int(round(dur * fps))
    a, b = (0, n) if not rng else (int(round(rng[0] * fps)), min(n, int(round(rng[1] * fps))))
    return list(range(a, b))


# ------------------------------------------------------------------ worker (one browser, contiguous frames -> segment)
def worker(args):
    from playwright.sync_api import sync_playwright
    W, H, fps = args.W, args.H, args.fps
    ow, oh = int(round(W * args.scale / 2) * 2), int(round(H * args.scale / 2) * 2)
    with sync_playwright() as pw:
        b, pg, errors = open_page(pw, args.url, W, H, args.scale)
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg" if args.jpeg else "png", "-i", "-",
                                "-vf", f"scale={ow}:{oh}:flags=bicubic,format=yuv420p", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
                                "-profile:v", "high", "-maxrate", args.maxrate, "-bufsize", str(2 * int(args.maxrate.rstrip("M"))) + "M", "-g", str(fps * 2), "-r", str(fps), args.segment], stdin=subprocess.PIPE)
        import base64
        cdp = pg.context.new_cdp_session(pg)                      # CDP capture: ~3x faster than page.screenshot for PNG
        shot = dict(format="jpeg", quality=94, optimizeForSpeed=True) if args.jpeg else dict(format="png", optimizeForSpeed=True)
        for i in range(args.f0, args.f1):
            pg.evaluate("t => window.__ms.render(t)", i / fps)
            enc.stdin.write(base64.b64decode(cdp.send("Page.captureScreenshot", shot)["data"]))
            if (i - args.f0) % 120 == 0:
                print(f"  [worker {args.f0}-{args.f1}] frame {i}", flush=True)
        enc.stdin.close()
        enc.wait()
        b.close()
        if errors:
            print("  page errors: " + " | ".join(errors[:5]), flush=True)


def render_video(project, url, resolved, out_mp4, fps, scale, workers, jpeg, rng=None, crf=17):
    W, H = resolved["width"], resolved["height"]
    frames = frame_times(fps, resolved["duration"], rng)
    workers = max(1, min(workers, len(frames) // 30 or 1))
    chunk = math.ceil(len(frames) / workers)
    tmp = out_mp4.parent / ("_seg_" + out_mp4.stem)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    procs, segs = [], []
    for k in range(workers):
        f0, f1 = frames[0] + k * chunk, min(frames[0] + (k + 1) * chunk, frames[-1] + 1)
        if f0 >= f1:
            continue
        seg = tmp / f"seg{k:02d}.mp4"
        segs.append(seg)
        cmd = [sys.executable, __file__, "--_worker", "--url", url, "--W", str(W), "--H", str(H), "--fps", str(fps), "--scale", str(scale),
               "--f0", str(f0), "--f1", str(f1), "--segment", str(seg), "--crf", str(crf), "--preset", "veryfast", "--maxrate", "14M"] + (["--jpeg"] if jpeg else [])
        procs.append(subprocess.Popen(cmd))
    for p in procs:
        if p.wait() != 0:
            raise SystemExit("a render worker failed")
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out_mp4)], check=True, cwd=tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def mux(video, wav, out, lufs):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
          f"aresample=192000,alimiter=limit=0.79:level=false:attack=1:release=60,aresample=48000")   # true-peak safety (~-2 dBTP before AAC)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)


def auto_times(meta):
    ts = []
    for s in meta["scenes"]:
        d = s["end"] - s["start"]
        ts += [s["start"] + min(.35, d * .2), s["start"] + d * .55, s["end"] - min(.12, d * .05)]
    for tr in meta["transitions"]:
        if tr["dur"] > 0:
            ts.append(tr["at"])
    return sorted({round(min(max(0, t), meta["duration"] - 1 / meta["fps"]), 3) for t in ts})


def contact_sheet(paths, labels, out, cols=4, tile_w=480):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in paths]
    if not ims:
        return
    w0, h0 = ims[0].size
    tw, th = tile_w, int(tile_w * h0 / w0)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 30) + 8), (28, 28, 34))
    d = ImageDraw.Draw(sheet)
    for i, (im, lb) in enumerate(zip(ims, labels)):
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 30)
        sheet.paste(im.resize((tw, th)), (x, y + 22))
        d.text((x + 2, y + 5), lb, fill=(235, 235, 90))
    sheet.save(out)


def stills(pg, times, outdir, meta):
    outdir.mkdir(parents=True, exist_ok=True)
    paths, labels = [], []
    for t in times:
        pg.evaluate("t => window.__ms.render(t)", t)
        p = outdir / f"t{t:07.3f}.png"
        pg.screenshot(path=str(p))
        paths.append(p)
        sc = next((s["id"] for s in meta["scenes"] if s["start"] <= t < s["end"]), "")
        labels.append(f"{t:6.2f}s  {sc}")
    return paths, labels


def audit(pg, meta, step=0.5):
    issues, t = [], 0.0
    ts = set()
    while t < meta["duration"]:
        ts.add(round(t, 3))
        t += step
    for s in meta["scenes"]:
        ts.add(round(min(s["end"] - .05, s["start"] + (s["end"] - s["start"]) * .8), 3))
    for t in sorted(ts):
        issues += pg.evaluate("t => window.__ms.audit(t)", t)
    return issues


def run_one(project, resolved, name, a):
    from playwright.sync_api import sync_playwright
    out = project / "out"
    out.mkdir(exist_ok=True)
    srv, url = mslib.serve(project, resolved)
    fps = a.fps or (15 if a.preview else resolved["fps"])
    scale = a.scale or (0.5 if a.preview else 1.0)
    t0 = time.time()
    with sync_playwright() as pw:
        b, pg, errors = open_page(pw, url, resolved["width"], resolved["height"])
        meta = pg.evaluate("window.__ms.meta()")
        meta["fps"] = resolved["fps"]
        meta["style_ids"], meta["motion_ids"] = resolved["style_ids"], resolved["motion_ids"]
        meta["sound"] = resolved["style"]["sound"]
        meta["audio"] = resolved.get("audio", {})
        meta["pageErrors"] = errors[:20]
        (out / f"{name}.meta.json").write_text(json.dumps(meta, indent=1))
        if meta.get("missingFonts"):
            print("WARNING missing fonts:", meta["missingFonts"])
        if errors:
            print("WARNING page errors:\n  " + "\n  ".join(errors[:10]))
        if a.stills is not None:
            times = auto_times(meta) if a.stills in ("auto", "") else [float(x) for x in a.stills.split(",")]
            paths, labels = stills(pg, times, out / "stills" / name, meta)
            contact_sheet(paths, labels, out / f"{name}.sheet.png")
            print(f"stills: {len(paths)} -> {out / 'stills' / name}\nsheet : {out / (name + '.sheet.png')}")
            b.close()
            srv.shutdown()
            return None
        issues = audit(pg, meta) if not a.preview else []
        (out / f"{name}.layout.json").write_text(json.dumps(issues, indent=1))
        bench_frames = {}
        if a.benchmark:
            for t in [x * 0.5 for x in range(int(meta["duration"] * 2))]:
                pg.evaluate("t => window.__ms.render(t)", t)
                bench_frames[f"{t:.1f}"] = hashlib.md5(pg.screenshot(type="png")).hexdigest()
        b.close()
    silent = out / f"_{name}.silent.mp4"
    rng = [float(x) for x in a.range.split(":")] if a.range else None
    print(f"rendering {name}: {resolved['width']}x{resolved['height']} x{scale} @ {fps} fps, {resolved['duration']} s, workers={a.workers}")
    render_video(project, url, resolved, silent, fps, scale, a.workers, a.jpeg, rng, crf=24 if a.preview else 16)
    srv.shutdown()
    final = out / f"{name}.mp4"
    ac = resolved.get("audio", {})
    want_audio = (not a.no_audio) and (ac.get("music") not in (False, "none") or bool(ac.get("sfx")))
    if want_audio:
        import audio as audiomod
        wav = out / f"{name}.wav"
        audiomod.build(project, meta, resolved, wav)
        mux(silent, wav, final, resolved["audio"].get("lufs", -14))
        silent.unlink()
    else:
        silent.replace(final)
    print(f"video : {final}  ({time.time() - t0:.0f}s)")
    if a.benchmark:
        import hashlib as hl
        bj = {"engine": meta["engine"], "spec_sha1": hl.sha1(json.dumps(mslib.load_spec(project), sort_keys=True).encode()).hexdigest(),
              "style": meta["style_ids"], "motion": meta["motion_ids"], "seed": meta["seed"], "fps": fps, "duration": meta["duration"],
              "frames_md5": bench_frames, "audio_md5": hashlib.md5((out / f"{name}.wav").read_bytes()).hexdigest() if want_audio else None}
        (out / f"{name}.benchmark.json").write_text(json.dumps(bj, indent=1))
        print("benchmark ->", out / f"{name}.benchmark.json")
    if not a.preview and not a.no_qc:
        import qc
        rep = qc.run(final, project, name, meta)
        print(qc.summary(rep))
    return final


def compare_grid(videos, labels, out, cols=None):
    """Side-by-side comparison video (labels burned in via PIL-made PNGs, so no font dependency in ffmpeg)."""
    from PIL import Image, ImageDraw
    n = len(videos)
    cols = cols or (n if n <= 3 else math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(videos[0])],
                                      capture_output=True, text=True).stdout)["streams"][0]
    tw = 960 if cols <= 2 else 640
    th = int(tw * probe["height"] / probe["width"]) // 2 * 2
    inputs, filt, lays = [], [], []
    for i, v in enumerate(videos):
        inputs += ["-i", str(v)]
        lab = out.parent / f"_label{i}.png"
        im = Image.new("RGBA", (tw, 34), (0, 0, 0, 170))
        ImageDraw.Draw(im).text((10, 10), labels[i], fill=(255, 255, 255, 255))
        im.save(lab)
        inputs += ["-i", str(lab)]
        filt.append(f"[{2 * i}:v]scale={tw}:{th},setsar=1[v{i}];[v{i}][{2 * i + 1}:v]overlay=0:0[l{i}]")
        lays.append(f"{(i % cols) * tw}_{(i // cols) * th}")
    for i in range(n, rows * cols):
        filt.append(f"color=c=black:s={tw}x{th}:d=1[l{i}]")
        lays.append(f"{(i % cols) * tw}_{(i // cols) * th}")
    fc = ";".join(filt) + ";" + "".join(f"[l{i}]" for i in range(rows * cols)) + f"xstack=inputs={rows * cols}:layout={'|'.join(lays)}:fill=black[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", fc, "-map", "[out]", "-map", "0:a?", "-c:v", "libx264", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    for p in out.parent.glob("_label*.png"):
        p.unlink()
    print("comparison ->", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?")
    ap.add_argument("--stills", nargs="?", const="auto")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 2)))
    ap.add_argument("--fps", type=int)
    ap.add_argument("--scale", type=float)
    ap.add_argument("--range")
    ap.add_argument("--jpeg", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-qc", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--style")
    ap.add_argument("--motion")
    ap.add_argument("--format")
    ap.add_argument("--variants")
    ap.add_argument("--benchmark", action="store_true")
    # internal worker args
    ap.add_argument("--_worker", action="store_true")
    ap.add_argument("--url")
    ap.add_argument("--W", type=int)
    ap.add_argument("--H", type=int)
    ap.add_argument("--f0", type=int)
    ap.add_argument("--f1", type=int)
    ap.add_argument("--segment")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--maxrate", default="14M", help="bitrate cap (grain/noise styles otherwise explode file size); X/Twitter max is 25M")
    a = ap.parse_args()
    if a._worker:
        a.scale = a.scale or 1.0
        return worker(a)
    if not a.project:
        ap.error("project directory required")
    project = Path(a.project).resolve()
    spec = mslib.load_spec(project)
    base = a.name or spec.get("name") or project.name
    if a.benchmark:
        spec["seed"] = spec.get("seed", 1234)
    if a.serve:
        srv, url = mslib.serve(project, mslib.resolve(spec, {"style": a.style, "motion": a.motion, "format": a.format}), port=8765)
        print(f"live preview: {url}/composition.html   (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    if a.variants:
        vids, labels = [], []
        for v in a.variants.split(";"):
            st, _, mo = v.partition(":")
            res = mslib.resolve(spec, {"style": st.strip() or None, "motion": mo.strip() or None, "format": a.format})
            name = f"{base}__{mslib.variant_name(st.strip(), mo.strip() or 'default')}"
            f = run_one(project, res, name, a)
            if f:
                vids.append(f)
                labels.append(f"{st} / {mo or res['motion']['id']}")
        if len(vids) > 1:
            compare_grid(vids, labels, project / "out" / f"{base}__compare.mp4")
        return
    overrides = {"style": a.style, "motion": a.motion, "format": a.format}
    name = base
    if a.style or a.motion or a.format:
        name = f"{base}__{mslib.variant_name(a.style or spec.get('style'), a.motion or spec.get('motion') or 'default')}" + (f"__{a.format.replace(':', 'x')}" if a.format else "")
    if a.benchmark:
        name += "__benchmark"
    if a.preview and a.stills is None:
        name += "__preview"
    run_one(project, mslib.resolve(spec, overrides), name, a)


if __name__ == "__main__":
    main()
