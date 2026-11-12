import { useQuery } from '@tanstack/react-query'
import { getRuntimeMetrics } from '../lib/api'

const fmt = (n: number) => n.toLocaleString()

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-xl font-semibold text-slate-100 font-mono mt-1">{value}</p>
      {hint && <p className="text-[11px] text-slate-500 mt-1">{hint}</p>}
    </div>
  )
}

export default function RuntimeMetrics() {
  const { data, isError } = useQuery({ queryKey: ['runtime-metrics'], queryFn: getRuntimeMetrics, refetchInterval: 10000 })
  if (isError) return <p className="card p-4 text-sm text-slate-400">Runtime metrics are unavailable.</p>
  if (!data) return <p className="card p-4 text-sm text-slate-400">Loading…</p>

  const routes = Object.entries(data.routes).filter(([name]) => name.includes('/api/v1/') && !name.endsWith('/metrics'))
  const { llm, counters } = data
  const cost = llm.estimated_cost_usd === null ? 'not priced' : '$' + llm.estimated_cost_usd.toFixed(4)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="LLM calls" value={fmt(llm.calls)} hint={'p50 ' + fmt(llm.p50_ms) + ' ms · p95 ' + fmt(llm.p95_ms) + ' ms'} />
        <Stat label="Tokens in / out" value={fmt(llm.tokens_in) + ' / ' + fmt(llm.tokens_out)} hint={'Estimated cost: ' + cost} />
        <Stat label="Injection guard" value={fmt(counters.guard_blocked ?? 0) + ' blocked'} hint={fmt(counters.guard_allowed ?? 0) + ' allowed'} />
        <Stat label="Abstentions" value={fmt(counters.rag_abstained ?? 0)} hint="Questions with nothing relevant retrieved" />
      </div>
      {routes.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500 border-b border-line">
                <th className="px-4 py-2 font-medium">Route</th>
                <th className="px-4 py-2 font-medium text-right">Requests</th>
                <th className="px-4 py-2 font-medium text-right">5xx</th>
                <th className="px-4 py-2 font-medium text-right">p50 ms</th>
                <th className="px-4 py-2 font-medium text-right">p95 ms</th>
              </tr>
            </thead>
            <tbody>
              {routes.map(([name, r]) => (
                <tr key={name} className="border-b border-line/50 last:border-0 text-slate-300">
                  <td className="px-4 py-2 font-mono">{name}</td>
                  <td className="px-4 py-2 text-right font-mono">{fmt(r.requests)}</td>
                  <td className="px-4 py-2 text-right font-mono">{fmt(r.errors_5xx)}</td>
                  <td className="px-4 py-2 text-right font-mono">{fmt(r.p50_ms)}</td>
                  <td className="px-4 py-2 text-right font-mono">{fmt(r.p95_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
