# Three.js Visual Direction

Use this reference to make the game feel authored without spending the whole scope on asset production.

## Start with a visual thesis

Choose one short statement that binds mechanic and world:

> “A courier races through a paper city that folds into ramps as the deadline approaches.”

Derive five decisions from it:

1. **Shape language:** rounded, angular, stacked, sliced, inflated, skeletal, modular.
2. **Palette:** one dominant field, one structural neutral, one gameplay accent, one danger color.
3. **Material family:** matte clay, cut paper, lacquered plastic, emissive wireframe, oxidized metal.
4. **Lighting:** soft studio, theatrical spot, overcast, sunset rim, nocturnal emissive.
5. **Motion signature:** folding, snapping, floating, stretching, orbiting, dissolving.

If an asset does not fit these decisions, restyle it or leave it out.

## Scale and composition

Define world units early. A common convention is one unit ≈ one meter, but consistency matters more than the exact mapping.

- Keep the playable route readable from the chosen camera.
- Exaggerate interactive silhouettes and color contrast.
- Use foreground framing, middle-ground action, and background landmarks to communicate depth.
- Keep hazards visible before they become unavoidable.
- Treat fog and depth of field as composition tools, not as cover for weak layouts.

Graybox first. Tune camera field of view, player speed, jump or turn radius, and obstacle spacing before creating detailed geometry.

## Color management

For ordinary color textures:

```js
renderer.outputColorSpace = THREE.SRGBColorSpace;
colorTexture.colorSpace = THREE.SRGBColorSpace;
```

Do not mark normal, roughness, metalness, displacement, or data textures as sRGB. Keep lighting and tone-mapping choices consistent across scenes; changing them per asset makes the world look patched together.

## Lighting recipes

### Soft diorama

- Hemisphere or ambient fill at low intensity.
- One directional key light with bounded shadows.
- Warm key and cooler environment.
- Contact shadows or a simple blob shadow under critical actors.

### Graphic arcade

- Strong ambient visibility.
- One directional or spot key.
- Emissive accents for objectives and danger.
- Little or no physically accurate darkness; gameplay clarity wins.

### Night exploration

- Low environment level, readable moon or rim light.
- Local point/spot lights only at landmarks and objectives.
- Fog to control depth.
- Exposure tuned so unlit navigation surfaces remain legible.

Avoid adding many shadow-casting point lights. Prefer baked or fake local light cues, emissive materials, projected decals, and carefully placed non-shadow lights.

## Shadows

Use shadows where they explain grounding, height, or danger.

- Limit shadow casters and receivers.
- Fit the directional-light shadow camera tightly to the play area.
- Pick the smallest acceptable shadow-map size.
- Disable shadows on small particles, distant props, and decorative lights.
- Use blob shadows for crowds or mobile scenes when full shadows are too expensive.

## Materials and geometry

Reuse a small material set. Vary color, roughness, scale, and orientation before inventing a new shader.

For procedural low-poly worlds:

- build props from boxes, cylinders, cones, extruded shapes, and instanced pieces;
- bevel only silhouette-critical edges;
- use vertex colors or a small texture atlas;
- make collision geometry simpler than visible geometry;
- group static props by material.

For imported assets:

- normalize scale and forward axis at the boundary;
- audit material count and texture size;
- compress or resize oversized textures;
- preserve author/license attribution;
- provide a clear placeholder if a model fails to load.

## Atmosphere without clutter

Pick one or two:

- height or distance fog;
- slow background particles;
- a restrained color grade;
- subtle animated environment pieces;
- decals for wear or direction;
- a single post-processing signature.

Do not stack bloom, chromatic aberration, film grain, vignette, scanlines, and camera shake by default. Effects should explain energy, impact, speed, damage, or place.

## Particles

Create a visual grammar:

| Event | Shape | Motion | Lifetime |
|:--|:--|:--|:--|
| Pickup | small bright shards | inward spiral | very short |
| Hit | directional chips | away from impact normal | short |
| Dust | soft low-contrast puffs | upward drift | medium |
| Boost | elongated streaks | opposite movement | continuous while active |
| Completion | larger palette accents | radial or upward | long enough to read |

Pool particles. Cap emission and degrade counts at lower quality. Important feedback should still read when particles are disabled.

## DOM UI over WebGL

Use HTML for:

- title, pause, settings, game-over, and accessibility controls;
- crisp score, timer, objectives, prompts, and subtitles;
- responsive layout and touch controls.

Keep the canvas and UI inside one positioned container. Use `pointer-events: none` on passive HUD layers and restore pointer events only on interactive controls.

UI should share the world's palette, type behavior, shape language, and motion timing without becoming a separate dashboard theme.

## Responsive and quality tiers

At minimum support:

- desktop landscape;
- narrow/mobile portrait or a clearly messaged orientation requirement;
- device pixel ratios above 1;
- reduced motion;
- a lower-quality path.

An automatic quality ladder can adjust:

1. pixel ratio;
2. post-processing resolution or removal;
3. shadow map and caster count;
4. particles and decorative animation;
5. draw distance and prop density.

Never remove objectives, hazards, collision, or readable UI as a quality optimization.

## Visual verification

Inspect:

- first frame before assets finish loading;
- brightest and darkest gameplay areas;
- the busiest effects moment;
- pause and game-over overlays;
- mobile controls over real gameplay;
- resized canvas and orientation changes;
- low-quality and reduced-motion modes.

Look for z-fighting, broken normals, wrong color space, texture seams, shadow acne, transparent sorting, clipped UI, unreadable contrast, and a camera that exposes unfinished world edges.
