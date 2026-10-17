import { Fragment, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Loader2, CheckCircle2, Circle, ArrowRight, AlertTriangle, FlaskConical, Gavel, FileText, RotateCcw } from 'lucide-react'
import { cn } from '../lib/cn'
import { listReports } from '../lib/api'
import { useInvestigation, type IOCType, type NodeId } from '../lib/useInvestigation'
import ReportViewer from '../components/ReportViewer'
import SimilarReports from '../components/SimilarReports'

const AGENTS: { id: NodeId; label: string; role: string; Icon: typeof FlaskConical }[] = [
  { id: 'researcher', label: 'Researcher', role: 'Gathers intel from KB, NVD & web', Icon: FlaskConical },
  { id: 'critic',     label: 'Critic',     role: 'Challenges findings & fills gaps',  Icon: Gavel },
  { id: 'reporter',   label: 'Reporter',   role: 'Writes the final assessment',       Icon: FileText },
]

export default function Investigate() {
  const [ioc, setIoc] = useState('')
  const [iocType, setIocType] = useState<IOCType>('cve')
  const { nodes, iteration, reportChunks, running, error, result, start } = useInvestigation()
  const recent = useQuery({ queryKey: ['reports'], queryFn: () => listReports(6), retry: false })

  const { refetch } = recent
  useEffect(() => { if (result) refetch() }, [result, refetch])

  const investigate = () => { if (ioc.trim() && !running) start(ioc.trim(), iocType) }

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
          placeholder="CVE-2021-44228, T1055, 185.220.101.1…"
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
        {AGENTS.map((a, i) => {
          const n = nodes[a.id]
          return (
            <Fragment key={a.id}>
              {i > 0 && (
                <div className="hidden md:flex items-center shrink-0">
                  <ArrowRight size={16} className={cn(n.status !== 'idle' ? 'text-accent' : 'text-slate-600')} />
                </div>
              )}
              <div className={cn('flex-1 min-w-0 card p-4 transition-all',
                n.status === 'active' && 'border-accent-dim bg-accent-faint/15 shadow-glow',
                n.status === 'done' && 'border-emerald-500/40')}>
                <div className="flex items-center gap-2 mb-1">
                  <a.Icon size={15} className={cn(
                    n.status === 'active' ? 'text-accent' : n.status === 'done' ? 'text-emerald-400' : 'text-slate-500')} />
                  <span className="font-medium text-sm text-slate-100">{a.label}</span>
                  {a.id === 'researcher' && iteration > 1 && (
                    <span className="flex items-center gap-1 text-[10px] text-amber-400"><RotateCcw size={10} /> pass {iteration}</span>
                  )}
                  <span className="ml-auto">
                    {n.status === 'idle'   && <Circle size={13} className="text-slate-600" />}
                    {n.status === 'active' && <Loader2 size={13} className="animate-spin text-accent" />}
                    {n.status === 'done'   && <CheckCircle2 size={13} className="text-emerald-400" />}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mb-2">{a.role}</p>
                {n.detail && <p className="text-xs text-slate-400 line-clamp-3 font-mono break-all">{n.detail.slice(-200)}</p>}
              </div>
            </Fragment>
          )
        })}
      </div>

      {/* Report */}
      {reportChunks.length > 0 && (
        <div className="card p-6 animate-slide-in">
          <ReportViewer reportChunks={reportChunks} isStreaming={running} />
          {result && (
            <p className="mt-4 text-[11px] text-slate-500 font-mono">
              {result.report_id ? `Saved · ${result.report_id}` : 'Not saved (report storage unavailable)'}
              {` · ${result.iterations} research pass${result.iterations > 1 ? 'es' : ''} · ${result.sources.length} KB sources`}
            </p>
          )}
        </div>
      )}

      <SimilarReports title="Similar past investigations" reports={result?.similar ?? []} />
      {!running && !result && <SimilarReports title="Recent investigations" reports={recent.data ?? []} />}
    </div>
  )
}
