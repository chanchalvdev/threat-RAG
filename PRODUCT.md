# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: people evaluating ThreatRAG from a public demo link — recruiters, hiring managers and engineers judging the build. They arrive cold, have a few minutes, and must see the system actually reason (retrieve, call tools, critique, report) rather than read claims about it. The UI must stay fully functional as a real analyst tool; the showcase is the working product, not a marketing page in front of it.

Secondary (inferred from the feature set, not confirmed as a target audience): security analysts asking ATT&CK / OWASP / CVE questions and investigating IOCs.

## Product Purpose
A cybersecurity RAG system that answers threat-intel questions with cited sources and runs a multi-agent investigation of an indicator. Success: a visitor launches an investigation or asks a question within seconds of landing and leaves understanding that the answers are grounded, cited and checked.

## Positioning
Grounded, inspectable reasoning: every answer cites the passages it used (with exact-ID vs similarity provenance), every tool call is visible as it happens, and investigations run a Researcher → Critic → Reporter loop where the Critic can send work back. Retrieval and guard quality are measured, not asserted (LLM-judge evaluation history, runtime telemetry, injection-guard counters).

## Operating Context
- Four areas: Investigate (multi-agent IOC run, the hero flow and landing destination), Chat (agentic Q&A with live tool timeline and cited sources), Knowledge Base (ingest MITRE ATT&CK / OWASP LLM Top 10 / PDFs, vector counts), Analytics (runtime metrics, LLM-judge quality trends, ad-hoc evaluation).
- IOC types: CVE, ATT&CK technique, IP, file hash, domain. CVE data is looked up live from NVD, not ingested.
- Investigation output: streamed markdown report, saved report id, research-pass count, KB source count, similar past investigations (pgvector), STIX 2.1 export.
- All model output streams over SSE.
- Publicly hosted with a daily model budget; requests can be rejected by the prompt-injection guard and must surface as clear errors.

## Capabilities and Constraints
- React 18 + TypeScript + Vite + Tailwind 3; lucide-react, recharts, react-markdown available.
- Existing Playwright and Vitest suites must stay green: accessible names and copy they assert on (e.g. textbox "Message", button "Send message", "Online", "Knowledge base search", "N cited source", "sim 87%", "exact ID match", "2 blocked", "Estimated cost: not priced") are product contract.
- Dark and light themes are both required.
- Motion is welcome but must fully degrade under prefers-reduced-motion.
- Indicators of compromise are never redacted or escaped in display.

## Evidence on Hand
Real backend data only: knowledge-base vector counts, evaluation history, runtime metrics, saved reports. No testimonials, customer logos or benchmark claims exist; none may be invented.

## Product Principles
1. Show the reasoning, not a claim about it — tool calls, agent handoffs and citations are the product's proof.
2. Time-to-first-wow under ten seconds: one obvious action from landing.
3. Provenance is always one glance away: every claim traces to a source or tool result.
4. A showcase that is genuinely usable — never a fake demo surface.

## Accessibility & Inclusion
WCAG AA contrast in both themes; full keyboard operation; prefers-reduced-motion honored for all non-essential motion.
