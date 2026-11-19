import axios from 'axios'
import { apiHeaders } from './api'

const http = axios.create({ baseURL: '/api/v1', headers: apiHeaders() })

export type FeedbackTarget = 'answer' | 'report'

export interface FeedbackRecord {
  id: string
  target: FeedbackTarget
  target_id: string
  rating: number
  note: string
  question: string
  created_at: string
}

export interface FeedbackSummary {
  answer: { up: number; down: number }
  report: { up: number; down: number }
  recent_down: FeedbackRecord[]
}

export interface FeedbackBody {
  target: FeedbackTarget
  target_id: string
  rating: 1 | -1
  note?: string
  question?: string
  answer?: string
}

export const sendFeedback = (body: FeedbackBody) => http.post<FeedbackRecord>('/feedback', body).then(r => r.data)

export const getFeedbackSummary = () => http.get<FeedbackSummary>('/feedback/summary').then(r => r.data)

/** Fetch with auth headers (a plain link would not send them), then hand the file to the browser. */
export async function downloadCandidates(): Promise<void> {
  const res = await fetch('/api/v1/feedback/candidates', { headers: apiHeaders() })
  if (!res.ok) throw new Error('Export failed (HTTP ' + res.status + ')')
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: 'golden-candidates.jsonl' })
  a.click()
  URL.revokeObjectURL(url)
}
