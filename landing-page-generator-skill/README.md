<div align="center">

# Landing Page Generator

**Build one production-ready HTML landing page, then audit the conversion path, CTA system, and likely performance risks.**

[Why it exists](#why-this-exists) · [What ships](#what-ships) · [Use it](#use-it) · [Browse all skills](../README.md)

<br>

<code>npx skills add buildfastwithai/buildfast-skills --skill landing-page-generator-skill</code>

</div>

![Editorial visual of a responsive landing-page system](assets/readme/landing-page-direction.webp)

<p align="center"><sub>Editorial direction visual—not a screenshot of a bundled demo. The skill produces a real, self-contained HTML page in your project.</sub></p>

---

## Why this exists

A landing page is not a pile of fashionable sections. It is one argument for one audience, moving toward one conversion goal. This skill makes the message and CTA system explicit, builds the page, and then runs focused audits instead of declaring success from appearance alone.

## What ships

- One self-contained, production-ready HTML page.
- A nine-section starter with four visual themes, SEO metadata, FAQ schema, and core performance safeguards.
- Copy guidance for PAS, AIDA, and Before–After–Bridge.
- Three executable audits for conversion structure, CTA placement and consistency, and likely speed risks.
- A handoff with the chosen framework/theme, results, assumptions, and exact assets or integrations still needed.

The skill removes sections that do not support the chosen goal. It never invents testimonials, customer logos, metrics, or guarantees.

## Use it

```bash
npx skills add buildfastwithai/buildfast-skills --skill landing-page-generator-skill
```

Then give it the audience, offer, traffic source, proof, and one conversion goal:

> “Use landing-page-generator-skill to make a webinar signup page for engineering managers. Traffic comes from LinkedIn ads.”

> “Audit this launch page and fix every issue below a B grade.”

> “Create a dark developer-tool page using PAS copy, with one free-trial CTA.”

## Recipe

1. **Set one conversion goal.** Define the audience, offer, traffic source, proof, objections, and action.
2. **Choose the argument.** Select the copy framework and only the sections that advance it.
3. **Choose the visual system.** Apply one of the documented styles or the user's existing brand constraints.
4. **Build the page.** Fill the self-contained starter and wire only real destinations.
5. **Audit and repair.** Run all three scripts, fix flagged issues and grades below B, then manually review message clarity.

## Audit loop

```bash
python scripts/conversion_checklist.py page.html
python scripts/cta_analyzer.py page.html
python scripts/page_speed_estimator.py page.html
```

### Starter baseline

| Check | Local result | What it demonstrates |
|:--|:--|:--|
| Conversion structure | **93 · A** | Expected hierarchy, proof, CTA placement, metadata, and mobile safeguards exist |
| Speed estimator | **100 · A** | The untouched starter avoids the common LCP and CLS risks the script can detect |
| CTA analyzer | **65 · C before copy is filled** | Placeholder labels are deliberately flagged; a finished page must replace them and reach B or better |

## Bring

- One conversion goal, one audience, the offer, traffic source, real proof, and brand constraints.
- Python 3 for the bundled audits.
- Real form, checkout, booking, analytics, and destination URLs before launch.

## What it will not do

- Split one page across competing primary goals.
- Fabricate proof, social validation, scarcity, or guarantees.
- Mark placeholder links or disconnected forms as complete.
- Trade basic speed and access for decorative effects.

## Inside the skill

```text
landing-page-generator-skill/
├── SKILL.md
├── agents/openai.yaml
├── assets/template.html
├── references/
│   ├── copy-frameworks.md
│   ├── design-styles.md
│   ├── optimization.md
│   └── section-library.md
└── scripts/
    ├── conversion_checklist.py
    ├── cta_analyzer.py
    └── page_speed_estimator.py
```

---

[← Browse BuildFast Skills](../README.md) · [MIT licensed](../LICENSE) · [View the repository](https://github.com/buildfastwithai/buildfast-skills)
