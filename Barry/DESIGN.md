```markdown
# Design System Strategy: The Digital Atelier

## 1. Overview & Creative North Star
**Creative North Star: The Curated Hearth**

This design system rejects the "command center" archetype of traditional data platforms. Instead of cold, high-density grids and clinical blue-light aesthetics, we are building a "Curated Hearth." The goal is to transform YouTube analytics from a source of stress into a source of inspiration. 

We achieve this through **Intentional Softness**. By utilizing high-radius corners (`xl: 3rem`), generous white space, and a tonal-first depth model, the interface feels less like a software tool and more like a tactile, physical workspace—reminiscent of high-end stationery and sunlight-drenched studios. We break the "template" look by favoring organic, asymmetric layouts and overlapping card structures that mimic a physical desktop.

## 2. Color & Surface Philosophy

The palette is rooted in warmth, moving away from pure whites and greys toward bone, cream, and clay.

### The "No-Line" Rule
**Lines are a failure of hierarchy.** In this system, 1px solid borders are strictly prohibited for sectioning. Differentiation must be achieved through:
*   **Background Shifts:** Place a `surface_container_lowest` card on a `surface_container` background.
*   **Tonal Transitions:** Use the subtle shift from `surface` to `surface_dim` to denote content boundaries.

### Surface Hierarchy & Nesting
Treat the UI as a series of nested, organic layers. 
*   **Base Layer:** `background` (#fffcf7).
*   **Sectioning:** Use `surface_container_low` for large, secondary regions.
*   **Priority Content:** Use `surface_container_lowest` (#ffffff) for primary cards to give them a "lifted" feel against the warmer background.
*   **Interactive Overlays:** Use `surface_bright` to draw the eye to active elements.

### The Glass & Signature Texture Rule
To elevate the dashboard from "flat" to "premium," incorporate **Glassmorphism** for floating navigation bars or filter pills. Use `surface` with 80% opacity and a `20px` backdrop blur. 
*   **Signature Gradient:** For primary CTAs and high-level growth metrics, apply a subtle linear gradient from `primary` (#a24a35) to `primary_container` (#ffac99) at a 135-degree angle. This adds "soul" and dimension to the data.

## 3. Typography: Editorial Clarity

We utilize **Plus Jakarta Sans** across all scales. Its modern, geometric curves mirror our `ROUND_SIXTEEN` corner philosophy, maintaining a friendly yet authoritative voice.

*   **Display & Headlines:** Use `display-md` for "Hero" metrics (e.g., total subscriber count). The generous letter spacing and large scale create an editorial, magazine-like feel.
*   **Titles:** `title-lg` should be used for card headers. Ensure a high-contrast color (`on_surface`) to maintain readability against the soft `surface_container` colors.
*   **Body & Labels:** `body-md` is the workhorse. For secondary metadata (e.g., "vs last 28 days"), use `label-md` with the `on_surface_variant` token to de-prioritize the text visually without losing legibility.

## 4. Elevation & Depth: Tonal Layering

Traditional shadows are too aggressive for a "cozy" workspace. We use **Ambient Depth**.

*   **The Layering Principle:** Hierarchy is achieved by stacking. A `surface_container_highest` element represents the most "recessed" area (like a tray), while `surface_container_lowest` represents the "highest" sheet of paper.
*   **Ambient Shadows:** For floating elements (Modals, Popovers), use an extra-diffused shadow: `box-shadow: 0 12px 40px rgba(162, 74, 53, 0.06);`. Note the tint: we use a tiny fraction of the `primary` or `on_surface` color rather than black to keep the shadow feeling natural and "warm."
*   **The Ghost Border:** If a boundary is strictly required for accessibility (e.g., in a high-density data table), use a "Ghost Border": `outline_variant` at 15% opacity.

## 5. Component Guidelines

### Buttons & Interaction
*   **Primary:** Highly rounded (`full`), using the signature Terracotta (`primary`) gradient. Text is `on_primary`.
*   **Secondary:** `secondary_container` background with `on_secondary_container` text. No border.
*   **Tertiary:** Transparent background with `primary` text. Use for low-emphasis actions like "View All."

### Analytics Cards
*   **Structure:** No dividers. Use `spacing.6` (2rem) as internal padding.
*   **Corner Radius:** Always use `lg` (2rem) or `xl` (3rem) for parent cards.
*   **Data Visualization:** Use `primary` (Coral/Terracotta) for growth lines, `secondary` (Sage) for steady states, and `tertiary` (Warm Brown) for benchmarks.

### Input Fields & Search
*   **Style:** Use `surface_container_high` as the fill color. 
*   **States:** On focus, transition the background to `surface_container_lowest` and apply a 2px `outline` in `primary` at 30% opacity. This creates a "glow" rather than a hard ring.

### The "Content Cluster" (New Component)
Instead of a standard list, use "Clusters." Group related YouTube comments or video stats into a single `surface_container_low` pod with `md` (1.5rem) rounded corners, separating items with vertical whitespace (`spacing.4`) instead of lines.

## 6. Do’s and Don’ts

### Do
*   **Do** use asymmetrical margins. Offsetting a header slightly to the left creates a "scrapbook" editorial feel.
*   **Do** use the `secondary` (Sage) and `tertiary` (Brown) tokens for data visualization to avoid the "Christmas effect" (Red/Green) and maintain the soft palette.
*   **Do** lean into `spacing.16` (5.5rem) for section gaps. Space is a luxury; use it.

### Don’t
*   **Don’t** use 100% black (#000000). Always use `on_surface` (#373831) for text to keep the contrast soft.
*   **Don’t** use sharp corners. Even the smallest tooltip should have at least `sm` (0.5rem) rounding.
*   **Don’t** use traditional "Alert Red" for errors. Use the `error` (#b3374e) and `error_container` tokens, which are muted and integrated into the warm palette.

---
**Director's Note:** Every pixel should feel intentional, not industrial. If a layout feels too "busy," increase the padding and move a container one tier down in the `surface_container` scale. We are not just showing data; we are hosting a conversation.```