#!/usr/bin/env python3
"""detect_env.py - inspect the machine and recommend a rendering backend for Motion Studio.

    python3 detect_env.py            human-readable report
    python3 detect_env.py --json     machine-readable

Checks: python libs (playwright, numpy, scipy, PIL), Chromium + WebGL, ffmpeg/ffprobe (+ key filters),
node/npm (for optional libs: three.js, Remotion), Blender, ImageMagick, TTS engines, fonts bundled with the skill.
"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def detect() -> dict:
    d = {"python": sys.version.split()[0], "libs": {}, "tools": {}, "notes": []}
    for lib in ("playwright", "numpy", "scipy", "PIL"):
        try:
            m = importlib.import_module(lib)
            d["libs"][lib] = getattr(m, "__version__", "ok")
        except Exception:  # noqa: BLE001
            d["libs"][lib] = None
    for tool in ("ffmpeg", "ffprobe", "node", "npm", "blender", "convert", "magick", "espeak-ng", "espeak", "piper", "say", "sox"):
        d["tools"][tool] = shutil.which(tool)
    if d["tools"]["ffmpeg"]:
        d["ffmpeg_version"] = run(["ffmpeg", "-version"]).splitlines()[0]
        filt = run(["ffmpeg", "-hide_banner", "-filters"])
        d["ffmpeg_filters"] = {f: (f" {f} " in filt) for f in ("loudnorm", "ebur128", "blackdetect", "freezedetect", "scdet", "xstack")}
    if d["tools"]["node"]:
        d["node_version"] = run(["node", "--version"])
    d["chromium"], d["webgl"] = None, None
    if d["libs"]["playwright"]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page()
                d["chromium"] = b.version
                d["webgl"] = pg.evaluate("""() => { const c = document.createElement('canvas'); const g = c.getContext('webgl2') || c.getContext('webgl');
                    if (!g) return null; const e = g.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'webgl'; }""")
                b.close()
        except Exception as e:  # noqa: BLE001
            d["notes"].append(f"playwright installed but Chromium failed to launch: {e}")
    fonts = sorted({p.name.split("-latin")[0] for p in (SKILL / "engine" / "fonts").glob("*.woff2")})
    d["bundled_fonts"] = fonts
    # recommendation
    ok_core = d["libs"]["playwright"] and d["chromium"] and d["tools"]["ffmpeg"]
    rec = []
    if ok_core:
        rec.append("html: HTML/SVG/Canvas scenes in headless Chromium -> FFmpeg (default for type, UI, charts, 2.5D, particles)")
        if d["webgl"]:
            rec.append("three: WebGL/Three.js inside the same page for true 3D (scripts/vendor.py three)" + (" - software GL, keep scenes light" if "SwiftShader" in str(d["webgl"]) else ""))
    else:
        rec.append("MISSING CORE: pip install playwright numpy scipy pillow && playwright install chromium; install ffmpeg")
    if d["tools"]["ffmpeg"]:
        rec.append("ffmpeg: compositing, concatenation, captions over existing footage, audio mux + loudness")
    if d["tools"]["blender"]:
        rec.append("blender: photoreal 3D (render frames with blender -b, composite with ffmpeg)")
    if d["tools"]["npm"]:
        rec.append("remotion: only if the user's repo already uses it (npm i remotion @remotion/cli; point it at the same Chromium)")
    tts = [t for t in ("piper", "espeak-ng", "espeak", "say") if d["tools"].get(t)]
    d["tts"] = tts
    if not tts:
        d["notes"].append("no text-to-speech engine: voice-over needs a recorded file (spec.audio.voiceover); captions are always burned in")
    d["recommendation"] = rec
    return d


def main():
    d = detect()
    if "--json" in sys.argv:
        print(json.dumps(d, indent=1))
        return
    print("Motion Studio environment")
    print(f"  python {d['python']}  libs: " + ", ".join(f"{k}={'ok' if v else 'MISSING'}" for k, v in d["libs"].items()))
    print(f"  chromium: {d['chromium'] or 'MISSING'}   webgl: {d['webgl'] or 'none'}")
    print(f"  ffmpeg: {d.get('ffmpeg_version', 'MISSING')}")
    if d.get("ffmpeg_filters"):
        print("    filters: " + ", ".join(f"{k}{'' if v else ' (missing)'}" for k, v in d["ffmpeg_filters"].items()))
    for t in ("node", "npm", "blender", "convert"):
        print(f"  {t}: {d['tools'][t] or '-'}")
    print(f"  TTS: {', '.join(d['tts']) or 'none'}")
    print(f"  bundled fonts: {len(d['bundled_fonts'])} families")
    print("Recommended backends:")
    for r in d["recommendation"]:
        print("  - " + r)
    for n in d["notes"]:
        print("NOTE: " + n)


if __name__ == "__main__":
    main()
