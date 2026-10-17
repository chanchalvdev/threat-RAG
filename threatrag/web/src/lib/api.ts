import axios from 'axios'

const API_KEY = import.meta.env.VITE_API_KEY // optional backend API_KEY guard; OIDC in Phase 4B
export const apiHeaders = (extra: Record<string, string> = {}): Record<string, string> =>
  API_KEY ? { ...extra, 'X-API-Key': API_KEY } : extra

const http = axios.create({ baseURL: '/api/v1', headers: apiHeaders() })

export interface SourceDoc {
  text: string
  source: string
  doc_type: string
  score: number
}

export interface RAGResponse {
  answer: string
  sources: SourceDoc[]
  tokens_used: number
  confidence: 'high' | 'medium' | 'low'
}

export interface IngestStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  chunks_processed: number
  total_chunks: number
  error: string | null
}

export interface IngestStats {
  collection: string
  total_vectors: number
  doc_type_counts: Record<string, number>
}

export type SSEEvent =
  | { type: 'source'; data: SourceDoc }
  | { type: 'chunk'; data: string }
  | { type: 'thought'; data: string }
  | { type: 'tool_call'; data: { name: string; input: string; tool_use_id: string } }
  | { type: 'tool_result'; data: string; tool_use_id: string }
  | { type: 'done'; session_id?: string; total_tokens?: number }
  | { type: 'error'; data: string }

export interface ReportSummary {
  id: string
  ioc: string
  ioc_type: string
  summary: string
  created_at: string
  similarity?: number | null
}

export interface EvaluationRecord {
  id: string
  question: string
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number | null
  overall: number
  created_at: string
}

// --- REST calls ---

export const listReports = (limit = 10) =>
  http.get<ReportSummary[]>('/investigate/reports', { params: { limit } }).then(r => r.data)

export const getEvaluationHistory = (limit = 50) =>
  http.get<EvaluationRecord[]>('/evaluate/history', { params: { limit } }).then(r => r.data)

export const runEvaluation = (body: { question: string; answer: string; contexts: string[]; ground_truth?: string }) =>
  http.post<Record<string, number | null>>('/evaluate', body).then(r => r.data)

export const queryRAG = (question: string, docTypes?: string[], k = 6) =>
  http.post<RAGResponse>('/query', { question, doc_types: docTypes, k }).then(r => r.data)

export const ingestPDF = (file: File, docType: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', docType)
  return http.post<{ job_id: string }>('/ingest/pdf', form).then(r => r.data)
}

export const ingestMITRE = () =>
  http.post<{ job_id: string }>('/ingest/mitre').then(r => r.data)

export const ingestOWASP = () =>
  http.post<{ job_id: string }>('/ingest/owasp').then(r => r.data)

export const getIngestStatus = (jobId: string) =>
  http.get<IngestStatus>(`/ingest/status/${jobId}`).then(r => r.data)

export const getIngestStats = () =>
  http.get<IngestStats>('/ingest/stats').then(r => r.data)

export const getHealth = () =>
  axios.get<{ status: string }>('/health').then(r => r.data)

// --- SSE streaming ---

export async function streamQuery(
  question: string,
  onEvent: (event: SSEEvent) => void,
  sessionId?: string,
): Promise<string | undefined> {
  const endpoint = sessionId ? '/api/v1/chat/stream' : '/api/v1/query/stream'
  const body = sessionId
    ? JSON.stringify({ question, session_id: sessionId })
    : JSON.stringify({ question, k: 6 })

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body,
  })

  if (!res.ok) {
    const payload = await res.json().catch(() => null)
    const detail = payload?.detail
    const message = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
      : typeof detail === 'string' ? detail : `Request failed (HTTP ${res.status})`
    throw new Error(message)
  }

  const newSessionId = res.headers.get('X-Session-ID') ?? undefined
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          onEvent(JSON.parse(line.slice(6)) as SSEEvent)
        } catch {}
      }
    }
  }

  return newSessionId
}
