---
name: godot-web-3d-demo-skill
description: Build short, polished 3D browser demos with Godot 4 and its web export — cinematic, visually striking vertical slices rather than full games. Use when a user wants a Godot 3D demo, showcase, tech demo, visual prototype, or "wow" scene that runs in the browser, or wants an existing Godot scene to look better on web. Do not trigger for complete playable games with progression (use threejs-game-generator-skill for Three.js games), 2D Godot projects, or non-Godot 3D work.
license: MIT
metadata:
  category: game-development
  engine: godot
---

# Godot 3D Web Demos

The goal is a **30–90 second piece that makes people say "wait, that's running in a browser?"** — not a complete game. One scene, one strong idea, a little interaction, and a lot of polish beats a big feature list every time. Spend effort on lighting, motion, atmosphere, and feel; skip menus, save systems, inventories, and multiple levels.

## 0. Hard facts that shape everything

- **Web export only runs on the Compatibility renderer (WebGL 2).** Forward+ and Mobile do not run in the browser. Design for Compatibility from minute one, or the scene will look great in the editor and flat in the browser.
- In Godot 4.7, Compatibility **has**: glow/bloom, tonemapping (AgX/Filmic/ACES), depth + height fog, SSAO, MSAA 3D, ReflectionProbes (max 2 per mesh), LightmapGI, GPU particles, custom shaders, fullscreen post-process quads, color adjustments.
- Compatibility **lacks**: SSR, SSIL, SDFGI, VoxelGI, volumetric fog/FogVolumes, light projectors. Fake them (see §4). Feature support grows each release — if a feature matters, check the "Overview of renderers" table in the docs for the installed version.
- Lights are forward-rendered with per-object limits: one shadowed DirectionalLight3D plus a few unshadowed omni/spot lights. Lean on emissive materials + glow for "lots of lights".
- Use a **single-threaded** web export (the default since 4.3): works on any static host, no special headers.
- C# projects can't export to web — **use GDScript.**
- Browsers block audio until a user gesture — a "Click to begin" overlay is mandatory and doubles as a dramatic opening.

## 1. Pick the demo concept (before any code)

Write a 5-line brief and share it with the user if they're around:

1. **Hero image** — the single frame that would be the thumbnail.
2. **Mood** — palette (2–3 key colors + one accent), time of day, weather.
3. **Beat sheet** — fade-in → reveal → interaction → climax → loop/end card.
4. **Interaction** — one verb only (orbit/look, steer, click-to-trigger, hold-to-charge).
5. **Signature effect** — the one thing that's technically impressive (shader water, 50k instanced grass, particle storm, dissolve shader, light trails).

Concepts that read well in Compatibility: neon synthwave flythrough with light trails; floating island at golden hour with drifting pollen; bioluminescent cave with glowing crystal veins; stormy sea and lighthouse beam; low-poly planet with orbiting ships; a museum pedestal object with hologram/dissolve shaders; hover-bike skimming a desert canyon.

If the user's idea needs SSR/volumetrics/GI, reinterpret it with fakes rather than abandoning it, and say so in one line.

## 2. Toolchain setup (Linux sandbox)

Check for `godot` first. If missing, get the latest **stable** 4.x from GitHub releases (look up the current tag via `https://api.github.com/repos/godotengine/godot/releases/latest`; don't hard-code a version):

```bash
VER=4.7.2   # replace with the latest stable tag found above
mkdir -p ~/godot && cd ~/godot
curl -LO https://github.com/godotengine/godot/releases/download/${VER}-stable/Godot_v${VER}-stable_linux.x86_64.zip
curl -LO https://github.com/godotengine/godot/releases/download/${VER}-stable/Godot_v${VER}-stable_export_templates.tpz
unzip -o Godot_v${VER}-stable_linux.x86_64.zip
ln -sf ~/godot/Godot_v${VER}-stable_linux.x86_64 /usr/local/bin/godot
TPL=~/.local/share/godot/export_templates/${VER}.stable
mkdir -p "$TPL" && unzip -o Godot_v${VER}-stable_export_templates.tpz -d /tmp/tpl && cp /tmp/tpl/templates/* "$TPL"/
godot --version
```

On Windows/macOS with Godot already installed, use the installed editor and its Export Template Manager instead.

For rendering previews you also want `xvfb` and Mesa GL (`xvfb-run`, `libgl1-mesa-dri`) plus `ffmpeg`; install if apt is reachable. If not, fall back to browser screenshots (§6) or ask the user to open the build.

## 3. Project skeleton

**Build the scene in GDScript, not in hand-written .tscn.** Hand-authored scene files with sub-resources are fragile to write as text. A tiny `main.tscn` whose root runs `main.gd` — which constructs environment, lights, meshes, materials, particles, and camera in `_ready()` — is robust, diffable, and easy to iterate. Split into a few scripts once it grows (`world.gd`, `camera_rig.gd`, `fx.gd`, `ui.gd`).

```
demo/
  project.godot
  export_presets.cfg
  main.tscn          # root Node3D with main.gd attached
  main.gd
  scripts/*.gd
  shaders/*.gdshader
  build/web/         # export output
```

`project.godot`:

```ini
config_version=5

[application]
config/name="Demo"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")

[display]
window/size/viewport_width=1920
window/size/viewport_height=1080
window/stretch/aspect="expand"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
anti_aliasing/quality/msaa_3d=2
textures/vram_compression/import_etc2_astc=true
```

`main.tscn`:

```
[gd_scene load_steps=2 format=3]
[ext_resource type="Script" path="res://main.gd" id="1"]
[node name="Main" type="Node3D"]
script = ExtResource("1")
```

`export_presets.cfg`:

```ini
[preset.0]
name="Web"
platform="Web"
runnable=true
export_filter="all_resources"
export_path="build/web/index.html"

[preset.0.options]
variant/thread_support=false
variant/extensions_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=true
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/head_include="<style>body{background:#000}</style>"
```

If export complains about option keys, read the error, fix the key for that version, and keep going.

## 4. The quality playbook

Work through these in order — each layer multiplies the previous one; skipping early layers can't be rescued by later ones.

### 4.1 Light and atmosphere first

```gdscript
var env := Environment.new()
env.background_mode = Environment.BG_SKY
var sky_mat := ProceduralSkyMaterial.new()   # or a custom sky shader for stylized looks
sky_mat.sky_top_color = Color("1b2a4a")
sky_mat.sky_horizon_color = Color("f2a35e")
sky_mat.ground_horizon_color = Color("f2a35e")
sky_mat.ground_bottom_color = Color("0d0f1a")
var sky := Sky.new(); sky.sky_material = sky_mat
env.sky = sky
env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
env.tonemap_mode = Environment.TONE_MAPPER_AGX
env.glow_enabled = true
env.glow_intensity = 0.9
env.glow_bloom = 0.08
env.glow_hdr_threshold = 1.0      # only emissive > 1.0 blooms — keeps it tasteful
env.fog_enabled = true
env.fog_light_color = Color("c98a5a")
env.fog_density = 0.012
env.fog_sky_affect = 0.6
env.fog_height = 2.0
env.fog_height_density = 0.15
env.ssao_enabled = true            # Compatibility 4.7+; check if older
env.adjustment_enabled = true
env.adjustment_contrast = 1.08
env.adjustment_saturation = 1.1
var we := WorldEnvironment.new(); we.environment = env; add_child(we)

var sun := DirectionalLight3D.new()
sun.rotation_degrees = Vector3(-18, 35, 0)  # low sun = long shadows = drama
sun.light_color = Color("ffd2a1")
sun.light_energy = 1.4
sun.shadow_enabled = true
add_child(sun)
```

Rules of thumb: low sun angles, warm key vs. cool ambient (or the reverse), fog to separate depth layers, emissive accents at 2–6 energy so glow picks them up. Keep a strong silhouette in the hero shot.

### 4.2 Assets: procedural, no downloads needed

The sandbox usually can't fetch asset libraries, and procedural work looks intentional:

- **Primitives + good materials** (`BoxMesh`, `SphereMesh`, `CylinderMesh`, `TorusMesh`, `PrismMesh`) composed into props; roughness variation and rim lighting do the rest.
- **SurfaceTool / ArrayMesh** for terrain (displace a `PlaneMesh` grid with `FastNoiseLite`), rocks (noise-displaced icospheres), ribbons/trails.
- **NoiseTexture2D** (seamless, normal-map mode) for albedo/normal/roughness detail.
- **MultiMeshInstance3D** for anything numerous — grass, debris, stars, crystals, city blocks. Thousands of instances at one draw call. Vary per-instance scale/rotation/color (`use_colors = true`).
- Low-poly flat-shaded is a valid style — commit to one style, don't mix.

If the user supplies glTF models, import them and still do the lighting pass.

### 4.3 Shaders that sell it (all Compatibility-safe)

Write small `spatial` shaders for the signature effect. Useful staples:

- **Fresnel rim/emissive glow**: `EMISSION = rim_color * pow(1.0 - dot(NORMAL, VIEW), rim_power) * energy;`
- **Dissolve/reveal**: noise texture vs. animated threshold, emissive edge band (`smoothstep`), driven by a Tween.
- **Stylized water**: vertex waves (sum of sines), depth-based color via `DEPTH_TEXTURE` (`hint_depth_texture`), fresnel tint, scrolling normal noise, foam from depth difference — replaces SSR.
- **Hologram**: scanlines from `world y + TIME`, flicker, additive (`render_mode blend_add, unshaded`).
- **Wind sway** on grass/trees: offset `VERTEX.xz` by `sin(TIME + world_pos)` weighted by `UV.y`.
- **God rays / volumetric fakes**: additive, unshaded cone or quad meshes with soft-edged noise alpha, plus GPU particle dust inside the beam.
- **Fake GI**: emissive surfaces + a few unshadowed low-energy OmniLight3Ds in their color; bake LightmapGI only if the scene is static and baking works headless.
- **Post-process**: fullscreen `MeshInstance3D` quad (or `ColorRect` with a `canvas_item` shader on a CanvasLayer) for vignette, chromatic aberration, film grain, subtle color LUT. Subtle — heavy post looks cheap.

### 4.4 Motion is half the quality

A static camera kills a demo. Build a camera rig:

- **Cinematic intro**: a Tween or `Path3D` + `PathFollow3D` dolly over 4–8 s with ease-in-out (`Tween.TRANS_SINE`, `EASE_IN_OUT`), ending on the hero framing.
- **Then hand control over** with smoothing: orbit/look with `lerp`/`slerp` toward targets (`1.0 - exp(-k * delta)` for frame-rate-independent damping). Never snap.
- **Micro-motion everywhere**: idle bobbing, slow rotation, drifting particles, breathing emissive pulses (`sin(TIME)`), subtle camera noise sway from `FastNoiseLite`.
- **Juice on interaction**: FOV kick, short camera shake, light flash, particle burst, time slow (`Engine.time_scale`) for 0.2 s, a sound.

### 4.5 Particles

`GPUParticles3D` with `ParticleProcessMaterial`: dust motes, embers, sparks, rain, pollen, warp streaks. Small emissive quads (`QuadMesh` with billboard material) so glow catches them. Turbulence on, gentle gravity, color ramp to fade out. Budget a few thousand, not 100k.

### 4.6 Framing, UI, sound

- **Title card**: fade from black, demo name in a clean font with letter-spacing, a one-line hint ("Drag to look · Click to ignite"), fade out.
- **"Click to begin" overlay** that unlocks audio and starts the intro.
- **End beat**: after the climax, a slow pull-back and a soft end card, or a seamless loop.
- **Audio**: generate an ambient drone or whoosh procedurally (`AudioStreamGenerator`) or use a user-provided file. Even a simple low drone makes it feel finished.
- Minimal HUD. No debug text in the final build.

## 5. Web performance and loading

- Target **60 fps on a mid-range laptop's integrated GPU**. Watch draw calls (MultiMesh!), shadow-casting lights (one), overdraw from big transparent particles, and particle counts.
- MSAA 4x is fine for small scenes; drop to 2x or `scaling_3d_scale` 0.8 if heavy.
- **Shader compile hitches** are the #1 thing that ruins first impressions on web. Pre-warm: during the black "click to begin" screen, put every material/particle system in front of the camera for a few frames (behind the overlay), then move them into place.
- Keep the `.pck` small: procedural assets, compressed textures, no unused imports.
- Expect the engine `.wasm` to be tens of MB — normal; the default shell shows a loading bar.

## 6. Build, look, iterate (don't skip)

You can't judge visuals from code. Look at real frames after every significant change.

```bash
cd demo
godot --headless --path . --import
# Render preview frames with Movie Maker under a virtual display (same renderer as web):
mkdir -p /tmp/frames
xvfb-run -s "-screen 0 1920x1080x24" godot --path . \
  --rendering-method gl_compatibility --rendering-driver opengl3 \
  --write-movie /tmp/frames/f.png --fixed-fps 30 --quit-after 360
```

- View 4–6 frames spread across the timeline (intro, hero shot, interaction moment, climax). Critique like an art director: clear focal point? good value range (true darks, bright highlights)? glow tasteful, not smeary? fog separating layers? any flat untextured surfaces, z-fighting, black materials, or shader errors?
- Read Godot's stdout/stderr for script and shader errors; fix all of them, including warnings about features missing in Compatibility.
- Simulate interaction in previews with a `--demo-autoplay` user arg (`OS.get_cmdline_user_args()`) that triggers the input beats on a timer.
- Make an MP4 preview the user can watch anywhere: `ffmpeg -framerate 30 -i /tmp/frames/f%08d.png -c:v libx264 -preset veryfast -pix_fmt yuv420p preview.mp4`.

Then export and smoke-test the real web build:

```bash
mkdir -p build/web
godot --headless --path . --export-release "Web" build/web/index.html
cd build/web && python3 -m http.server 8060
```

If a browser is available (built-in browser, Chrome extension, or headless Chromium/Playwright with SwiftShader), load it, click to begin, screenshot, and check the console for errors.

Do at least **two polish passes** after the first working version. The first pass makes it work; the polish passes make it terrific. Typical polish targets: stronger lighting contrast, a foreground element for depth, more micro-motion, a better camera end pose, a nicer title card.

## 7. Deliver

- **Zip of `build/web/`** — ready to drop on itch.io (HTML5 project) or any static host. Mention it must be served over HTTP, not opened as `file://`.
- **Zip of the Godot project** so they can open it in the editor.
- **`preview.mp4`** and 1–2 hero screenshots.
- A short note: controls, the signature effect, and one idea for what to push next.

## GDScript 4 gotchas

- `@onready`, `@export`, typed vars (`var speed: float = 3.0`), `:=` inference.
- Tweens: `var t := create_tween(); t.tween_property(cam, "position", target, 4.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)`.
- Input: override `_unhandled_input(event)`; mouse look uses `InputEventMouseMotion.relative`. On web, `Input.mouse_mode = Input.MOUSE_MODE_CAPTURED` only works after a click.
- `MultiMesh.transform_format = MultiMesh.TRANSFORM_3D` must be set **before** `instance_count`.
- Materials in code: `StandardMaterial3D.new()`; emission needs `emission_enabled = true`, then `emission` and `emission_energy_multiplier`.
- `ShaderMaterial.set_shader_parameter("name", value)` (not `set_shader_param`).
- Godot 3 tutorials (KinematicBody, `yield`, `instance()`) are wrong for 4.x — use CharacterBody3D, `await`, `instantiate()`.
