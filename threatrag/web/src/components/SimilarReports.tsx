import { History } from 'lucide-react'
import type { ReportSummary } from '../lib/api'

interface Props {
  title: string
  reports: ReportSummary[]
}

export default function SimilarReports({ title, reports }: Props) {
  if (reports.length === 0) return null
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
        <History size={13} /> {title}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {reports.map(r => (
          <div key={r.id} className="card p-3 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-slate-100 truncate">{r.ioc}</span>
              <span className="text-[10px] uppercase text-slate-500">{r.ioc_type}</span>
              {r.similarity != null && (
                <span className="ml-auto text-[11px] font-mono text-accent">{(r.similarity * 100).toFixed(0)}%</span>
              )}
            </div>
            <p className="text-[11px] text-slate-500">{new Date(r.created_at).toLocaleString()}</p>
            <p className="text-xs text-slate-400 line-clamp-3">{r.summary.replace(/[#*|]/g, '').trim()}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
