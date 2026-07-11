# ThreatRAG — User Guide

A walkthrough of the four screens in the app: **Chat**, **Knowledge Base**, **Investigate**,
and **Analytics**. For getting the app running locally, see [start-services.sh](start-services.sh)
(`./start-services.sh` / `status` / `stop`) — this guide assumes it's already up at
**http://localhost:5174**.

---

## 1. Before you start: load the knowledge base

ThreatRAG answers questions by retrieving from a vector store — if it's empty, Chat and
Investigate have nothing to cite. Do this once per fresh environment:

1. Open the **Knowledge Base** tab (left sidebar, database icon).
2. Click **MITRE ATT&CK** to ingest the technique corpus, and **OWASP LLM Top 10** for the
   LLM-specific vulnerability corpus. Each click starts a background ingestion job.
3. Watch the job card that appears under the buttons — it shows a progress bar and a
   chunk counter (e.g. `340/812 chunks`) while running, then turns green (✓) when done or
   red (✗) with an error message if it fails.
4. Optionally, drag a PDF onto the dashed drop zone (or click it to browse) to ingest your
   own threat intel document — it's tagged as `custom` doc type.
5. The right-hand panel shows a live total vector count and a bar chart of vectors per
   source. It refreshes automatically every 5 seconds, so you'll see the count climb as
   ingestion progresses.

> **Note:** the "vectors by source" chart depends on the backend correctly tagging each
> vector's `doc_type` — if it's showing empty even after ingesting, that's a backend
> reporting quirk, not a sign that ingestion failed. Check the total count instead.

---

## 2. Chat — ask a question

The main screen (chat bubble icon). This is a conversational Q&A interface backed by the
knowledge base.

1. Type a question in the box at the bottom, e.g. *"What is T1055 Process Injection?"* or
   *"What CVEs affect Apache Log4j?"*. No pre-loaded question? Click one of the suggestion
   cards on the empty-state screen to try one instantly.
2. **Questions must be at least 10 characters.** If you type something shorter, the send
   button disables and a small amber hint appears under the input — this is enforced by
   the backend, so the UI warns you before you even submit.
3. Press **Enter** to send (**Shift+Enter** for a new line instead).
4. While the assistant is thinking, you'll see a pulsing three-dot indicator, then the
   answer streams in token-by-token.
5. Once the answer is cited, a **"N cited sources"** link appears below it — click to
   expand a list of the exact passages used, each with:
   - a doc-type badge (`mitre attack`, `owasp llm`, `cve`, `custom`)
   - a relevance percentage and bar
   - a **Copy text** button to grab the raw passage
6. Hover over any assistant answer to reveal a **copy** icon in the top-right corner —
   copies the full answer as plain text/Markdown.
7. If the agent used a tool (KB search, CVE lookup, web search) to answer, a timeline of
   those tool calls appears under the message — click one to expand its input/output.
8. Click **New conversation** (top of the message list) to clear history and start a fresh
   session — this also drops the session ID so context doesn't leak between topics.
9. If something goes wrong (backend down, LLM error), the message bubble shows a red
   warning with the error text instead of hanging silently — no need to guess whether it's
   still "thinking."

---

## 3. Investigate — multi-agent IOC deep-dive

The magnifying-glass tab. Use this instead of Chat when you want a structured, multi-pass
report on a specific indicator rather than a single conversational answer.

1. Choose the **IOC type** from the dropdown: `CVE`, `TECHNIQUE`, `IP`, `HASH`, or `DOMAIN`.
2. Enter the indicator itself, e.g. `CVE-2021-44228` or `T1055`, and press **Enter** or
   click **Investigate**.
3. Watch the three-stage pipeline animate left to right:
   - **Researcher** — pulls intel from the knowledge base, NVD, and web search
   - **Critic** — challenges the findings and flags gaps
   - **Reporter** — writes the final structured report
   Each card lights up (cyan glow) while active and turns green with a checkmark when
   done; a live snippet of its latest output shows underneath.
4. Once the Reporter finishes, the full **Markdown report** streams into the panel below
   the pipeline — typically an executive summary, technical details, and recommended
   actions for that IOC.
5. Use the two buttons above the report:
   - **Copy Markdown** — copies the raw report text
   - **Export PDF** — opens your browser's print dialog (choose "Save as PDF")
6. If the request fails outright (e.g. backend unreachable), a red banner appears above
   the pipeline with the error instead of the cards spinning forever.

---

## 4. Analytics — check answer quality (RAGAs)

The bar-chart tab. Two things live here: a quality-trend overview, and a manual scoring
tool.

**Trend charts** (top section) show four RAGAs metrics — Faithfulness, Answer Relevancy,
Context Precision, Context Recall — each with a green dashed line at 0.8 (target) and
yellow at 0.5 (floor). *(Currently populated with illustrative demo data, not live
history — treat it as a preview of the layout rather than production metrics.)*

**Run an evaluation** (bottom section) scores one Q&A exchange on demand:

1. Fill in:
   - **Question** — the question that was asked
   - **Answer** — the answer that was generated (e.g. paste one from Chat)
   - **Contexts** — the retrieved passages used to generate it, **one per line**
   - **Ground truth** *(optional)* — a reference answer; supplying this unlocks the
     Context Recall score, which can't be computed without it
2. Click **Evaluate** (disabled until Question, Answer, and Contexts are all filled).
3. Results appear as color-coded bars: green ≥ 0.8, yellow ≥ 0.5, red below — each with
   the exact numeric score to three decimal places.
4. A red error banner appears if the evaluation call fails (e.g. RAGAs/backend not
   configured) instead of hanging on "Evaluating…" indefinitely.

---

## Quick reference

| Task | Where |
|---|---|
| Ask a security question | Chat |
| Load MITRE/OWASP/custom PDFs into the KB | Knowledge Base |
| Deep-dive a CVE, technique, IP, hash, or domain | Investigate |
| Score answer quality against RAGAs metrics | Analytics |
| Check backend connectivity | Green/red dot, top-right of every page |
| See which model is answering | Model chip, top-right ( `kimi-k2.7`, `minimax-m3`, etc.) |

## Troubleshooting

- **"Offline" red dot in the header** — the backend isn't reachable; run
  `./start-services.sh status` from the repo root to see which piece is down.
- **Chat send button greyed out** — your question is under 10 characters; add a bit more
  detail.
- **Knowledge Base chart empty despite a nonzero vector count** — known backend reporting
  gap in `doc_type_counts`; the total count is still accurate.
- **Investigate/Analytics shows a red error banner** — read the message directly; it's
  passed through from the backend (e.g. "HTTP 500", "RAGAs pipeline not configured")
  rather than a generic failure.
