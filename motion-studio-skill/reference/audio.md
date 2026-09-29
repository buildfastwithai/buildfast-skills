# Audio: music, SFX, voice-over, sync

`scripts/audio.py` renders the soundtrack at render time (render.py calls it) from three inputs:
1. **Genre + key + BPM** from the style's `sound` block (overridable in spec.json: `bpm`, `audio.music`).
   Genres: ambient, cinematic, synthwave, corporate, chiptune, lofi, glitch, horror, trailer, whimsical, documentary, none.
   A blended style ("vhs + horror") can switch to the secondary's darker genre.
2. **Arrangement** from each scene's `energy` (0..1): low energy drops drums/bass, high energy adds arps, hats, stabs; energy ≤ .1 = silence (use it before a title hit).
3. **Cues** from the composition: transitions (whoosh/swoosh/glitch/impact), `slam`/`shake` (impact), typewriter/code (type clicks), particles (impact/pop), cursor clicks, toasts (notify), logo reveals (riser + chime), charts (ticks), plus your own `C.cue(t, type, {gain, dur})`.
   SFX types: impact boom whoosh swoosh riser click pop tick ding chime glitch type notify shimmer stinger braam heartbeat zap beep static drop reverse hit. The style's `sound.sfx` palette (clean/soft/paper/chip/tape...) colours them.

Mix: sidechain ducking under kicks, reverb send, gentle EQ, soft limiter, then two-pass loudnorm to **-14 LUFS / -1.5 dBTP** (social platforms) at mux. A SFX-only stem (`out/NAME.sfx.wav`) is written for QC.

- **No music**: `"audio": {"music": "none", "sfx": true}`; nothing at all: `"sfx": false` too (or `render.py --no-audio`). Don't add sound for its own sake - documentary/calm pieces may want music only; UI promos want clicks.
- **Your own track**: `"audio": {"file": "assets/track.mp3"}` replaces the generated music (SFX still layered). For beat-sync run `audio.py --analyze assets/track.mp3 <project>` first - it writes beats/onsets/energy, sets bpm and duration; drive animation with `C.audio.level(t)`, `C.audio.band(t, 0..3)`, `C.audio.onsetNear(t)`, `C.audio.beatPhase(t)` (music visualizer / lyric video).
- **Voice-over**: no TTS engine ships with the skill. Record/generate a VO file elsewhere, set `"audio": {"voiceover": "assets/vo.wav"}` - it is mixed on top with automatic ducking. Always also show the words on screen (autoplay is muted).
- **Sync rules**: put hits on the beat grid (`C.beat`), space percussive cues ≥ ~0.3 s apart (closer hits mask each other - QC reports it), and pre-roll whooshes (transition cues already do).
