---
version: 1
slug: "threatrag-web"
primary_target: "threatrag/web"
related_targets: []
---

# ThreatRAG web app — surface brief

Scope: the whole web app (threatrag/web): Investigate (landing), Ask (chat), Index (knowledge base), Telemetry (analytics). Visitor mode: Operate.
Audience: cold visitors from a public demo link judging the build; it must also work as a real analyst tool.
Job: launch an investigation or ask a question within seconds; see the reasoning (tool calls, Critic send-backs, citations) happen.
Constraints: Playwright + Vitest copy/accessible names are contract; light and dark themes; prefers-reduced-motion honoured; IOCs never redacted.

## Direction contract

THESIS: ThreatRAG is a cross-reference index. Every answer, source, tool call and report is a filed card with a serial; citations are cross-references you follow by hovering. Refuses the near-black neon SOC console with glowing cyan panels.

OWN-WORLD: Filing-cabinet green shell rail (#1E2B27 family), card-stock ground and cards (light) / cabinet-interior charcoal-green (dark). Signal inks on index tabs: vermilion (critical, Critic), cobalt (Researcher, primary refs), ochre (Reporter, warnings), cabinet green (success). Archivo (variable width, condensed for headings) for UI; Courier Prime only for IDs, IOCs, serials and tool I/O. Structure from 1px rules and a 3px top rule on cards; tabs protrude from card tops; punch-hole rows encode magnitude. No glow, no glass, no gradient.

STORY: The visitor types or picks an indicator, watches three agent cards get filed (Critic visibly returning work), reads a report whose S-n references light their source card, and exports STIX.

FIRST VIEWPORT: Left 232px cabinet rail with nav (Investigate active), status and model. Main: page title "Investigate an indicator" with file serial; a full-width IOC slip (type select, mono input, vermilion "Investigate" action) with example indicators below; three agent cards in a single ruled row; report card (left, wide) with source tray (right, 360px). Empty state shows recent investigation cards.

FORM: Cross-Reference Index (1940s signals-intelligence card index), candidate 5 of the ordered grounded list, assigned by the roll. seed:a8e2c982cf4d6576. Signature move: cross-reference highlight — hovering or focusing an S-n citation lifts its tabbed source card in the tray (and vice versa); punch-hole magnitude ramp for relevance. Raises: 1px-rule structure (Plate Annual); fixed five-step magnitude ramp (Star Atlas); one serial system across artifacts (Fac Catalog); in-place per-digit metric updates in fixed columns (Split-Flap). Motion grammar: cards file in by a short drop-and-settle (translateY 8px, 220ms expo-out), tab lift on cross-reference, nothing else.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
