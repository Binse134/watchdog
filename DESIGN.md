---
name: Watchdog
description: A clinical, terminal-instrument dashboard for monitoring self-hosted n8n workflows
colors:
  terminal-amber: "oklch(0.62 0.18 48)"
  terminal-amber-hover: "oklch(0.68 0.18 48)"
  instrument-blue: "oklch(0.58 0.06 230)"
  near-black: "oklch(0.09 0 0)"
  panel: "oklch(0.155 0.004 48)"
  panel-raised: "oklch(0.21 0.004 48)"
  hairline: "oklch(0.34 0.004 48)"
  ink: "oklch(0.93 0.004 48)"
  ink-muted: "oklch(0.62 0.006 48)"
  status-failing: "oklch(0.58 0.21 25)"
  status-silent: "oklch(0.58 0.15 85)"
  status-orphaned: "oklch(0.60 0.16 300)"
  status-healthy: "oklch(0.68 0.13 152)"
typography:
  headline:
    fontFamily: "var(--font-geist-sans)"
    fontSize: "clamp(1.5rem, 2.5vw, 1.875rem)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "var(--font-geist-sans)"
    fontSize: "1.0625rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "var(--font-geist-sans)"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "var(--font-geist-mono)"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.02em"
rounded:
  sm: "6px"
  md: "10px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.terminal-amber}"
    textColor: "#0a0a0a"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "{colors.terminal-amber-hover}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  status-pill-failing:
    backgroundColor: "{colors.status-failing}"
    textColor: "#0a0a0a"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "3px 10px"
---

# Design System: Watchdog

## 1. Overview

**Creative North Star: "The Instrument Panel"**

Watchdog is read like an oscilloscope, not browsed like a SaaS dashboard. The
reference point is old monitoring instrumentation — amber phosphor displays,
analog dials, control-room consoles — where every glowing element exists to
report a fact, not to decorate. The product's own principle states it
plainly: status is the headline, and a healthy system should look quiet.
This system makes that literal: a near-black surface that disappears at rest,
one amber signal color reserved for what actually needs attention, and
typography split cleanly between human-readable prose (Geist Sans) and
exact-readout data (Geist Mono) — counts, timestamps, IDs always render in
mono, the way a terminal would print them.

It explicitly rejects the generic SaaS-dashboard look this project's
PRODUCT.md calls out by name: no purple/blue gradients, no identical
icon-card grids, no hero-metric tiles with a gradient accent. There is one
brand color, used sparingly, and a second cool accent for quieter UI; that's
the entire decorative vocabulary. Everything else is structure, contrast,
and a tightly disciplined status-color system.

**Key Characteristics:**
- Dark by default — built for the moment someone opens this after an alert email, not a bright first-run demo.
- One amber signal color (terminal-amber), spent almost entirely on primary actions and the brand mark — never on status.
- Status colors are a closed, separate palette from brand colors, so "this needs attention" is never confused with "this is just a button."
- Mono type for anything that's data (counts, timestamps, health labels); sans for anything that's prose.
- Flat by default — no drop shadows. Depth comes from three stepped surface lightness levels, not elevation shadows.

## 2. Colors

A near-black instrument-panel surface carries almost the entire UI; color is spent deliberately, not ambiently.

### Primary
- **Terminal Amber** (oklch(0.62 0.18 48)): The single brand color. Used only for primary actions (Sync, Generate summary, Connect), the wordmark, and focus rings. Never used for status — keeping it out of the status vocabulary is what makes it read as "the brand" instead of "a warning."

### Secondary
- **Instrument Blue** (oklch(0.58 0.06 230)): A desaturated, clinical blue-grey for secondary interactive elements — links, secondary buttons, selected nav state. Cool against amber's warmth; carries none of amber's urgency.

### Neutral
- **Near-Black** (oklch(0.09 0 0)): Page background. Pure neutral, zero chroma — the instrument panel's resting state.
- **Panel** (oklch(0.155 0.004 48)): Card/section surfaces, one step up from bg. Barely tinted toward the brand hue (chroma 0.004) — just enough to feel like *this* product's dark, not a generic dark mode.
- **Raised Panel** (oklch(0.21 0.004 48)): Modals, dropdowns, popovers — the third and final surface step.
- **Hairline** (oklch(0.34 0.004 48)): Borders and dividers. A line, not a shadow — this system separates surfaces with edges, not elevation. Bumped from the original 0.26 in Phase 12 after measuring it landed at only ~1.26:1 contrast against `panel` (and the three surface-lightness steps measure only ~1.1:1 apart from each other) — both well under the 3:1 floor for perceivable UI boundaries. Not pushed all the way to 3:1, which would fight the flat/quiet aesthetic; this is a moderate, measured improvement, not full WCAG 1.4.11 compliance.
- **Primary Text** (oklch(0.93 0.004 48)): Body and heading text. 7:1+ against bg.
- **Secondary Text** (oklch(0.62 0.006 48)): Timestamps, counts, helper text, placeholders. ≥3.5:1 against bg — used for de-emphasis, never for anything a user must read to use the product.

### Status (closed palette, separate from brand colors)
- **Failing Red** (oklch(0.58 0.21 25)): The most saturated color in the system, on purpose — failing is the one state that should pull the eye immediately.
- **Silent Gold** (oklch(0.58 0.15 85)): Distinct hue from terminal-amber (85° vs 48°) so "silent" is never mistaken for a branded element.
- **Orphaned Violet** (oklch(0.60 0.16 300)): A structural problem (the workflow vanished from n8n), not a runtime one — deliberately a colder, stranger hue than the other two to read as "different kind of problem."
- **Healthy Green** (oklch(0.68 0.13 152)): Used only as a small dot, never a filled pill (see The Calm Default Rule below).
- **Unused**: no color at all — secondary-text gray, ghosted. Nothing to report, nothing to look at.

### Named Rules
**The One Signal Rule.** Terminal Amber appears only on primary actions and the wordmark. If you reach for it anywhere in the status system, stop — that's instrument-blue or a status color's job, not the brand's.

**The Calm Default Rule.** Only `failing` and `silent` render as filled, saturated pills — they're the two states someone needs to act on. `healthy` renders as quiet text with a small solid dot; `unused` and `orphaned`-at-rest render as plain secondary-text with an outlined dot. A fully healthy dashboard should look almost monochrome; color density is itself a signal of how much is wrong.

## 3. Typography

**Body/Headline Font:** Geist Sans (with system-ui fallback) — already loaded in `app/layout.tsx`, no new dependency.
**Label/Mono Font:** Geist Mono (with ui-monospace fallback) — also already loaded.

**Character:** A clean geometric sans for anything written in prose, paired against its own monospace sibling for anything that's a measurement. The pairing IS the instrument-panel metaphor: prose explains, mono reports.

### Hierarchy
- **Headline** (600, `clamp(1.5rem, 2.5vw, 1.875rem)`, 1.2 line-height, -0.01em): Page titles — "Connections," a workflow's name.
- **Title** (500, 1.0625rem, 1.3 line-height): Card and section headers — a workflow card's name, a settings section label.
- **Body** (400, 0.9375rem, 1.6 line-height, 65–75ch max): Summaries, descriptions, form helper text.
- **Label** (500, 0.75rem, 1 line-height, 0.02em tracking, Geist Mono): Status pills, counts (`7d: 12 runs`), timestamps, IDs. Always mono, always this exact size — it's the system's "readout" voice and should never be mistaken for prose.

### Named Rules
**The Readout Rule.** Any number that describes a measurement of the system — run counts, error counts, timestamps, durations — renders in Geist Mono at the Label size, even mid-sentence. Anything a human wrote (a summary, a label, a name) renders in Geist Sans. If you're unsure which a string is, ask whether n8n or a human produced it.

## 4. Elevation

Flat by default — no `box-shadow` anywhere in the system. Depth is conveyed by three stepped surface lightnesses (bg → panel → panel-raised) plus 1px hairline borders, the way a physical instrument panel separates its dials with bezels, not by lighting effects. The one allowed deviation: a soft amber glow (not a shadow) on the focus ring of interactive elements, since this is a UI you operate with a keyboard during an incident and the focus state must be unmistakable.

### Named Rules
**The Bezel, Not Glow Rule.** Cards and modals separate from their background with a 1px hairline border and a lighter surface step — never a drop shadow. The one exception is the focus ring (see above); everything else is flat.

## 5. Components

### Buttons
- **Shape:** 6px radius (`{rounded.sm}`) — a small, deliberate corner, not pill-shaped, not square.
- **Primary:** Terminal Amber fill, near-black text (`#0a0a0a`, not pure ink — amber is too bright for the light-text rule), Geist Mono label-weight text, 10px/18px padding. Reserved for the one primary action per screen (Sync, Connect, Generate summary, Log in).
- **Secondary/Ghost:** Transparent background, 1px hairline border, ink text. Hover: border brightens to instrument-blue, no fill change.
- **Hover/Focus:** Primary brightens (L 0.62 → 0.68) rather than darkening — a dark UI should brighten on interaction, not muddy further. Focus state: 2px amber glow ring, visible on every interactive element, never suppressed.

### Status Pills
- **Failing / Silent / Orphaned:** Filled pill, `{rounded.full}`, Geist Mono label text, near-black (`#0a0a0a`) text on the status color (Helmholtz rule: these are saturated mid-tone fills, but `#0a0a0a` reads more "instrument readout" than pure white here — confirm contrast per pill at implementation, adjust to white if a given status color's measured contrast falls short).
- **Healthy:** No pill. A small solid 6px dot in Healthy Green, inline before the label, label itself in secondary-text mono.
- **Unused:** No pill, no dot — secondary-text mono label only, optionally a hollow/outlined 6px dot.

### Cards / Containers (workflow cards, connection cards)
- **Corner Style:** 10px radius (`{rounded.md}`) — one step softer than buttons, since these hold more content.
- **Background:** Panel surface, 1px hairline border.
- **Shadow Strategy:** None — see Elevation.
- **Internal Padding:** 24px (`{spacing.lg}`).
- Cards are used here because list-of-workflows genuinely is the right affordance (a real list of distinct, equally-weighted items) — not the lazy default. Never nest a card inside a card; a workflow card's internal sections are separated by hairlines, not inner cards.

### Inputs / Fields
- **Style:** Panel-raised background, 1px hairline border, 6px radius, ink text, secondary-text placeholder (still ≥4.5:1, not the muted default).
- **Focus:** Border shifts to instrument-blue, 2px amber glow ring matches buttons' focus treatment for consistency.
- **Error:** Border shifts to Failing Red; error message renders below in Failing Red, Geist Sans body size (prose, not mono — it's a human-readable message, not a measurement).

### Navigation
- Single top bar, panel background, 1px hairline bottom border (replaces the current plain `border-gray-200`). Wordmark in terminal-amber. Active/current section indicated by instrument-blue text, not a filled pill or underline bar.

## 6. Do's and Don'ts

### Do:
- **Do** keep Terminal Amber to primary actions and the wordmark only (The One Signal Rule).
- **Do** render `healthy` and `unused` as quiet, low-color text states (The Calm Default Rule) — color density should rise only with real problems.
- **Do** set every number that measures the system (counts, timestamps, durations) in Geist Mono (The Readout Rule).
- **Do** separate every surface with a hairline border and a lighter surface step, never a shadow (The Bezel, Not Glow Rule).
- **Do** pair every status color with a text label, never color alone — required for WCAG AA and PRODUCT.md's color-blind accessibility note.

### Don't:
- **Don't** use purple/blue gradients or a gradient-accented hero-metric tile — PRODUCT.md names this directly as the generic-SaaS-dashboard look to avoid.
- **Don't** build identical icon+heading+text card grids as a default layout move.
- **Don't** use `border-left`/`border-right` as a colored accent stripe on any card, list row, or alert.
- **Don't** use `background-clip: text` gradient headings — emphasis comes from weight/size/mono, never a gradient.
- **Don't** add a drop shadow anywhere outside the one allowed focus-ring glow.
- **Don't** let a healthy dashboard look as colorful as a broken one — if every workflow is healthy, the screen should look almost monochrome.
