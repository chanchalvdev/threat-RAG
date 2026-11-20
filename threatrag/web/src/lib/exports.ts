import axios from 'axios'
import { apiHeaders } from './api'

const http = axios.create({ baseURL: '/api/v1', headers: apiHeaders() })

export interface ExportOptions { pdf: boolean; slack: boolean; teams: boolean }
export type Channel = 'slack' | 'teams'

export const getExportOptions = () => http.get<ExportOptions>('/investigate/exports').then(r => r.data)

export const notifyChannel = (reportId: string, channel: Channel) =>
  http.post<{ sent: Channel }>(`/investigate/reports/${reportId}/notify`, { channel }).then(r => r.data)

/** Fetch with auth headers (a plain link would not send them), then hand the file to the browser. */
export async function downloadPdf(reportId: string, filename: string): Promise<void> {
  const res = await fetch(`/api/v1/investigate/reports/${reportId}/pdf`, { headers: apiHeaders() })
  if (!res.ok) throw new Error('PDF export failed (HTTP ' + res.status + ')')
  const url = URL.createObjectURL(await res.blob())
  Object.assign(document.createElement('a'), { href: url, download: filename }).click()
  URL.revokeObjectURL(url)
}
