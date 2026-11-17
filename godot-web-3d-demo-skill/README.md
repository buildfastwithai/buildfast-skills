<div align="center">

# Godot Web 3D Demo

**Turn a one-line idea into a short, cinematic Godot 4 demo that runs in the browser and looks far better than it has any right to.**

[Why it exists](#why-this-exists) · [What you get](#what-you-get) · [Use it](#use-it) · [Browse all skills](../README.md)

<br>

<code>npx skills add buildfastwithai/buildfast-skills --skill godot-web-3d-demo-skill</code>

</div>

---

## Why this exists

Godot's web export runs only on the Compatibility renderer (WebGL 2). Scenes built with desktop features — SSR, SDFGI, volumetric fog — look great in the editor and flat in the browser. This skill designs for the browser from the first line, fakes the missing effects with shaders and emissive glow, and spends its effort where demos are judged: lighting, motion, atmosphere, and feel.

It builds a 30–90 second vertical slice, not a full game. One scene, one signature effect, one interaction, a lot of polish.

## What you get

- A 5-line creative brief: hero shot, mood, beat sheet, interaction, signature effect.
- A GDScript-built Godot 4 project set up for Compatibility and single-threaded web export.
- Procedural assets (no downloads needed): noise terrain, MultiMesh instancing, GPU particles, custom shaders.
- A layered visual pass: sky, AgX tonemapping, glow, fog, SSAO, rim and emissive shaders, subtle post-processing.
- A cinematic camera intro, smoothed controls, micro-motion, and interaction feedback.
- Shader pre-warming, a "click to begin" audio unlock, a title card, and an end beat.
- Verification by rendered frames, plus the web build zip, the project zip, and a preview MP4.

## Use it

```bash
npx skills add buildfastwithai/buildfast-skills --skill godot-web-3d-demo-skill
```

Then describe the vibe and the one thing it should show off:

```text
Use godot-web-3d-demo-skill to build a bioluminescent cave demo:
glowing crystal veins, drifting spores, click to pulse light through the cave.
```

## Good fits

- Tech demos and visual showcases for a portfolio, itch.io, or social posts.
- "Wow" first-impression scenes to pitch a game idea.
- Making an existing Godot scene look good on the web.

Need a complete playable game loop instead? Use **[Three.js Game Generator](../threejs-game-generator-skill/)**.
