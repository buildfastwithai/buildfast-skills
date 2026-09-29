# Transitions

| type | feel | good for |
|---|---|---|
| cut / match | invisible, rhythmic | on-beat edits, match cuts (same shape/position on both sides) |
| fade (through black) | ending, time passing | endings, chapters, horror |
| dissolve / blur | soft continuity | calm, luxury, documentary |
| whip (dir) | speed, energy | energetic, anime, social |
| push (dir) | spatial continuity | UI, SaaS, lists, timelines |
| zoom | into detail / next level | snappy, reveals |
| radial / iris | focus, reveal from a point | reveals, playful, retro |
| wipe (dir, accent edge) / slice | graphic, editorial | infographics, technical, kinetic type |
| mask (diagonal) | premium graphic | modern commercial |
| flash | impact frame | trailers, anime, drops |
| glitch / distortion | corruption, tension | glitch, VHS, horror, cyberpunk |
| shape (circle/square/diamond, accent colour) | brand-y bumper | SaaS, 90s, social |
| morph (blob) | liquid transformation | abstract, organic, holographic |
| particles | dissolution | sci-fi, fantasy, particle styles |

Selection: `type:'auto'` intersects the style's and motion's preferred lists, skips their avoid lists, and uses the `intent` of the cut (impact, reveal, escalate, calm, continue, end, transform) - so choice follows narrative, not randomness. Rules: vary types (QC warns when every cut is the same fade/dissolve); faster transitions in faster motion languages; save the most dramatic transition for the payoff; transitions add their own whoosh/impact cues. Custom transitions: `engine/extensions/*.js` (extend.py new-transition).
