---
name: ernesta-email-design-system
description: "Ernesta's email design system built from the Ernesta Email Component Library in Figma: tokens, all atoms/molecules/modules, the three newsletter templates and the live lifecycle emails (Welcome, Persian Edit, Custom-sizing 101, Sample, Roomvo). Use whenever building, editing or reviewing an Ernesta newsletter or lifecycle email, choosing email colors, fonts or modules, or when the user mentions Ernesta email components, templates, hero, product grid, reviews module, support bar or footer."
---

# Ernesta email design system

Source of truth: the Design System artifact https://claude.ai/artifact/GajxHxzdVqsq9FEaBchaqV, built from the Figma file "Ernesta Email Component Library" (fileKey dAMxIWTCyv3Hk8nALva1GM, https://www.figma.com/design/dAMxIWTCyv3Hk8nALva1GM/Ernesta-Email-Component-Library).

## Steps
1. Read `project/README.md` from the artifact with the Artifact tool (`action: "read"`, `path`). It holds the usage rules. Then read `project/tokens.json` for exact colors, type, spacing and radii.
2. Read `project/templates.md` to pick the closest starting point: Back in stock, Product feature (layouts A/B) or Editorial (layouts A/B), or one of the live emails (Welcome, Persian Edit, Custom-sizing 101, Sample, Roomvo).
3. For each module, read `project/components/<Name>/README.md` (variants, toggles, what it is built from, where it is used) and `project/components/<Name>/preview.html`. Nine components have production email markup in their preview (PreHeader, Hero, ProductGrid, ReviewsModule, FeatureText, ImageText, Ctas, SupportBar, Footer); copy that and swap the content.
4. All other components (atoms like CtaButtons, ProductCard, Numbers; molecules like ImageCollage, ImageStack, ThreeColumnFeatureCard, FiftyFiftyImageText, Headers; modules like ImageTextStepsModule, ImageImageModule, CollectionStack, the ImageStack* themed families) have a Figma render at `project/assets/<Atoms|Molecules|Modules>/<name>.png`. Read it (`path`) to see every variant, then build the HTML from the render and the tokens.
5. Template and email renders are under `project/assets/Templates/` and `project/assets/Emails/`.
6. `project/figma-file.md` maps every Figma page and node id. If something is missing or a render looks out of date, read the node in the Figma file with the Figma tools.
7. Use the `newsletter-recommended-styles` skill for the "Recommended for you" block and review quotes.

## Rules to keep even if the artifact cannot be read
- Colors: surface #f8f6f3, ink #262933, white #ffffff, linen #f6f4f1, banner-mist #c8cdd0. Dark modules are ink with cream (#f8f6f3) text.
- Fonts: serif headlines (Portonovo, fallback Georgia), sans text (Reader Pro, fallback Helvetica/Arial). H1 48, H2 32, H3 24, H4 18, 600 weight, -1% tracking; body 13-15; buttons 11 uppercase, +5% tracking. Mobile sizes are smaller (H1 32, H2 24, H3 20, H4 16).
- Buttons: solid ink or outline; one primary CTA per module; over dark photography use a solid white button.
- 600px desktop, 390px mobile, table-based HTML with inline styles, 24px side gutter.
- Every send has a pre-header, a support bar (or the value-prop marquee at the top) and the footer with an unsubscribe link.
- Keep `[STYLE]` merge fields and placeholders such as "Lorem ipsum" out of anything that is actually sent, except where the ESP replaces the merge field.
