---
name: ThreatRAG
description: A cross-reference index for threat intelligence; every answer, source and agent is a filed card with a serial.
colors:
  ground: "#E3DBC7"
  card: "#F7F2E5"
  card-2: "#EDE6D4"
  ink: "#18191A"
  ink-2: "#464237"
  ink-3: "#5F584A"
  rule: "#CDC2A9"
  rule-strong: "#18191A"
  rail: "#1D2A26"
  rail-2: "#2A3A33"
  rail-ink: "#DCE3DA"
  rail-ink-2: "#9DB0A4"
  vermilion: "#B8321B"
  cobalt: "#255E9E"
  ochre: "#8A5F00"
  ochre-fill: "#D9A21B"
  cabinet-green: "#2D7A4C"
  act: "#B8321B"
  on-act: "#FFFFFF"
  ground-dark: "#0F1411"
  card-dark: "#18201B"
  card-2-dark: "#202A24"
  ink-dark: "#ECE6D6"
  ink-2-dark: "#C3BCAA"
  ink-3-dark: "#9C9584"
  rule-dark: "#2E3A33"
  rule-strong-dark: "#AEB8AA"
  rail-dark: "#090D0B"
  rail-2-dark: "#17211C"
  rail-ink-2-dark: "#93A69A"
  vermilion-dark: "#EE6A4F"
  cobalt-dark: "#7FA9E6"
  ochre-dark: "#E3B54A"
  cabinet-green-dark: "#6CC08A"
  act-dark: "#E2583B"
  on-act-dark: "#140906"
typography:
  display:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "3rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 72"
  headline:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 80"
  title:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 80"
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.625
    fontFeature: "'tnum' 1"
  label:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    lineHeight: "1rem"
    letterSpacing: "0.12em"
  serial:
    fontFamily: "'Courier Prime', ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: "1rem"
  indicator:
    fontFamily: "'Courier Prime', ui-monospace, monospace"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: "1.75rem"
rounded:
  none: "0px"
  chip: "2px"
  hole: "9999px"
spacing:
  gutter: "16px"
  gutter-wide: "32px"
  card-inset: "14px"
  section: "32px"
  tab-clearance: "13px"
  page-max: "90rem"
  rail-width: "232px"
components:
  button-act:
    backgroundColor: "{colors.act}"
    textColor: "{colors.on-act}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "10px 20px"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "6px 12px"
  button-line-hover:
    backgroundColor: "{colors.card-2}"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
  field:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px 16px 16px"
  card-quiet:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 14px"
  chip-ref:
    backgroundColor: "{colors.cobalt}"
    textColor: "{colors.card}"
    typography: "{typography.serial}"
    rounded: "{rounded.chip}"
    padding: "3px 6px"
  nav-item:
    backgroundColor: "{colors.rail}"
    textColor: "{colors.rail-ink}"
    height: "44px"
    padding: "0 20px"
  nav-item-active:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    height: "44px"
---

# Design System: ThreatRAG

## Overview

**Creative North Star: "The Cross-Reference Index"**

ThreatRAG is drawn as a mid-century signals-intelligence card index. Everything the system produces (an answer, a retrieved passage, an agent's work, a saved report, a tool call) is a filed card with a serial: `S-1`, `AG-2`, `A-1`, `L-3`, `Q-1`, `R-7E41C0`. Citations are cross-references: an `S-n` chip in the prose and the tabbed source card it points to light each other on hover or focus. The shell is a filing-cabinet green rail; the work surface is card stock on a darker card-stock ground in light mode, and cabinet-interior charcoal green in dark.

Structure comes from rules, not boxes or shadows: a 3px ink rule across the top of a card, 1px rules between rows, coloured index tabs protruding above card tops. Colour is signal ink, used on tabs, chips, stamps and state words, never as a wash. Density is that of a working tool: compact rows, mono identifiers, tabular numerals everywhere. The world refuses the near-black neon SOC console: no glow, no glass, no gradient.

**Key Characteristics:**
- Every artifact carries a serial in Courier Prime; one serial system across the app.
- Cards are flat card stock with a heavy top rule; coloured tabs protrude above them.
- Four signal inks with fixed meanings: vermilion, cobalt, ochre, cabinet green.
- Archivo at condensed width (wdth 72-80) for headings, normal width for UI text.
- Magnitude shown as a five-hole punch row, not a bar or a percentage alone.
- Square corners everywhere except the 2px cross-reference chip and the round punch holes.

## Colors

Card stock and filing-cabinet green, struck through with four signal inks. Every value has a light and a dark counterpart (frontmatter keys ending `-dark`); the source of truth is the RGB-channel custom properties in `threatrag/web/src/index.css`, so Tailwind can apply alpha.

### Primary
- **Vermilion Stamp** (`vermilion`, also `act`): the single action colour (the Investigate and Send buttons, the text caret, the typing cursor) and the critical signal: the Critic agent's tab and send-backs, CVE source tabs, the CRITICAL / HIGH severity stamps, error text. In dark mode the action fill (`act-dark`) is a deeper vermilion than the signal ink (`vermilion-dark`) so white-on-red and red-on-charcoal both hold contrast.

### Secondary
- **Index Cobalt** (`cobalt`): the Researcher agent, MITRE ATT&CK source tabs and chips, links in prose, the focus ring and the focused-field border.

### Tertiary
- **File Ochre** (`ochre` for text, `ochre-fill` for fills): the Reporter agent and OWASP LLM sources, warnings, the medium severity stamp, text selection (45% fill). `ochre-fill` is the same in both themes and always carries near-black text.
- **Cabinet Green** (`cabinet-green`): success only: "Filed", "exact ID match", Online, low severity, custom-upload sources.

### Neutral
- **Card Stock Ground** (`ground`): the page behind the cards; also the active nav item, which reads as a card pulled out of the rail.
- **Card Stock** (`card`) and **Worn Card** (`card-2`): card faces; `card-2` is the hover face for rows and line buttons.
- **Ink / Ink 2 / Ink 3** (`ink`, `ink-2`, `ink-3`): primary text, secondary text, and metadata (labels, serials, placeholders). Ink 3 is the floor; nothing lighter carries text.
- **Rule** (`rule`) and **Strong Rule** (`rule-strong`): 1px dividers and field borders; the 3px card top rule and page-header underline.
- **Cabinet Rail** (`rail`, `rail-2`, `rail-ink`, `rail-ink-2`): the navigation shell, its hover row, its text and its metadata.

### Named Rules
**The Fixed Ink Rule.** Each signal ink means one thing everywhere: vermilion is critical and the Critic, cobalt is the Researcher and ATT&CK, ochre is the Reporter and OWASP, green is success. Never use a signal ink decoratively or reassign it.

**The One Action Rule.** Only the primary submit on a page is filled vermilion. Everything else is a line or text button.

## Typography

**Display Font:** Archivo (variable, width 62-125, weight 400-800), condensed via `font-variation-settings: 'wdth' 72`
**Body Font:** Archivo at normal width (`'wdth' 100`), with ui-sans-serif fallback
**Label/Mono Font:** Courier Prime 400/700, with ui-monospace fallback

**Character:** A condensed, heavy grotesque for headings stamped onto cards, paired with a typewriter mono that types the identifiers. Tabular numerals are on globally so counts and metrics never jitter.

### Hierarchy
- **Display** (800, 2.25rem mobile / 3rem desktop, line-height 1, wdth 72): page titles only ("Investigate an indicator", "Ask the index"); always followed by a strong rule underline.
- **Headline** (800, 1.5rem, wdth 80): section and report titles inside cards.
- **Title** (800, 1.25rem, wdth 80): agent names on agent cards and similar card headings.
- **Body** (400, 0.875rem, relaxed leading): UI and prose; reading measure capped at 60-72ch.
- **Label** (700, 0.6875rem, 0.12em tracking, uppercase, ink-3): table headers, small section headings, status words ("FILED", "WORKING"), doc-type lines.
- **Serial** (Courier Prime 400, 0.75rem, ink-3): artifact serials and file numbers.
- **Indicator** (Courier Prime 400, 1.125rem): the IOC input. Mono at body size also sets IDs, IOCs, model names and tool inputs.

### Named Rules
**The Typewriter Rule.** Courier Prime sets only machine identity: serials, IDs, IOCs, hashes, model names, tool I/O, keyboard hints. Never prose, never buttons, never headings.

**The Condensed Heading Rule.** Headings use Archivo condensed (wdth 72 for display, 80 for headline/title) at 800; never set a heading in a different family.

## Layout

A fixed 232px cabinet rail on the left at `md` (768px) and up; below it the rail collapses to a top bar with the wordmark and a four-column bottom-of-rail nav strip (56px tall items, icon over label). The main column scrolls independently inside a full-viewport frame.

Pages sit in a centred column capped at 90rem (Investigate, Index, Telemetry) or 3xl (Ask), with a 16px gutter on mobile and 32px from `md`, 32-40px top padding, and 32px between sections. Two-pane layouts use asymmetric grids (`report | 22rem source tray`, `1fr | 0.8fr`) that stack to one column below `lg`. The three agent cards form a single ruled row at `md` (1px rule between them, no gap) and stack with 24px gaps below.

Cards with tabs need 13px of clearance above them for the protruding tab. Card insets are tight: 12-16px.

## Elevation & Depth

Flat. Depth is expressed by rules and tabs: a card is a lighter sheet with a 3px strong top rule (or a 1px rule for quiet cards) sitting on the darker ground. The only shadow in the system is state-driven: when a source card is cross-referenced, it lifts 2px with a soft drop and a 2px ink ring.

### Shadow Vocabulary
- **Cross-reference lift** (`box-shadow: 0 6px 14px -6px rgb(0 0 0 / 0.35)` with `translateY(-2px)` and a 2px ink/60 ring offset 2px): only on the source card matching the hovered or focused S-n chip.

### Named Rules
**The Flat Card Rule.** Cards are flat at rest. Lift appears only as the answer to a cross-reference, never as decoration or hover polish.

## Shapes

Square. Cards, buttons, fields, the IOC slip, severity stamps and code blocks all have 0 radius. Two exceptions carry meaning: the cross-reference chip (2px) so it reads as a slip of paper inset in prose, and punch holes and the health dot (fully round). Index tabs are 56 x 10px coloured rectangles positioned 13px above a card's top-left (16px in); on cross-reference the tab grows to 14px tall and rises.

## Components

### Buttons
Blunt and printed; never rounded, never shadowed.
- **Shape:** square corners (0px), semibold 0.875rem, 8px icon gap.
- **Action:** vermilion fill with white text (dark: deep vermilion with near-black text), 10px 20px; the IOC slip's submit is 14px 28px at 15px. Hover drops to 90% fill.
- **Line:** 1px strong rule at 70% alpha, ink text, 6px 12px; hover fills with worn card.
- **Text:** ink-2, medium weight, no padding; hover to ink.
- **Disabled:** 45% opacity, not-allowed cursor. Focus is the global 2px cobalt outline offset 2px.

### Chips (cross-reference)
- **Style:** Courier Prime bold at 0.78em, 3px 6px, 2px radius, filled with the source type's ink (cobalt ATT&CK, ochre-fill OWASP, vermilion CVE, green custom) and card-coloured text; reads `S-n` followed by the ID at normal weight.
- **State:** hover or focus lifts the chip 2px with a 2px ink ring and lights its source card; click opens and scrolls to the card. An unresolved citation renders as plain bracketed mono text in ink-3, not as a chip.

### Severity stamps
Bold words in reports that name a severity become stamps: uppercase, 0.08em tracking, 0.78em, 2px border, square. Critical is filled vermilion; high, medium and low are outlined in vermilion, ochre and green.

### Cards / Containers
- **Corner Style:** square (0px).
- **Background:** card stock; idle agent cards at 70% opacity.
- **Shadow Strategy:** none at rest (see Elevation & Depth).
- **Border:** filed card: 3px strong top rule; quiet card: 1px rule on top only. Inner sections divided by 1px rules.
- **Internal Padding:** 14-16px horizontal, 12-16px vertical.
- **Tab:** optional coloured index tab protruding above the top-left, in the card's signal ink.

### Inputs / Fields
- **Style:** card fill, 1px rule border, square, 0.875rem ink text, ink-3 placeholder.
- **Hover / Focus:** border darkens to ink-3 on hover and turns cobalt on focus; no outline glow.
- **IOC slip:** a filed card holding a type select, a large mono indicator input and the action button in one row, divided by 1px rules; stacks on mobile.

### Navigation
- **Style:** cabinet rail with the condensed wordmark THREATRAG (800, 0.02em tracking) over a rail-ink-2 tagline. Items are 44px rows: 17px line icon, label, and a mono keyboard hint (1-4) right-aligned.
- **States:** default rail-ink at 80%; hover fills rail-2; active becomes a ground-coloured row with ink text and bold weight, as if pulled from the drawer.
- **Mobile:** a four-column strip under the wordmark, icon over 0.6875rem label, 56px tall.

### Punch-hole magnitude (signature)
A row of five 8px round holes with 1.5px borders in the current text colour; filled holes are solid, empty holes are hollow at 50% opacity. Similarity score maps to holes by `ceil(score x 5)`, clamped 1-5, always paired with the mono "sim NN%" reading. The same row counts research passes (cobalt, at least three holes).

### Ticker (signature)
Metric values update in place: each character sits in its own cell and only changed characters replay a 220ms drop-in (translateY -60%, opacity 0.2 to 1, expo-out). Values never cross-fade or count up.

### Agent file and tool log
The three agents (AG-1 Researcher cobalt, AG-2 Critic vermilion, AG-3 Reporter ochre) file left to right as tabbed cards. A working agent shows a short ink bar running along its 3px top rule. The Critic's send-backs are listed with a return icon and "Returned to Researcher." in vermilion. Tool calls are a ruled list of `L-n` rows with mono tool inputs.

### Motion
Cards and new rows file in by an 8px drop-and-settle (240ms, `cubic-bezier(0.16, 1, 0.3, 1)`). Tabs and chips lift on cross-reference (150-200ms expo). The active-agent rule run loops at 1.4s. Everything collapses to near-zero under `prefers-reduced-motion`.

## Do's and Don'ts

### Do:
- **Do** give every new artifact a mono serial in the existing system (`S-n`, `AG-n`, `A-n`, `L-n`, `Q-n`, `R-XXXXXX`).
- **Do** build structure from rules: a 3px strong top rule on filed cards, 1px rules between rows and panes.
- **Do** mark a card's type with a protruding 56 x 10px index tab in its signal ink.
- **Do** show relevance or counts with the five-hole punch row, paired with the exact number.
- **Do** define every colour as an RGB-channel custom property with light and dark values, and reference it through the Tailwind token.
- **Do** keep text at ink-3 or darker on card stock in both themes.

### Don't:
- **Don't** use glow, glassmorphism, gradients or neon-on-black panels; this is not a SOC console.
- **Don't** round cards, buttons or fields; only the cross-reference chip (2px) and holes are curved.
- **Don't** add resting shadows; the cross-reference lift is the only shadow.
- **Don't** fill a second button with vermilion on the same view.
- **Don't** set prose, buttons or headings in Courier Prime, or IDs and IOCs in Archivo.
- **Don't** redact or escape indicators of compromise in display; only credential formats are redacted.
