import { useState } from 'react'
import { apiHeaders, type ReportSummary, type SourceDoc } from './api'

export type IOCType = 'ip' | 'hash' | 'domain' | 'cve' | 'technique'
export type NodeId = 'researcher' | 'critic' | 'reporter'
export type NodeStatus = 'idle' | 'active' | 'done'

export interface NodeState {
  status: NodeStatus
  detail: string
}

type InvestigationEvent =
  | { type: 'node_start'; node: NodeId; iteration: number }
  | { type: 'node_done'; node: NodeId; summary: string }
  | { type: 'routing'; from: NodeId; to: NodeId; reason: string }
  | { type: 'tool_call'; node: NodeId; name: string; input: string }
  | { type: 'report_chunk'; data: string }
  | { type: 'done'; report_id: string | null; iterations: number; sources: SourceDoc[]; similar: ReportSummary[] }
  | { type: 'error'; data: string }

const IDLE: Record<NodeId, NodeState> = {
  researcher: { status: 'idle', detail: '' },
  critic: { status: 'idle', detail: '' },
  reporter: { status: 'idle', detail: '' },
}

/** Drives POST /investigate/stream and folds its SSE events into UI state. */
export function useInvestigation() {
  const [nodes, setNodes] = useState(IDLE)
  const [iteration, setIteration] = useState(0)
  const [reportChunks, setReportChunks] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Extract<InvestigationEvent, { type: 'done' }> | null>(null)

  const patch = (id: NodeId, next: Partial<NodeState>) =>
    setNodes(prev => ({ ...prev, [id]: { ...prev[id], ...next } }))

  const handle = (evt: InvestigationEvent) => {
    switch (evt.type) {
      case 'node_start':
        patch(evt.node, { status: 'active' })
        if (evt.node === 'researcher') setIteration(evt.iteration)
        break
      case 'node_done': patch(evt.node, { status: 'done', detail: evt.summary }); break
      case 'tool_call': patch('researcher', { detail: `→ ${evt.name} ${evt.input}` }); break
      case 'routing':
        if (evt.to === 'researcher') patch('critic', { status: 'idle', detail: `Sent back: ${evt.reason}` })
        break
      case 'report_chunk': setReportChunks(prev => [...prev, evt.data]); break
      case 'done': setResult(evt); break
      case 'error': setError(evt.data); break
    }
  }

  const start = async (ioc: string, iocType: IOCType) => {
    setRunning(true); setError(null); setReportChunks([]); setResult(null); setNodes(IDLE); setIteration(0)
    try {
      const res = await fetch('/api/v1/investigate/stream', {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ ioc, ioc_type: iocType }),
      })
      if (!res.ok || !res.body) {
        const payload = await res.json().catch(() => null)
        const msg = Array.isArray(payload?.detail) ? payload.detail[0]?.msg : payload?.detail
        throw new Error(msg ?? `Investigation failed (HTTP ${res.status})`)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try { handle(JSON.parse(line.slice(6)) as InvestigationEvent) } catch { /* partial line */ }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Investigation failed — is the backend running?')
    } finally {
      setRunning(false)
    }
  }

  return { nodes, iteration, reportChunks, running, error, result, start }
}
