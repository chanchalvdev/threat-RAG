import { useQuery } from '@tanstack/react-query'
import { cn } from '../lib/cn'
import { getFeedStatus, type FeedStep } from '../lib/feeds'

const n = (v: unknown) => (typeof v === 'number' ? v.toLocaleString() : String(v ?? '–'))

function describe(name: string, step: FeedStep): string {
  if (step.error) return step.error
  if (step.skipped) return String(step.skipped)
  if (name === 'mitre') return step.changed ? `re-indexed the release last changed ${step.latest_change}: ${n(step.chunks)} passages` : 'unchanged since the last run'
  if (name === 'baseline') return `hit@6 ${n(step['hit@6'])} before the first refresh`
  if (name === 'kev') return `${n(step.items)} actively exploited CVEs`
  if (name === 'taxii') return `${n(step.chunks)} new passages` + (step.dropped_instruction_like ? ` · ${n(step.dropped_instruction_like)} dropped as instruction-like` : '')
  if (name === 'eval') return `hit@6 ${n(step['hit@6'])}` + (step.previous != null ? ` (was ${n(step.previous)})` : '') + (step.regressed ? ' · regressed' : '')
  return JSON.stringify(step)
}

const LABELS: Record<string, string> = { baseline: 'Baseline', mitre: 'MITRE ATT&CK', kev: 'CISA KEV', taxii: 'TAXII', eval: 'Retrieval check' }

/** The scheduled refresh: when it last ran and what each feed did. */
export default function FeedStatus() {
  const { data } = useQuery({ queryKey: ['feed-status'], queryFn: getFeedStatus, retry: false })
  if (!data) return null
  if (!data.at) {
    return (
      <p className="text-sm text-ink-3 border-t border-rule pt-3">
        Feeds have not run. Start the daily refresh with <code className="font-mono text-ink-2">docker compose --profile feeds up -d scheduler</code>.
      </p>
    )
  }
  return (
    <div>
      <p className="text-sm text-ink-2">
        Last refresh <span className="font-mono text-ink">{new Date(data.at).toLocaleString()}</span>
        {data.regressed && <span className="text-verm font-semibold"> · retrieval got worse after the last ATT&amp;CK update</span>}
      </p>
      <dl className="mt-2 border-t border-rule-strong divide-y divide-rule">
        {Object.entries(data.steps).map(([name, step]) => (
          <div key={name} className="grid grid-cols-[9rem_1fr] gap-3 py-2 text-sm">
            <dt className="text-ink">{LABELS[name] ?? name}</dt>
            <dd className={cn(step.error || step.regressed ? 'text-verm' : 'text-ink-2')}>{describe(name, step)}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
