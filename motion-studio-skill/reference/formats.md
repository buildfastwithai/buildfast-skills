# Formats and aspect-aware composition

| format | size | safe area (x, y, w, h of frame) | compose as |
|---|---|---|---|
| 16:9 | 1920×1080 | .06 .08 .88 .84 | side-by-side (text left, visual right), lower thirds, letterbox allowed |
| 9:16 | 1080×1920 | .07 .13 .86 .67 | stacked: headline upper third, subject centre, captions above the platform UI (bottom ~20 %, right ~12 % on TikTok) |
| 1:1 | 1080×1080 | .07 .07 .86 .86 | centred, symmetric, text stacked over visual |
| 4:5 | 1080×1350 | .07 .08 .86 .80 | like 1:1 with a headline band |
| 21:9 | 2560×1080 | .10 .08 .80 .84 | panoramic; keep text in the centre 60 % |
| custom | "1600x900" in the brief or spec width/height | engine default safe area | - |

Optimise, don't resize: branch layouts on `C.vertical` / `C.square`.
- Vertical: huge type (display 12-15 u, body ≥ 4.5 u), one idea per screen, subject centred, faster comprehension (hook in frame 1), captions burned in (autoplay is muted), the UI kit auto-scales ×1.6.
- Square/4:5: stack, centre, avoid wide side-by-side layouts.
- Landscape: use the width - split screens, parallax pans, lower thirds.
Minimum readable text is 2.2 u (≈24 px at 1080 short side); QC flags anything smaller. Platforms: X autoplays muted (≤ 2:20), Reels/TikTok cover the bottom and right edges, YouTube Shorts ≤ 60 s.
Re-layout an existing project for another format: `render.py <p> --format 9:16` (check the stills; fix scenes that need a vertical composition).
