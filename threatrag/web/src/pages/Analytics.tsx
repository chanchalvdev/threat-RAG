import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { cn } from '../lib/cn'
import { getEvaluationHistory, runEvaluation } from '../lib/api'
import RuntimeMetrics from '../components/RuntimeMetrics'
import QualityTrends from '../components/QualityTrends'

const FIELDS = [
  { key: 'question',     label: 'Question',     rows: 2, placeholder: 'The question that was asked' },
  { key: 'answer',       label: 'Answer',       rows: 3, placeholder: 'The generated answer to evaluate' },
  { key: 'contexts',     label: 'Contexts',     rows: 4, placeholder: 'Retrieved passages, one per line' },
  { key: 'ground_truth', label: 'Ground truth (optional)', rows: 2, placeholder: 'A reference answer; enables context recall' },
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
      setError('Evaluation failed: the judge model did not return scores. Check that the backend and judge model are reachable.')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="px-4 md:px-8 pt-8 md:pt-10 pb-16 max-w-[90rem] mx-auto space-y-12">
      <header className="border-b border-rule-strong pb-4">
        <h1 className="display text-4xl md:text-5xl">Analytics</h1>
      </header>

      <section aria-labelledby="runtime-h" className="space-y-3">
        <div>
          <h2 id="runtime-h" className="display text-2xl [font-variation-settings:'wdth'_80]">Runtime</h2>
          <p className="text-sm text-ink-2 mt-1">This API process since its last restart · latency over the last 500 requests (time to first byte for streams)</p>
        </div>
        <RuntimeMetrics />
      </section>

      <section aria-labelledby="quality-h">
        <h2 id="quality-h" className="display text-2xl [font-variation-settings:'wdth'_80]">Answer quality</h2>
        <p className="text-sm text-ink-2 mt-1">
          LLM-judge scores over the last {trend.length} evaluation{trend.length === 1 ? '' : 's'} ·
          <span className="text-green font-semibold"> dashed green</span> is the 0.8 target,
          <span className="text-ochre font-semibold"> dashed ochre</span> the 0.5 floor
        </p>
        <QualityTrends rows={trend} loading={history.isLoading} />
      </section>

      <section aria-labelledby="eval-h" className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.8fr)] gap-8 items-start">
        <div className="card mt-[13px] p-5 md:p-6 space-y-4">
          <span aria-hidden className="tab bg-cobalt" />
          <div>
            <h2 id="eval-h" className="display text-2xl [font-variation-settings:'wdth'_80]">Score an answer</h2>
            <p className="text-sm text-ink-2 mt-1">Grade a question, answer and context set with the judge model.</p>
          </div>
          {FIELDS.map(({ key, label, rows, placeholder }) => (
            <div key={key}>
              <label htmlFor={`eval-${key}`} className="label">{label}</label>
              <textarea id={`eval-${key}`} rows={rows} value={form[key]} placeholder={placeholder}
                onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
                className={cn('field w-full mt-1.5 px-3 py-2 resize-y leading-relaxed', key === 'contexts' && 'font-mono text-xs')} />
            </div>
          ))}
          <button type="button" onClick={runEval} disabled={evaluating || !canRun} className="btn-act">
            {evaluating ? 'Scoring…' : 'Score answer'}
          </button>
          {error && (
            <p role="alert" className="flex items-start gap-2 text-sm text-verm font-medium">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" /> {error}
            </p>
          )}
        </div>

        <div aria-live="polite">
          <h3 className="label mb-1">Scores</h3>
          {!result ? (
            <p className="text-sm text-ink-3 border-t border-rule pt-3">Scores appear here and join the trend above.</p>
          ) : (
            <dl className="border-t border-rule-strong divide-y divide-rule animate-file-in">
              {Object.entries(result).filter((e): e is [string, number] => typeof e[1] === 'number').map(([k, v]) => (
                <div key={k} className="grid grid-cols-[10rem_1fr_3.5rem] items-center gap-3 py-2.5">
                  <dt className="text-sm text-ink capitalize">{k.replace(/_/g, ' ')}</dt>
                  <dd className="h-2.5 bg-card-2">
                    <span className={cn('block h-full transition-[width] duration-500 ease-expo',
                      v >= 0.8 ? 'bg-green' : v >= 0.5 ? 'bg-ochre-fill' : 'bg-verm')} style={{ width: `${Math.min(v, 1) * 100}%` }} />
                  </dd>
                  <dd className="font-mono text-sm text-ink text-right">{v.toFixed(3)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </section>
    </div>
  )
}
