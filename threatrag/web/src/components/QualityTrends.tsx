import { LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useTokens } from '../lib/theme'
import type { EvaluationRecord } from '../lib/api'

const METRICS = [
  { key: 'faithfulness',      label: 'Faithfulness',      tone: 'cobalt' },
  { key: 'answer_relevancy',  label: 'Answer relevancy',  tone: 'ochre' },
  { key: 'context_precision', label: 'Context precision', tone: 'green' },
  { key: 'context_recall',    label: 'Context recall',    tone: 'verm' },
] as const

type Row = EvaluationRecord & { t: number }

/** Four small multiples on one scale, target (0.8) and floor (0.5) ruled across each. */
export default function QualityTrends({ rows, loading }: { rows: Row[]; loading: boolean }) {
  const tk = useTokens()
  if (rows.length === 0) {
    return (
      <p className="card-quiet p-5 text-sm text-ink-2">
        {loading ? 'Loading evaluation history…' : 'No evaluations recorded yet. Score one below and the trend starts here.'}
      </p>
    )
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
      {METRICS.map(m => {
        const latest = [...rows].reverse().find(r => typeof r[m.key] === 'number')?.[m.key] as number | undefined
        const below = latest !== undefined && latest < 0.5
        return (
          <figure key={m.key} className="card-quiet mt-[13px] px-4 pt-3 pb-2">
            <figcaption className="flex items-baseline justify-between mb-1">
              <span className="text-sm font-semibold text-ink">{m.label}</span>
              <span className={`font-mono text-sm font-bold ${below ? 'text-verm' : 'text-ink'}`}>
                {latest === undefined ? 'n/a' : latest.toFixed(2)}
              </span>
            </figcaption>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={rows} margin={{ top: 6, right: 6, left: -24, bottom: 0 }}>
                <CartesianGrid stroke={tk.rule} strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: tk.ink3, fontFamily: 'Courier Prime' }} stroke={tk.rule} tickLine={false} />
                <YAxis domain={[0, 1]} ticks={[0, 0.5, 0.8, 1]} tick={{ fontSize: 10, fill: tk.ink3, fontFamily: 'Courier Prime' }} stroke={tk.rule} tickLine={false} />
                <Tooltip cursor={{ stroke: tk.ink3, strokeDasharray: '2 3' }}
                  contentStyle={{ background: tk.card, border: `1px solid ${tk.rule}`, borderRadius: 0, fontSize: 12, color: tk.ink }}
                  formatter={(v: number) => v?.toFixed(3)} labelFormatter={l => `Evaluation ${l}`} />
                <ReferenceLine y={0.8} stroke={tk.green} strokeDasharray="4 4" strokeOpacity={0.7} />
                <ReferenceLine y={0.5} stroke={tk.ochre} strokeDasharray="4 4" strokeOpacity={0.7} />
                <Line type="linear" dataKey={m.key} stroke={tk[m.tone]} strokeWidth={2} dot={rows.length < 4 ? { r: 3, fill: tk[m.tone] } : false}
                  activeDot={{ r: 4 }} connectNulls isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </figure>
        )
      })}
    </div>
  )
}
