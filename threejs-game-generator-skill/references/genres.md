# Three.js Genre Decisions

Use this reference to choose a viable 3D mechanic set and avoid genre-specific scope traps.

## Selection table

| Genre shape | Camera | First complete loop | Primary technical risk |
|:--|:--|:--|:--|
| Third-person collectathon | damped chase camera | collect targets while avoiding one hazard, then reach exit | camera collision and character grounding |
| First-person exploration | pointer-lock camera | find/activate a short sequence and escape | input capture, level readability, motion comfort |
| Diorama strategy | fixed orbit/orthographic | place or command units through one encounter | selection, pathing, and readable scale |
| Endless runner | forward/rail camera | dodge, collect, speed up, fail, restart | object recycling and mobile controls |
| Arcade driving | chase camera | finish a timed route or survive traffic | vehicle feel without overbuilding physics |
| Physics puzzle | fixed or orbit camera | solve three escalating rooms | deterministic reset and stable rigid bodies |
| Arena survival | high chase/isometric | survive waves, collect upgrades, defeat a boss | crowd performance and feedback saturation |
| Hover/flight game | chase or cockpit | pass gates or deliver an object under time pressure | readable 3D navigation and orientation |

Lead with one loop that can be completed in minutes. Add content only after restart is reliable and the loop feels good.

## Third-person action or collectathon

Minimum:

- capsule or simple character controller;
- camera-relative movement;
- ground probe, slope/step rules, and coyote time if jumping;
- chase camera with collision avoidance;
- one obstacle family, one collectible family, one endpoint;
- clear damage/failure and restart.

Do not begin with animation blending, an equipment system, quests, and a large imported world. Prove movement and camera in a graybox.

## First-person exploration

Minimum:

- explicit Start action and pointer-lock explanation;
- yaw/pitch look with clamped pitch;
- grounded movement and collision;
- interaction ray with a visible prompt;
- a small landmark-driven environment;
- pause on pointer-lock loss;
- non-audio clue for every critical sound.

Reduce head bob and field-of-view effects when reduced motion is enabled. Avoid narrow collision mazes until movement comfort is proven.

## Diorama strategy

Minimum:

- bounded board with a stable camera;
- pointer/touch selection using raycasting;
- placement preview or command feedback;
- one resource or cooldown;
- a single encounter with readable win/loss;
- clear team colors and selection states.

Keep unit count small until pathing and selection remain responsive. Use simple steering or grid navigation before adopting a complex navigation stack.

## Endless runner

Minimum:

- three lanes or one continuous lateral axis;
- jump, dodge, or lane change;
- chunk spawning and recycling;
- readable obstacle telegraphing;
- score/distance, escalating pace, failure, instant restart;
- touch swipes or large virtual controls.

Recycle chunks and props. Never let random generation create unavoidable obstacle combinations; validate a safe path.

## Arcade driving

Choose the feel first:

- **Kinematic arcade:** direct speed/steering model, raycast suspension or ground following, predictable drift.
- **Rigid-body:** use when collisions, jumps, and weight transfer are the point.

Minimum:

- one vehicle with readable steering and braking;
- chase camera with speed-aware damping;
- a closed route, delivery objective, or survival arena;
- checkpoints or recovery from leaving the route;
- speed, objective, and time UI;
- finish/fail/restart.

Tuning steering response, camera, and road scale is more valuable than adding vehicle customization.

## Physics puzzle

Minimum:

- one manipulation verb;
- stable collision materials and sleep thresholds;
- deterministic level reset;
- trajectory or affordance preview;
- three short levels that teach, combine, then test the rule;
- undo or quick restart.

Use a physics library when stacked bodies, joints, or impulses are central. Keep visual meshes separate from simple collision shapes.

## Arena survival

Minimum:

- camera-relative movement;
- one automatic or directed attack;
- two enemy behaviors;
- drops or score that reward risk;
- escalating spawn director;
- a short upgrade choice;
- boss or timed completion;
- pooling and spatial queries.

Preserve silhouettes under heavy effects. Cap enemies, projectiles, particles, labels, and audio voices independently so the busiest moment degrades gracefully.

## Hover or flight

Minimum:

- pitch/yaw/roll or simplified banking model;
- horizon and altitude cues;
- chase/cockpit camera that keeps orientation readable;
- gates, delivery points, or targets with distance feedback;
- recovery when the player leaves the route;
- speed/boost and completion state.

Use fog, landmarks, shadows, trails, and ground detail to communicate motion through 3D space. A featureless sky makes speed and direction unreadable.

## Content budgeting

For a first delivery, prefer:

- one player verb set;
- one environment kit;
- two or three obstacle/enemy behaviors;
- one short escalation curve;
- one boss, final room, delivery, or finish line;
- one restartable run.

The ceiling can be impressive later. The first milestone must already be a game someone can finish, fail, and immediately replay.
