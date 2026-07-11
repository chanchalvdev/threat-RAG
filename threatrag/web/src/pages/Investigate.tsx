import { Fragment, useState } from 'react'
import { Search, Loader2, CheckCircle2, Circle, ArrowRight, AlertTriangle, FlaskConical, Gavel, FileText } from 'lucide-react'
import { cn } from '../lib/cn'
import ReportViewer from '../components/ReportViewer'

type IOCType = 'ip' | 'hash' | 'domain' | 'cve' | 'technique'
type NodeStatus = 'idle' | 'active' | 'done'

interface AgentCard {
  id: string
  label: string
  role: string
  Icon: typeof FlaskConical
  status: NodeStatus
  lastChunk: string
}

const INITIAL_AGENTS: AgentCard[] = [
  { id: 'researcher', label: 'Researcher', role: 'Gathers intel from KB, NVD & web', Icon: FlaskConical, status: 'idle', lastChunk: '' },
  { id: 'critic',     label: 'Critic',     role: 'Challenges findings & fills gaps',  Icon: Gavel,        status: 'idle', lastChunk: '' },
  { id: 'reporter',   label: 'Reporter',   role: 'Writes the final assessment',       Icon: FileText,     status: 'idle', lastChunk: '' },
]

export default function Investigate() {
  const [ioc, setIoc] = useState('')
  const [iocType, setIocType] = useState<IOCType>('cve')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reportChunks, setReportChunks] = useState<string[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [agents, setAgents] = useState<AgentCard[]>(INITIAL_AGENTS)

  const setAgentStatus = (id: string, status: NodeStatus, lastChunk = '') =>
    setAgents(prev => prev.map(a => a.id === id ? { ...a, status, ...(lastChunk ? { lastChunk } : {}) } : a))

  const investigate = async () => {
    if (!ioc.trim() || running) return
    setRunning(true)
    setError(null)
    setReportChunks([])
    setIsStreaming(true)
    setAgents(INITIAL_AGENTS)

    try {
      const res = await fetch('/api/v1/investigate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ioc, ioc_type: iocType }),
      })
      if (!res.ok || !res.body) throw new Error(`Investigation failed (HTTP ${res.status})`)

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Investigation failed — is the backend running?')
      setIsStreaming(false)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* IOC input */}
      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <select value={iocType} onChange={e => setIocType(e.target.value as IOCType)}
          aria-label="IOC type" className="input-base px-3 py-2.5 sm:w-36">
          {(['cve', 'technique', 'ip', 'hash', 'domain'] as IOCType[]).map(t =>
            <option key={t} value={t}>{t.toUpperCase()}</option>
          )}
        </select>
        <input value={ioc} onChange={e => setIoc(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') investigate() }}
          placeholder="CVE-2021-44228, T1055, 185.220.x.x…"
          className="input-base flex-1 px-4 py-2.5 font-mono" />
        <button onClick={investigate} disabled={running || !ioc.trim()}
          className="btn-primary px-5 py-2.5 flex items-center justify-center gap-2 text-sm shadow-glow">
          {running ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          Investigate
        </button>
      </div>

      {error && (
        <p className="flex items-center gap-2 text-sm text-red-400 card border-red-500/30 p-3">
          <AlertTriangle size={15} className="shrink-0" /> {error}
        </p>
      )}

      {/* Agent pipeline */}
      <div className="flex flex-col md:flex-row items-stretch gap-2">
        {agents.map((a, i) => (
          <Fragment key={a.id}>
            {i > 0 && (
              <div className="hidden md:flex items-center shrink-0">
                <ArrowRight size={16} className={cn(a.status !== 'idle' ? 'text-accent' : 'text-slate-600')} />
              </div>
            )}
            <div className={cn('flex-1 card p-4 transition-all',
              a.status === 'active' && 'border-accent-dim bg-accent-faint/15 shadow-glow',
              a.status === 'done' && 'border-emerald-500/40')}>
              <div className="flex items-center gap-2 mb-1">
                <a.Icon size={15} className={cn(
                  a.status === 'active' ? 'text-accent' : a.status === 'done' ? 'text-emerald-400' : 'text-slate-500')} />
                <span className="font-medium text-sm text-slate-100">{a.label}</span>
                <span className="ml-auto">
                  {a.status === 'idle'   && <Circle size={13} className="text-slate-600" />}
                  {a.status === 'active' && <Loader2 size={13} className="animate-spin text-accent" />}
                  {a.status === 'done'   && <CheckCircle2 size={13} className="text-emerald-400" />}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mb-2">{a.role}</p>
              {a.lastChunk && (
                <p className="text-xs text-slate-400 line-clamp-3 font-mono">{a.lastChunk.slice(-200)}</p>
              )}
            </div>
          </Fragment>
        ))}
      </div>

      {/* Report */}
      {reportChunks.length > 0 && (
        <div className="card p-6 animate-slide-in">
          <ReportViewer reportChunks={reportChunks} isStreaming={isStreaming} />
        </div>
      )}
    </div>
  )
}
