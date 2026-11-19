import { useQuery } from '@tanstack/react-query'
import { getRuntimeMetrics } from '../lib/api'
import Ticker from './Ticker'

const fmt = (n: number) => n.toLocaleString()

/** One ledger line: what is counted on the left, the figure in a fixed right-hand column. */
function Stat({ label, value, unit, hint, tone }: { label: string; value: string; unit?: string; hint?: string; tone?: string }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-6 gap-y-1 px-5 py-3.5 border-b border-rule">
      <dt className="text-[15px] font-semibold text-ink">{label}
        {hint && <span className="block text-xs font-normal text-ink-2 mt-0.5">{hint}</span>}
      </dt>
      <dd className={`font-mono font-bold text-xl sm:text-right tabular-nums ${tone ?? 'text-ink'}`}>
        <Ticker value={value} />{unit && <span className="font-sans">{' ' + unit}</span>}
      </dd>
    </div>
  )
}

export default function RuntimeMetrics() {
  const { data, isError } = useQuery({ queryKey: ['runtime-metrics'], queryFn: getRuntimeMetrics, refetchInterval: 10000 })
  if (isError) return <p className="card-quiet p-4 text-sm text-ink-2">Runtime metrics are unavailable: the API did not answer /metrics.</p>
  if (!data) return <div className="card h-28 animate-pulse" aria-busy="true" aria-label="Loading runtime metrics" />

  const routes = Object.entries(data.routes).filter(([name]) => name.includes('/api/v1/') && !name.endsWith('/metrics'))
  const { llm, counters } = data
  const cost = llm.estimated_cost_usd === null ? 'not priced' : '$' + llm.estimated_cost_usd.toFixed(4)
  const blocked = counters.guard_blocked ?? 0

  return (
    <div className="space-y-6">
      <dl className="card grid grid-cols-1 lg:grid-cols-2 lg:gap-x-0 [&>div:nth-child(odd)]:lg:border-r">
        <Stat label="LLM calls" value={fmt(llm.calls)} hint={'p50 ' + fmt(llm.p50_ms) + ' ms · p95 ' + fmt(llm.p95_ms) + ' ms'} />
        <Stat label="Tokens in / out" value={fmt(llm.tokens_in) + ' / ' + fmt(llm.tokens_out)} hint={'Estimated cost: ' + cost} />
        <Stat label="Injection guard" value={fmt(blocked)} unit="blocked" hint={fmt(counters.guard_allowed ?? 0) + ' allowed'} tone={blocked > 0 ? 'text-verm' : undefined} />
        <Stat label="Abstentions" value={fmt(counters.rag_abstained ?? 0)} hint="Nothing relevant retrieved" />
      </dl>
      {routes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Latency and errors per API route</caption>
            <thead>
              <tr className="border-b border-rule-strong text-left">
                <th scope="col" className="label py-2 pr-4 font-bold">Route</th>
                <th scope="col" className="label py-2 px-3 font-bold text-right">Requests</th>
                <th scope="col" className="hidden sm:table-cell label py-2 px-3 font-bold text-right">5xx</th>
                <th scope="col" className="hidden sm:table-cell label py-2 px-3 font-bold text-right">p50 ms</th>
                <th scope="col" className="label py-2 pl-3 font-bold text-right">p95 ms</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {routes.map(([name, r]) => (
                <tr key={name} className="border-b border-rule last:border-0 hover:bg-card/60">
                  <td className="py-2.5 pr-4 text-ink sm:whitespace-nowrap">
                    {name.split('/').map((part, k) => <span key={k}>{k > 0 && <>/<wbr /></>}{part}</span>)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-ink-2"><Ticker value={fmt(r.requests)} /></td>
                  <td className={`hidden sm:table-cell py-2.5 px-3 text-right ${r.errors_5xx > 0 ? 'text-verm font-bold' : 'text-ink-2'}`}>{fmt(r.errors_5xx)}</td>
                  <td className="hidden sm:table-cell py-2.5 px-3 text-right text-ink-2">{fmt(r.p50_ms)}</td>
                  <td className="py-2.5 pl-3 text-right text-ink-2">{fmt(r.p95_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
