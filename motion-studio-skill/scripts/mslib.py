"""Shared helpers for Motion Studio scripts: registries, spec resolution, style/motion blending, local server."""
from __future__ import annotations

import copy
import functools
import http.server
import json
import re
import socketserver
import threading
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ENGINE = SKILL / "engine"
STYLE_DIR = SKILL / "styles" / "visual"
MOTION_FILE = SKILL / "styles" / "motion" / "motion.json"
FORMATS_FILE = SKILL / "styles" / "formats.json"
TEMPLATE_DIR = SKILL / "templates"


# ------------------------------------------------------------------ registries
@functools.lru_cache(maxsize=1)
def styles() -> dict:
    out = {}
    for f in sorted(STYLE_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for s in data["styles"]:
            s = dict(s)
            s["_file"] = f.name
            out[s["id"]] = s
    return out


@functools.lru_cache(maxsize=1)
def motions() -> dict:
    return {m["id"]: m for m in json.loads(MOTION_FILE.read_text(encoding="utf-8"))["motions"]}


@functools.lru_cache(maxsize=1)
def templates() -> dict:
    return {json.loads(f.read_text(encoding="utf-8"))["id"]: json.loads(f.read_text(encoding="utf-8")) for f in sorted(TEMPLATE_DIR.glob("*.json"))}


@functools.lru_cache(maxsize=1)
def formats() -> dict:
    return json.loads(FORMATS_FILE.read_text(encoding="utf-8"))


def norm(text: str) -> str:
    t = text.lower().replace("’", "'")
    t = re.sub(r"[_]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------ blending
STYLE_LOOK_KEYS = ("palette", "glow")                    # what a secondary style contributes
MOTION_SIGNATURE_KEYS = ("glitch", "jitter", "step_fps", "blur")


def split_ids(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [x.strip() for x in re.split(r"\s*\+\s*", str(value)) if x.strip()]


def blend_styles(ids: list[str]) -> dict:
    """Primary owns structure (fonts, type, background, radius, textures, transitions); secondaries add palette mood,
    extra textures, preferred transitions and sound mood.  Max 3 styles."""
    reg = styles()
    for i in ids:
        if i not in reg:
            raise SystemExit(f"unknown style '{i}' (see plan.py --list styles)")
    base = copy.deepcopy(reg[ids[0]])
    base["blend"] = ids[1:3]
    for sid in ids[1:3]:
        s = reg[sid]
        base["palette"] = dict(base["palette"], **{k: v for k, v in s["palette"].items() if k in ("bg", "bg2", "surface", "accent", "accent2", "accent3", "muted")})
        base["glow"] = max(base.get("glow", 0), s.get("glow", 0))
        tex = {t.split(":")[0]: t for t in base.get("texture", [])}
        for t in s.get("texture", []):
            k = t.split(":")[0]
            if k not in tex and k not in ("letterbox",):
                tex[k] = t
        base["texture"] = list(tex.values())
        base["transitions"]["prefer"] = list(dict.fromkeys(base["transitions"]["prefer"] + s["transitions"]["prefer"][:2]))
        base["transitions"]["avoid"] = [x for x in dict.fromkeys(base["transitions"]["avoid"] + s["transitions"]["avoid"]) if x not in base["transitions"]["prefer"][:3]]
        base["sound"] = dict(base["sound"], mood=(base["sound"].get("mood", "") + " " + s["sound"].get("mood", "")).strip())
        if s["sound"]["music"] in ("horror", "cinematic") and base["sound"]["music"] not in ("horror",):
            base["sound"]["music_alt"] = s["sound"]["music"]
    base["id"] = "+".join(ids)
    return base


def blend_motions(ids: list[str]) -> dict:
    """Primary owns easing, durations, stagger, pacing; secondaries add their signature channels
    (glitch, jitter, stepping, blur, shake/handheld) and preferred transitions."""
    reg = motions()
    for i in ids:
        if i not in reg:
            raise SystemExit(f"unknown motion '{i}' (see plan.py --list motion)")
    base = copy.deepcopy(reg[ids[0]])
    for mid in ids[1:3]:
        m = reg[mid]
        for k in MOTION_SIGNATURE_KEYS:
            base[k] = max(base.get(k, 0), m.get(k, 0))
        for k in ("shake", "handheld"):
            base["camera"][k] = max(base["camera"].get(k, 0), m["camera"].get(k, 0))
        base["transitions"]["prefer"] = list(dict.fromkeys(m["transitions"]["prefer"][:2] + base["transitions"]["prefer"]))
        base["transitions"]["avoid"] = [x for x in base["transitions"]["avoid"] if x not in m["transitions"]["prefer"][:2]]
    base["id"] = "+".join(ids)
    return base


# ------------------------------------------------------------------ spec
def load_spec(project: Path) -> dict:
    p = project / "spec.json"
    if not p.exists():
        raise SystemExit(f"{p} not found - create a project with plan.py --scaffold")
    return json.loads(p.read_text(encoding="utf-8"))


def resolve(spec: dict, overrides: dict | None = None) -> dict:
    """Turn a project spec (ids, format) into the fully resolved object the engine receives as window.MS_SPEC."""
    s = copy.deepcopy(spec)
    for k, v in (overrides or {}).items():
        if v is not None:
            s[k] = v
    fm = formats()["formats"]
    fmt = s.get("format", "16:9")
    if fmt in fm:
        s.setdefault("width", fm[fmt]["width"])
        s.setdefault("height", fm[fmt]["height"])
        if overrides and "format" in overrides:
            s["width"], s["height"] = fm[fmt]["width"], fm[fmt]["height"]
        s.setdefault("safe", fm[fmt]["safe"])
    s.setdefault("width", 1920)
    s.setdefault("height", 1080)
    s.setdefault("fps", 30)
    s.setdefault("seed", 1234)
    style_ids = split_ids(s.get("style") or "minimal")
    motion_ids = split_ids(s.get("motion")) or [styles()[style_ids[0]]["motion_default"]]
    st = blend_styles(style_ids)
    mo = blend_motions(motion_ids)
    s["style_ids"], s["motion_ids"] = style_ids, motion_ids
    s["style"], s["motion"] = st, mo
    audio = s.setdefault("audio", {})
    s.setdefault("bpm", audio.get("bpm") or st["sound"]["bpm"])
    audio.setdefault("music", "auto")
    audio.setdefault("sfx", True)
    audio.setdefault("lufs", -14)
    if audio.get("features"):
        audio["features_url"] = "/" + audio["features"].lstrip("/")
    return s


def variant_name(style, motion) -> str:
    return re.sub(r"[^a-z0-9+-]+", "-", f"{style}__{motion}".lower()).replace("+", "-")


# ------------------------------------------------------------------ local server
class _Handler(http.server.SimpleHTTPRequestHandler):
    project: Path = Path(".")
    spec_js: bytes = b""

    def log_message(self, *a):
        pass

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/engine/"):
            return str(ENGINE / path[len("/engine/"):])
        return str(self.project / path.lstrip("/"))

    def do_GET(self):
        if self.path.split("?")[0] == "/engine/ms.js":          # engine + user extensions (engine/extensions/*.js)
            body = (ENGINE / "ms.js").read_bytes()
            for f in sorted((ENGINE / "extensions").glob("*.js")) if (ENGINE / "extensions").exists() else []:
                body += b"\n;/* extension: " + f.name.encode() + b" */\n" + f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.split("?")[0] == "/__spec.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(self.spec_js)))
            self.end_headers()
            self.wfile.write(self.spec_js)
            return
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve(project: Path, resolved: dict, port: int = 0):
    """Serve the project dir + /engine + /__spec.js on localhost; returns (server, base_url)."""
    handler = type("H", (_Handler,), {"project": project.resolve(), "spec_js": ("window.MS_SPEC = " + json.dumps(resolved) + ";").encode()})
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
