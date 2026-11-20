import axios from 'axios'
import { apiHeaders } from './api'

const http = axios.create({ baseURL: '/api/v1', headers: apiHeaders() })

/** One step's outcome; `error` when that feed failed, otherwise feed-specific counts. */
export type FeedStep = { error?: string; [key: string]: unknown }

export interface FeedStatus {
  at: string | null
  ok: boolean | null
  regressed: boolean
  steps: Record<string, FeedStep>
}

export const getFeedStatus = () => http.get<FeedStatus>('/ingest/feeds').then(r => r.data)
