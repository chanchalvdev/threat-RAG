import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Loader2, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/cn'
import { getEvaluationHistory, runEvaluation } from '../lib/api'

const METRICS = [
  { key: 'faithfulness',      label: 'Faithfulness',      color: '#22D3EE' },
  { key: 'answer_relevancy',  label: 'Answer Relevancy',  color: '#a855f7' },
  { key: 'context_precision', label: 'Context Precision', color: '#22c55e' },
  { key: 'context_recall',    label: 'Context Recall',    color: '#f97316' },
]

const FIELDS = [
  { key: 'question',     label: 'Question',     rows: 2, placeholder: 'The question that was asked' },
  { key: 'answer',       label: 'Answer',       rows: 2, placeholder: 'The generated answer to evaluate' },
  { key: 'contexts',     label: 'Contexts',     rows: 3, placeholder: 'Retrieved context passages — one per line' },
  { key: 'ground_truth', label: 'Ground truth (optional)', rows: 2, placeholder: 'Reference answer, enables context recall' },
] as const

type FormKey = typeof FIELDS[number]['key']

export default function Analytics() {
  const [form, setForm] = useState<Record<FormKey, string>>({ question: '', answer: '', contexts: '', ground_truth: '' })
  const [result, setResult] = useState<Record<string, number | null> | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const history = useQuery({ queryKey: ['eval-history'], queryFn: () => getEvaluationHistory(50) })
  const trend = (history.data ?? []).map((e, i) => ({ ...e, t: i + 1 }))

  const canRun = form.question.trim() && form.answer.trim() && form.contexts.trim()

  const runEval = async () => {
    setEvaluating(true)
    setError(null)
    try {
      const scores = await runEvaluation({
        question: form.question,
        answer: form.answer,
        contexts: form.contexts.split('\n').filter(Boolean),
        ground_truth: form.ground_truth || undefined,
      })
      setResult(scores)
      history.refetch()
    } catch {
      setError('Evaluation failed — check that the backend and RAGAs pipeline are running.')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <section>
        <h2 className="text-base font-semibold text-slate-100 mb-1">Quality trends</h2>
        <p className="text-xs text-slate-500 mb-4">RAGAs metrics over the last {trend.length} evaluations · green line = target (0.8), yellow = floor (0.5)</p>
        {trend.length === 0 && (
          <p className="card p-4 text-sm text-slate-400 mb-4">
            {history.isLoading ? 'Loading…' : 'No evaluations recorded yet — run one below to start the trend.'}
          </p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {METRICS.map(m => (
            <div key={m.key} className="card p-4">
              <p className="text-sm font-medium text-slate-300 mb-3">{m.label}</p>
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#18233B" />
                  <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#697894' }} stroke="#22304F" />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#697894' }} stroke="#22304F" />
                  <Tooltip contentStyle={{ background: '#111A2C', border: '1px solid #1D2A45', borderRadius: 8, fontSize: 11 }} />
                  <ReferenceLine y={0.8} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.5} />
                  <ReferenceLine y={0.5} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.5} />
                  <Line type="monotone" dataKey={m.key} stroke={m.color} dot={trend.length < 3} strokeWidth={2} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      </section>

      {/* Eval form */}
      <section className="card p-6 space-y-4">
        <div>
          <h3 className="font-semibold text-sm text-slate-100">Run an evaluation</h3>
          <p className="text-xs text-slate-500 mt-0.5">Score a question / answer / context triple with RAGAs</p>
        </div>
        {FIELDS.map(({ key, label, rows, placeholder }) => (
          <div key={key}>
            <label htmlFor={`eval-${key}`} className="text-xs font-medium text-slate-400">{label}</label>
            <textarea id={`eval-${key}`} rows={rows} value={form[key]} placeholder={placeholder}
              onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
              className="input-base w-full mt-1.5 px-3 py-2 resize-none" />
          </div>
        ))}
        <button onClick={runEval} disabled={evaluating || !canRun}
          className="btn-primary text-sm px-5 py-2.5 flex items-center gap-2">
          {evaluating && <Loader2 size={14} className="animate-spin" />}
          {evaluating ? 'Evaluating…' : 'Evaluate'}
        </button>

        {error && (
          <p className="flex items-center gap-2 text-sm text-red-400">
            <AlertTriangle size={14} className="shrink-0" /> {error}
          </p>
        )}

        {result && (
          <div className="bg-surface-900 border border-line rounded-lg p-4 space-y-2.5 animate-slide-in">
            {Object.entries(result).filter((e): e is [string, number] => typeof e[1] === 'number').map(([k, v]) => (
              <div key={k} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-40 capitalize">{k.replace(/_/g, ' ')}</span>
                <div className="flex-1 h-2 bg-surface-600 rounded-full overflow-hidden">
                  <div className={cn('h-full rounded-full transition-all duration-500',
                    v >= 0.8 ? 'bg-emerald-400' : v >= 0.5 ? 'bg-yellow-400' : 'bg-red-500')}
                    style={{ width: `${Math.min(v, 1) * 100}%` }} />
                </div>
                <span className="text-xs text-slate-200 font-mono w-12 text-right">{v.toFixed(3)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
