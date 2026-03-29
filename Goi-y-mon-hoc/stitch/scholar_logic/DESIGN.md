# Design System Documentation: The Intellectual Architecture

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Academic Atelier."** 

Unlike traditional educational platforms that feel like rigid, digital filing cabinets, this system treats the dashboard as a high-end, curated workspace. It rejects the "template" look characterized by heavy borders and flat boxes. Instead, it embraces **Atmospheric Depth**—using light, layering, and sophisticated tonal shifts to guide the student’s eye. The goal is to create a "flow state" environment where data density feels like a natural landscape rather than a cluttered spreadsheet.

Through intentional asymmetry—such as offset headers and varied card widths—we break the monotony of the grid, making the learning experience feel bespoke, premium, and intellectually stimulating.

---

## 2. Colors & Surface Philosophy

The palette is rooted in a "Professional Blue" core, but its execution relies on the interplay of white space and subtle grey transitions to create a sense of calm authority.

### The "No-Line" Rule
**Borders are prohibited for sectioning.** To define boundaries between the sidebar, main content, and utility panels, use background color shifts. 
- *Implementation:* Place a `surface_container_low` section directly against a `surface` background. The change in hex value provides all the separation the eye needs without the visual noise of a 1px line.

### Surface Hierarchy & Nesting
Think of the UI as stacked sheets of fine vellum. Use the surface-container tiers to create "nested" importance:
- **Base Layer:** `surface` (#f8f9fa) – The infinite canvas.
- **Structural Zones:** `surface_container_low` (#f3f4f5) – Sidebars and navigation.
- **Content Cards:** `surface_container_lowest` (#ffffff) – This creates a "lifted" effect where the most important data sits on the brightest white.
- **Interaction Wells:** `surface_container_high` (#e7e8e9) – Used for inset elements like search bars or code blocks.

### The "Glass & Gradient" Rule
To elevate the "Modern" requirement, floating elements (like the Chatbot or Modals) must use **Glassmorphism**. Use a semi-transparent `surface_container_lowest` with a `backdrop-blur` of 12px-16px. 
*CTA Soul:* For primary actions, do not use a flat hex. Apply a subtle linear gradient from `primary` (#005bbf) to `primary_container` (#1a73e8) at a 135-degree angle to provide a "lit-from-within" professional polish.

---

## 3. Typography: The Editorial Voice

We utilize **Inter** not as a utility font, but as an editorial tool. The hierarchy is designed to minimize cognitive load while maintaining an authoritative "Higher Ed" feel.

- **Display (Large/Medium):** Reserved for high-level motivational stats (e.g., "94% Syllabus Complete"). These use tight letter-spacing (-0.02em) to feel impactful.
- **Headline & Title:** Use `headline-sm` for module titles. These should be paired with generous top-spacing (`spacing-12`) to allow the content to breathe.
- **Body & Label:** Use `body-md` for instructional text. Labels (`label-md`) should always be in `on_surface_variant` (#414754) to create a clear visual distinction from primary user data.

*Director's Tip:* Contrast is king. Pair a `display-sm` stat with a `label-sm` descriptor in all-caps to create a sophisticated, data-rich header that feels like a premium financial report.

---

## 4. Elevation & Depth

We move away from the "drop shadow" era into **Tonal Layering.**

- **The Layering Principle:** A `surface_container_lowest` card sitting on a `surface_container_low` background creates a natural elevation of 1dp without a single pixel of shadow.
- **Ambient Shadows:** For floating elements (Chatbots, Pop-overs), use a shadow with a blur radius of 32px and an opacity of 6%. The shadow color must be a tint of our `primary` (e.g., `#001a41` at 5% opacity) to ensure the shadow feels like it belongs to the environment.
- **The "Ghost Border" Fallback:** If accessibility requires a stroke (e.g., in high-contrast modes), use `outline_variant` (#c1c6d6) at 20% opacity. **Never use 100% opaque borders.**

---

## 5. Components

### Cards & Data Lists
*Rule: Forbid divider lines.* 
Use `spacing-4` or `spacing-5` as vertical gutters. In lists, alternate background colors between `surface_container_lowest` and `surface_container_low` to create row distinction.

### Buttons
- **Primary:** Gradient-filled (`primary` to `primary_container`), `roundedness-md` (0.75rem).
- **Secondary:** Transparent background with a `Ghost Border`.
- **Tertiary:** Text-only in `primary` color, used for low-priority "Cancel" or "Back" actions.

### The Friendly Chatbot Interface
The chatbot should not look like a support widget. Style it as a "Study Companion." 
- **User Bubbles:** `primary` background with `on_primary` text.
- **Bot Bubbles:** `surface_container_high` with a subtle glassmorphism blur. 
- **Positioning:** Offset from the bottom right using `spacing-8` to avoid crowding the main content.

### Form Validation
- **Default State:** `outline_variant` at 40% opacity.
- **Focus State:** `primary` 2px ghost-border with a subtle `primary_fixed` outer glow.
- **Error State:** `error` (#ba1a1a) text paired with an `error_container` (#ffdad6) background fill for the input field.

### Progress Bars
Avoid the "flat" look. Use `primary_fixed` as the track color and a `primary` gradient for the fill. The `roundedness-full` scale should be applied to both the track and the indicator.

---

## 6. Do’s and Don’ts

### Do
- **Do** use `spacing-16` or `spacing-20` for major section margins to create an "Editorial" feel.
- **Do** layer your surfaces. An inner card should always be "brighter" (`surface_container_lowest`) than its parent container.
- **Do** use `tertiary` (#9e4300) sparingly for "Warning" or "High Priority" callouts to break the blue/grey monotony.

### Don't
- **Don't** use 1px solid borders to separate the sidebar from the main content. Use a background shift.
- **Don't** use pure black (#000000) for text. Use `on_surface` (#191c1d) to maintain a soft, premium readability.
- **Don't** overcrowd the dashboard. If data density is high, use `spacing-2.5` (0.5rem) as your "tight" unit, but ensure it is balanced by large `headline` typography.
- **Don't** use "default" system shadows. Always use the Ambient Shadow formula (high blur, low opacity).