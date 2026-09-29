# Automated QC (scripts/qc.py, run by every final render)

| # | check | how | severity |
|---|---|---|---|
| 1 | file exists / non-empty | stat | error |
| 2 | duration | ffprobe vs spec (± 1.5 frames) | error |
| 3 | resolution / aspect | ffprobe vs spec | error (aspect) / info (preview scale) |
| 4 | frame rate, pixel format | ffprobe | warn |
| 5 | audio stream present when expected; loudness -18..-10 LUFS; true peak | ffprobe, ebur128 | warn |
| 6 | black frames not explained by a fade/hold | blackdetect, minus declared fades/`hold:'black'`/head+tail | warn |
| 7 | frozen frames ≥ 3 s not declared as a hold | freezedetect | warn (info if declared) |
| 8 | visual glitches: abrupt full-frame changes away from scene/transition/cue times | scdet | warn (info in glitch/VHS styles) |
| 9 | text leaving the frame / outside the safe area (ignored while a transition carries it out) | engine audit every 0.5 s + near scene ends | error / warn |
| 10 | text too small (below 2.2 u) or overflowing its box | engine audit | warn / error |
| 11 | missing fonts, missing assets, page errors | engine meta, console | error |
| 12 | transitions: variety (not all fade/dissolve) | meta | warn |
| 13 | scene timing: scenes ≥ 0.4 s, reading speed ≤ 4.5 words/s | meta text inventory | warn |
| 14 | audio sync: every percussive cue has a distinct attack in the SFX stem within 30 ms; muxed audio vs rendered mix offset ≤ 1 frame (cross-correlation) | stem onset analysis, xcorr | warn / error |
| 15 | representative frames from the FINAL file (scene starts, middles, transitions) | `out/NAME.qc-sheet.png` | **you must Read and judge it** |
| 16 | fix + re-render | the loop in SKILL.md | - |

Results: `out/NAME.qc.json` + a one-screen summary. Errors must be fixed. Warnings: fix, or state why they're intended. Then look at the sheet for what automation can't judge: hierarchy, composition, contrast, rhythm, whether each style actually reads as that style, whether transitions look intentional.
Previews (`--preview`) skip QC; stills (`--stills`) are for design iteration, not a substitute for the final QC.
