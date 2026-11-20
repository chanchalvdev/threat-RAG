import type { Page } from '@playwright/test'

export const sse = (events: object[]) => events.map(e => 'data: ' + JSON.stringify(e) + '\n\n').join('')

export const SOURCE = { text: 'One password tried against many accounts.', source: 'MITRE ATT&CK Enterprise', doc_type: 'mitre_attack', score: 0.82, ref_id: 'T1110.003' }

export async function mockApi(page: Page) {
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }))
  await page.route('**/api/v1/chat/suggestions', route => route.fulfill({ json: { suggestions: [] } }))
  await page.route('**/api/v1/metrics', route => route.fulfill({ json: {
    routes: { 'POST /api/v1/chat/stream': { requests: 3, errors_5xx: 0, p50_ms: 412.5, p95_ms: 980.1 } },
    llm: { calls: 7, tokens_in: 9120, tokens_out: 1480, p50_ms: 3100, p95_ms: 5200, estimated_cost_usd: null },
    counters: { guard_blocked: 2, guard_allowed: 9, rag_abstained: 1 },
  } }))
  await page.route('**/api/v1/evaluate/history**', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/feedback/summary', route => route.fulfill({ json: {
    answer: { up: 4, down: 1 }, report: { up: 2, down: 0 },
    recent_down: [{ id: 'f1', target: 'answer', target_id: 's:1', rating: -1, note: 'missed APT29', question: 'Which groups use T1558.003?', created_at: '2026-11-19' }],
  } }))
  await page.route('**/api/v1/investigate/reports?**', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/ingest/feeds', route => route.fulfill({ json: { at: null, ok: null, regressed: false, steps: {} } }))
  await page.route('**/api/v1/investigate/exports', route => route.fulfill({ json: { pdf: true, slack: true, teams: false } }))
  await page.route('**/api/v1/ingest/stats', route => route.fulfill({ json: {
    collection: 'threat_intel_v2', total_vectors: 3506, doc_type_counts: { mitre_attack: 3379, owasp_llm: 127 },
  } }))
}
