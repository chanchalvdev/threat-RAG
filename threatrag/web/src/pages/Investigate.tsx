import { useState } from 'react'
import { Search, Loader2, CheckCircle2, Circle } from 'lucide-react'
import { cn } from '../lib/cn'
import ReportViewer from '../components/ReportViewer'

type IOCType = 'ip' | 'hash' | 'domain' | 'cve' | 'technique'
type NodeStatus = 'idle' | 'active' | 'done'

interface AgentCard {
  id: string
  label: string
  status: NodeStatus
  lastChunk: string
}

export default function Investigate() {
  const [ioc, setIoc] = useState('')
  const [iocType, setIocType] = useState<IOCType>('cve')
  const [running, setRunning] = useState(false)
  const [reportChunks, setReportChunks] = useState<string[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [agents, setAgents] = useState<AgentCard[]>([
    { id: 'researcher', label: 'Researcher', status: 'idle', lastChunk: '' },
    { id: 'critic',     label: 'Critic',     status: 'idle', lastChunk: '' },
    { id: 'reporter',   label: 'Reporter',   status: 'idle', lastChunk: '' },
  ])

  const setAgentStatus = (id: string, status: NodeStatus, lastChunk = '') =>
    setAgents(prev => prev.map(a => a.id === id ? { ...a, status, lastChunk } : a))

  const investigate = async () => {
    if (!ioc.trim()) return
    setRunning(true)
    setReportChunks([])
    setIsStreaming(true)
    setAgents(agents.map(a => ({ ...a, status: 'idle', lastChunk: '' })))

    const res = await fetch('/api/v1/investigate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ioc, ioc_type: iocType }),
    })

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
        if (!line.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(line.slice(6))
          if (evt.type === 'node_start') setAgentStatus(evt.node, 'active')
          if (evt.type === 'node_done')  setAgentStatus(evt.node, 'done', evt.summary)
          if (evt.type === 'node_chunk') setAgentStatus(evt.node, 'active', evt.data)
          if (evt.type === 'report_chunk') setReportChunks(prev => [...prev, evt.data])
          if (evt.type === 'done') { setAgentStatus('reporter', 'done'); setIsStreaming(false) }
        } catch {}
      }
    }

    setRunning(false)
  }

  return (
    <div className="p-6 max-w-5xl space-y-6">
      {/* Input */}
      <div className="flex gap-3">
        <select value={iocType} onChange={e => setIocType(e.target.value as IOCType)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm">
          {(['cve', 'technique', 'ip', 'hash', 'domain'] as IOCType[]).map(t =>
            <option key={t} value={t}>{t.toUpperCase()}</option>
          )}
        </select>
        <input value={ioc} onChange={e => setIoc(e.target.value)}
          placeholder="CVE-2021-44228 or T1055..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500" />
        <button onClick={investigate} disabled={running || !ioc.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-lg px-4 py-2 flex items-center gap-2 text-sm">
          {running ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          Investigate
        </button>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-3 gap-4">
        {agents.map(a => (
          <div key={a.id}
            className={cn('rounded-xl border p-4 transition-all',
              a.status === 'active' ? 'border-blue-500 bg-blue-950' :
              a.status === 'done'   ? 'border-green-600 bg-green-950' :
                                      'border-gray-700 bg-gray-800')}>
            <div className="flex items-center gap-2 mb-2">
              {a.status === 'idle'   && <Circle size={14} className="text-gray-500" />}
              {a.status === 'active' && <Loader2 size={14} className="animate-spin text-blue-400" />}
              {a.status === 'done'   && <CheckCircle2 size={14} className="text-green-400" />}
              <span className="font-medium text-sm">{a.label}</span>
            </div>
            {a.lastChunk && (
              <p className="text-xs text-gray-400 line-clamp-3">{a.lastChunk.slice(-200)}</p>
            )}
          </div>
        ))}
      </div>

      {/* Report */}
      {reportChunks.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-6">
          <ReportViewer reportChunks={reportChunks} isStreaming={isStreaming} />
        </div>
      )}
    </div>
  )
}
