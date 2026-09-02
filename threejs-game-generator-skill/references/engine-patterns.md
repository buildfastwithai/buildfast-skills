# Three.js Engine Patterns

Use these patterns when the project needs a foundation or when an existing foundation is causing control, timing, lifecycle, or performance bugs. Adapt them to the current stack instead of copying them blindly.

## Project shape

A small game benefits from explicit ownership without becoming an engine:

```text
src/
├── main.js
├── game/
│   ├── Game.js
│   ├── Input.js
│   ├── State.js
│   └── Save.js
├── world/
│   ├── createWorld.js
│   └── collisions.js
├── entities/
├── ui/
└── styles.css
```

Keep the renderer, scene, active camera, clock, resource registry, and game state owned by one `Game` boundary. Entity modules receive the dependencies they need; they should not import a global renderer.

## Renderer and resize

```js
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  powerPreference: 'high-performance',
});

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.querySelector('#game').append(renderer.domElement);

const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 500);

function resize() {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  if (renderer.domElement.width !== width || renderer.domElement.height !== height) {
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  }
}
```

Cap pixel ratio deliberately. A phone at 3× or 4× density can spend most of the frame budget drawing pixels the player cannot distinguish.

## Animation and simulation

Use one authoritative loop. `setAnimationLoop` also leaves a clean path to WebXR:

```js
const clock = new THREE.Clock();
const FIXED_STEP = 1 / 60;
let accumulator = 0;

function frame() {
  resize();
  const frameDelta = Math.min(clock.getDelta(), 0.1);
  accumulator += frameDelta;

  input.sample();
  while (accumulator >= FIXED_STEP) {
    game.fixedUpdate(FIXED_STEP, input.actions);
    accumulator -= FIXED_STEP;
  }

  game.updatePresentation(frameDelta, accumulator / FIXED_STEP);
  renderer.render(scene, camera);
}

renderer.setAnimationLoop(frame);
```

Use a capped variable delta for simple visual experiences. Use the fixed step for collision-heavy movement, replays, or mechanics where inconsistent frame rates change results. Pause or reset the clock when the page loses focus so the next frame does not contain a huge delta.

## State machine

Prefer one explicit state over many flags:

```js
const GameState = Object.freeze({
  LOADING: 'loading',
  READY: 'ready',
  PLAYING: 'playing',
  PAUSED: 'paused',
  WON: 'won',
  LOST: 'lost',
});
```

Route transitions through one function. It should control input capture, pointer lock, audio, UI visibility, and the simulation clock. Reject impossible transitions and make restart reset every run-owned value.

## Input actions

Map physical inputs to semantic actions:

```js
const actions = {
  moveX: 0,
  moveY: 0,
  lookX: 0,
  lookY: 0,
  primary: false,
  pausePressed: false,
};
```

Keep “held,” “pressed this frame,” and “released this frame” separate. Pointer, keyboard, gamepad, and touch adapters should write the same action shape. Clear transient input on blur and when opening a menu.

For pointer lock:

- request it only from an explicit user gesture;
- show the escape/pause behavior before capture;
- treat lock loss as pause, not as continued movement;
- keep a non-pointer-lock path for menus and touch devices.

## Movement and collision

Choose collision fidelity from the mechanic:

- **Sphere or capsule against simple world volumes:** character movement, pickups, arcade enemies.
- **Raycasts:** ground checks, aiming, interaction, line of sight, vehicle suspension.
- **Spatial grid or octree:** many static obstacles or many nearby entities.
- **Physics library:** stacked rigid bodies, joints, rolling objects, or simulation-driven puzzles.

Use `Box3`, `Sphere`, rays, and squared distances for broad-phase tests. Reuse scratch vectors:

```js
const desired = new THREE.Vector3();
const forward = new THREE.Vector3();

function updateMovement(dt) {
  camera.getWorldDirection(forward);
  forward.y = 0;
  forward.normalize();
  desired.set(actions.moveX, 0, actions.moveY);
  // Transform desired input into camera-relative world motion, then resolve collision.
}
```

Do not create new vectors for every entity every frame. Allocate scratch objects once or keep them on the owning system.

For character controllers:

- separate horizontal acceleration from gravity;
- use a ground probe and a small snap distance;
- resolve penetration before applying the next step;
- cap slope angle and step height explicitly;
- keep camera smoothing independent of collision resolution.

## Camera patterns

### Follow camera

Compute a target position from the player, then damp toward it. Raycast from the player anchor to the desired camera position and pull the camera forward when geometry blocks the path.

### Orbit or diorama camera

Constrain polar angle, distance, and zoom. Keep the playfield within known bounds and ensure pointer gestures do not conflict with game actions.

### First-person camera

Separate yaw from pitch, clamp pitch, and apply movement using yaw only. Pointer lock loss should pause the game.

Avoid parenting the camera directly to a jittery physics body. Follow an interpolated visual anchor instead.

## Loading and asset ownership

Load required assets before entering `READY`. Show progress and a useful failure message. With `GLTFLoader`, clone scenes or skinned models using the appropriate utilities instead of reusing one live hierarchy in multiple places.

Track ownership:

- shared geometries, materials, and textures live in a resource registry;
- entity instances reference shared resources;
- scene-specific resources are disposed when leaving that scene;
- object URLs, event listeners, intervals, and audio nodes are released with the scene that created them.

Disposing a mesh means disposing its unique geometry/material/texture resources and removing references; removing it from the scene alone does not free GPU memory.

## Pooling and hot-loop discipline

Pool short-lived objects such as projectiles, impact decals, floating labels, and particles once profiling shows churn.

Inside hot loops:

- reuse vectors, matrices, colors, rays, and result arrays;
- skip distant or inactive entities;
- avoid DOM writes unless a displayed value changed;
- group identical geometry/material with `InstancedMesh`;
- merge static geometry where culling and editing requirements allow it;
- avoid traversing the entire scene graph for per-frame gameplay queries.

## Persistence

Store a small versioned document:

```json
{
  "version": 1,
  "settings": { "music": 0.6, "effects": 0.8, "quality": "auto" },
  "progress": { "bestScore": 12400, "unlockedLevel": 3 }
}
```

Wrap reads and writes in `try/catch`. Validate types, ignore unknown fields, and fall back to defaults when data is corrupt. Save settings and milestone progress, not an enormous live scene graph.

## Performance triage

Measure the busiest gameplay moment. Reduce cost in this order:

1. cap pixel ratio and post-processing resolution;
2. reduce shadow-map size, shadow casters, and expensive lights;
3. reduce draw calls through reuse and instancing;
4. reduce transparent overdraw and particle count;
5. reduce simulation frequency for distant or inactive systems;
6. lower model and texture complexity.

Keep gameplay readability, collision, and input responsiveness before decorative fidelity.
