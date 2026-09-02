<div align="center">

# Talking Avatar

**Build a lightweight realtime voice app whose character mouth follows the actual remote audio stream.**

[Proof](#proof) · [What you get](#what-you-get) · [Use it](#use-it) · [Browse all skills](../README.md)

<br>

<code>npx skills add buildfastwithai/buildfast-skills --skill talking-avatar-skill</code>

</div>

![Aiko in the Tsukiakari Books realtime voice app](assets/readme/aiko-desktop.webp)

<p align="center"><sub>Aiko at Tsukiakari Books, a real voice-avatar app built with this skill.</sub></p>

---

## Proof

The desktop image above and the mobile capture below come from [Tsukiakari Books](https://sotto-realtime-voice.satvikps.chatgpt.site/), a working example with a bring-your-own-key Realtime flow.

| Desktop composition | Mobile composition |
|:--:|:--:|
| <img src="assets/readme/aiko-desktop.webp" alt="Aiko voice companion desktop interface" width="100%"> | <img src="assets/readme/aiko-mobile.webp" alt="Aiko voice companion mobile interface" width="100%"> |

A live lip-sync recording is still stronger proof than a still image and remains a welcome addition; this README does not pretend otherwise.

## Why this exists

Many avatar demos are a chat box beside an animated portrait. This skill treats voice, character, safety, and state as one product: the session is negotiated behind a same-origin server route, the key remains ephemeral, and mouth poses are driven by measured remote audio amplitude instead of a decorative timer.

## What you get

- A Next.js/vinext talking-avatar interface, or integration into a compatible existing realtime app.
- One canonical portrait and an identity-consistent mouth-pose sprite set.
- Audio-driven lip sync plus listening, speaking, muted, error, retry, and disconnected states.
- A bring-your-own-key OpenAI Realtime flow that keeps credentials out of committed client code.
- Focused regression tests, scaffold helpers, and local avatar-asset validation.
- A handoff covering commands run and any credential, image, or deployment step still owned by the user.

## Use it

```bash
npx skills add buildfastwithai/buildfast-skills --skill talking-avatar-skill
```

Then supply a portrait or describe the character and product:

> “Use talking-avatar-skill to build a voice companion from this portrait.”

> “Create a warm museum-guide character from a description and add it to my existing Next.js Realtime app.”

> “Fix this avatar so its mouth responds to the assistant's actual audio instead of looping randomly.”

## Recipe

1. **Choose the mode.** Scaffold a compatible initialized app or integrate with an existing safe realtime backend.
2. **Anchor the identity.** Use the supplied portrait or generate one canonical character before deriving mouth poses.
3. **Wire the realtime path.** Keep session negotiation on the server and credentials ephemeral.
4. **Drive the face from audio.** Measure the remote stream, smooth amplitude, and map it to the sprite poses.
5. **Test the states.** Validate assets, unresolved template tokens, reconnect/error behavior, and the production build when available.

## Local scaffold proof

| Check | Result |
|:--|:--|
| Initialized-project guard | Correctly rejects an empty folder without `package.json` |
| Dry run and scaffold | Exit code **0** against an initialized local project |
| Template replacement | **0** unresolved template tokens |
| Pre-build regression test | **2 passed**, with **2 worker-build checks skipped** until a vinext build exists |

## Bring

- An initialized Next.js or vinext project for the bundled scaffold. Existing Vite apps need a safe backend route for negotiation.
- Node.js, `framer-motion`, and `@phosphor-icons/react` for the generated app.
- Python 3 for scaffold and asset-validation utilities.
- An OpenAI API key supplied at runtime.
- Image generation or a complete user-supplied character asset set.

## What it will not do

- Commit an API key or expose it in a client bundle.
- Animate the mouth with a random loop and call it lip sync.
- Regenerate each mouth pose as a different identity.
- Replace a working realtime architecture without a concrete need.

## Inside the skill

```text
talking-avatar-skill/
├── SKILL.md
├── agents/openai.yaml
├── assets/starter/
├── references/
│   ├── app-contract.md
│   ├── image-pipeline.md
│   └── realtime-lipsync.md
└── scripts/
    ├── scaffold_app.py
    └── validate_avatar_assets.py
```

---

[← Browse BuildFast Skills](../README.md) · [MIT licensed](../LICENSE) · [View the standalone skill](https://github.com/buildfastwithai/talking-avatar)
