import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { downloadCandidates, getFeedbackSummary } from '../lib/feedback'

const share = (up: number, down: number) => (up + down ? Math.round((up / (up + down)) * 100) + '% helpful' : 'no votes yet')

/** Analyst votes, the latest complaints, and the down-voted questions as golden-set drafts. */
export default function FeedbackPanel() {
  const summary = useQuery({ queryKey: ['feedback-summary'], queryFn: getFeedbackSummary, retry: false })
  const [exportFailed, setExportFailed] = useState(false)
  const s = summary.data

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)] gap-8 items-start">
      <dl className="border-t border-rule-strong divide-y divide-rule">
        {(['answer', 'report'] as const).map(t => (
          <div key={t} className="grid grid-cols-[7rem_1fr_auto] items-baseline gap-3 py-2.5">
            <dt className="text-sm text-ink capitalize">{t}s</dt>
            <dd className="font-mono text-sm text-ink">{s ? `${s[t].up} up / ${s[t].down} down` : '–'}</dd>
            <dd className="text-xs text-ink-2">{s ? share(s[t].up, s[t].down) : ''}</dd>
          </div>
        ))}
        <div className="pt-3">
          <button type="button" className="btn-line text-xs"
            onClick={() => { setExportFailed(false); downloadCandidates().catch(() => setExportFailed(true)) }}>
            <Download size={13} /> Download review candidates
          </button>
          <p className="text-xs text-ink-3 mt-2 max-w-[48ch]">
            Down-voted questions in the golden-set format. Check each expectation before adding it to eval/golden.jsonl.
          </p>
          {exportFailed && <p role="alert" className="text-xs text-verm mt-1">Export failed: feedback storage is unavailable.</p>}
        </div>
      </dl>

      <div>
        <h3 className="label mb-1">Latest down-votes</h3>
        {!s?.recent_down.length ? (
          <p className="text-sm text-ink-3 border-t border-rule pt-3">No down-votes filed.</p>
        ) : (
          <ul className="border-t border-rule-strong divide-y divide-rule">
            {s.recent_down.map(r => (
              <li key={r.id} className="py-2.5 text-sm">
                <p className="text-ink"><span className="label mr-2">{r.target}</span>{r.question || r.target_id}</p>
                {r.note && <p className="text-ink-2 mt-0.5">“{r.note}”</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
