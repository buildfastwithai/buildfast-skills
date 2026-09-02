<div align="center">

# Premium UI Revamp

**Turn a generic or visibly AI-generated interface into a deliberate product while preserving its behavior and stack.**

[Why it exists](#why-this-exists) · [What changes](#what-changes) · [Use it](#use-it) · [Browse all skills](../README.md)

<br>

<code>npx skills add buildfastwithai/buildfast-skills --skill premium-ui-revamp-skill</code>

</div>

![Editorial visual of a generic interface becoming a coherent premium UI](assets/readme/revamp-direction.webp)

<p align="center"><sub>Editorial transformation visual—not a screenshot of a bundled app. The skill audits and edits the real interface you provide.</sub></p>

---

## Why this exists

Generic interfaces rarely fail because they need more gradients. They fail because hierarchy, density, typography, spacing, components, and interaction states do not agree. This skill diagnoses those systems in the rendered product, fixes the highest-leverage problems first, and verifies that the redesign did not break the application underneath it.

## What changes

| Pass | The work |
|:--|:--|
| **1 · Structure** | Hierarchy, content order, information architecture, density, and responsive composition |
| **2 · System** | Typography, spacing, color, radii, elevation, shared components, and interaction states |
| **3 · Finish** | Optical alignment, icons, borders, microcopy, transitions, and final visual detail |

You receive implemented changes in the existing stack, a compact design brief, the rationale behind the decisions, validation results, and any limitation that still needs product or brand input.

## Use it

```bash
npx skills add buildfastwithai/buildfast-skills --skill premium-ui-revamp-skill
```

Then name the surface, desired character, and workflows that must remain intact:

> “Use premium-ui-revamp-skill to make this dashboard feel precise and trustworthy. Preserve every workflow.”

> “Audit this marketing page at desktop and mobile sizes, then implement the highest-impact fixes.”

> “Remove the generic AI design tells from this React app without turning it into another bland minimal site.”

## Recipe

1. **Inspect the product.** Read the frontend, run it, and review the real route at representative desktop and mobile widths.
2. **Write a compact brief.** Name the product character, strongest problems, preserved behaviors, and intended design system.
3. **Fix in leverage order.** Structure first, system second, polish last.
4. **Work inside the stack.** Reuse existing components, dependencies, data flow, and routes wherever they remain sound.
5. **Verify the rendered result.** Run the production build, inspect responsive states, and test keyboard, focus, and reduced motion.

## Done means

| Surface | Required proof |
|:--|:--|
| **Behavior** | Existing routes, controls, content, and data flow still work |
| **Access** | Keyboard, focus-visible, reduced-motion, and responsive states remain usable |
| **System** | Shared tokens and repeated components stay coherent |
| **Build** | The production build succeeds |
| **Finish** | The rendered result passes the included quality rubric |

## Bring

- An existing frontend and the route or screen to improve.
- Product, audience, brand, or visual constraints.
- The project's normal build tools and permission to edit the in-scope interface.

The workflow supports HTML/CSS/JavaScript, React, Vue, Svelte, Next.js, and similar frontend projects.

## What it will not do

- Replace the framework just to make redesign easier.
- Rewrite unrelated components or backend behavior.
- Hide structural problems under surface decoration.
- Call a redesign complete without inspecting the rendered product.

## Inside the skill

```text
premium-ui-revamp-skill/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── premium-patterns.md
    └── quality-rubric.md
```

---

[← Browse BuildFast Skills](../README.md) · [MIT licensed](../LICENSE) · [View the repository](https://github.com/buildfastwithai/buildfast-skills)
