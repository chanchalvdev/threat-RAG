import type { IngestStats } from '../lib/api'
import Ticker from './Ticker'
import Holes from './Holes'

const NAMES: Record<string, { label: string; ink: string }> = {
  mitre_attack: { label: 'MITRE ATT&CK', ink: 'text-cobalt' },
  owasp_llm:    { label: 'OWASP LLM Top 10', ink: 'text-ochre' },
  cve:          { label: 'CVE', ink: 'text-verm' },
  custom:       { label: 'Custom PDFs', ink: 'text-green' },
}

/** Vector counts per source as a ruled register: columns stay put, numbers tick in place. */
export default function IndexStats({ stats }: { stats: IngestStats | undefined }) {
  if (!stats) {
    return (
      <div className="card mt-[13px] p-6 space-y-3" aria-busy="true" aria-label="Loading index statistics">
        <div className="h-10 w-48 bg-card-2" /><div className="h-3 w-64 bg-card-2" /><div className="h-24 bg-card-2" />
      </div>
    )
  }
  const rows = Object.entries(stats.doc_type_counts).sort((a, b) => b[1] - a[1])
  const total = Math.max(1, stats.total_vectors)

  return (
    <div className="card mt-[13px] px-6 pt-5 pb-6">
      <span aria-hidden className="tab bg-green" />
      <p className="text-sm text-ink-2">Collection <span className="font-mono text-ink">{stats.collection}</span></p>

      {rows.length === 0 ? (
        <p className="mt-6 pt-4 border-t border-rule text-sm text-ink-2">
          The index is empty. Load MITRE ATT&amp;CK and the OWASP LLM Top 10 to give answers something to cite.
        </p>
      ) : (
        <table className="w-full mt-4 text-sm">
          <caption className="sr-only">Passages by source</caption>
          <thead>
            <tr className="border-b border-rule-strong text-left">
              <th scope="col" className="label py-2 font-bold">Source</th>
              <th scope="col" className="label py-2 font-bold">Share</th>
              <th scope="col" className="label py-2 font-bold text-right">Passages</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, v]) => {
              const meta = NAMES[k] ?? { label: k.replace(/_/g, ' '), ink: 'text-ink-2' }
              const share = v / total
              return (
                <tr key={k} className="border-b border-rule last:border-0">
                  <td className="py-2.5 pr-3 text-ink">{meta.label}</td>
                  <td className="py-2.5 pr-3">
                    <span className="flex items-center gap-2 text-xs text-ink-2">
                      <Holes filled={Math.max(1, Math.round(share * 5))} className={meta.ink} label={`${Math.round(share * 100)}% of the index`} />
                      {Math.round(share * 100)}%
                    </span>
                  </td>
                  <td className="py-2.5 text-right font-mono text-ink"><Ticker value={v.toLocaleString()} /></td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-rule-strong">
              <th scope="row" className="py-3 text-left text-[15px] font-bold text-ink" colSpan={2}>Passages filed</th>
              <td className="py-3 text-right font-mono font-bold text-2xl text-ink"><Ticker value={stats.total_vectors.toLocaleString()} /></td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  )
}
