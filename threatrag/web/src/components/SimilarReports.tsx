import { ArrowUpRight } from 'lucide-react'
import type { ReportSummary } from '../lib/api'
import { reportSerial } from './ReportViewer'
import Holes, { magnitude } from './Holes'

interface Props {
  title: string
  reports: ReportSummary[]
  onPick?: (r: ReportSummary) => void
}

const clean = (s: string) => s.replace(/[#*|`>_-]+/g, ' ').replace(/\s+/g, ' ').trim()

/** Past investigations as filed cards; picking one re-opens that indicator. */
export default function SimilarReports({ title, reports, onPick }: Props) {
  if (reports.length === 0) return null
  return (
    <section>
      <h2 className="label mb-1">{title}</h2>
      <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-x-4 gap-y-2">
        {reports.map(r => {
          const body = (<>
            <span aria-hidden className="tab -top-[11px] bg-rule-strong/60 w-10" />
            <span className="flex items-center gap-2">
              <span className="font-mono font-bold text-ink truncate">{r.ioc}</span>
              {onPick && <ArrowUpRight size={15} className="shrink-0 text-ink-3 group-hover:text-act transition-colors" />}
              <span className="serial ml-auto shrink-0">{reportSerial(r.id)}</span>
            </span>
            {r.similarity != null && (
              <span className="flex items-center gap-1.5 text-xs text-ink-2 mt-1">
                <Holes filled={magnitude(r.similarity)} className="text-ink-2" /> {(r.similarity * 100).toFixed(0)}% similar
              </span>
            )}
            <span className="block text-xs text-ink-2 line-clamp-2 mt-1.5">{clean(r.summary)}</span>
            <span className="block text-xs text-ink-3 mt-2">{new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</span>
          </>)
          return (
            <li key={r.id} className="card-quiet mt-[13px]">
              {onPick
                ? <button type="button" onClick={() => onPick(r)} title={`Investigate ${r.ioc} again`}
                    className="group block w-full text-left p-4 hover:bg-card-2 transition-colors">{body}</button>
                : <div className="p-4">{body}</div>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
