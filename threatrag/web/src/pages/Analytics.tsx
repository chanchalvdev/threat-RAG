import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import axios from 'axios'

const METRICS = [
  { key: 'faithfulness',       label: 'Faithfulness',        color: '#3b82f6' },
  { key: 'answer_relevancy',   label: 'Answer Relevancy',    color: '#a855f7' },
  { key: 'context_precision',  label: 'Context Precision',   color: '#22c55e' },
  { key: 'context_recall',     label: 'Context Recall',      color: '#f97316' },
]

interface EvalRequest {
  question: string
  answer: string
  contexts: string
  ground_truth?: string
}

export default function Analytics() {
  const [evalForm, setEvalForm] = useState<EvalRequest>({ question: '', answer: '', contexts: '' })
  const [evalResult, setEvalResult] = useState<Record<string, number> | null>(null)
  const [evaluating, setEvaluating] = useState(false)

  const runEval = async () => {
    setEvaluating(true)
    try {
      const r = await axios.post('/api/v1/evaluate', {
        question: evalForm.question,
        answer: evalForm.answer,
        contexts: evalForm.contexts.split('\n').filter(Boolean),
        ground_truth: evalForm.ground_truth || undefined,
      })
      setEvalResult(r.data)
    } catch {}
    setEvaluating(false)
  }

  const mockData = Array.from({ length: 10 }, (_, i) => ({
    t: i + 1,
    faithfulness: 0.7 + Math.random() * 0.25,
    answer_relevancy: 0.65 + Math.random() * 0.3,
    context_precision: 0.6 + Math.random() * 0.35,
    context_recall: 0.55 + Math.random() * 0.4,
  }))

  return (
    <div className="p-6 max-w-5xl space-y-8">
      <h2 className="text-lg font-semibold">RAGAs Quality Metrics</h2>

      <div className="grid grid-cols-2 gap-4">
        {METRICS.map(m => (
          <div key={m.key} className="bg-gray-800 rounded-xl p-4">
            <p className="text-sm font-medium text-gray-300 mb-3">{m.label}</p>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={mockData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="t" tick={{ fontSize: 10 }} stroke="#6b7280" />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} stroke="#6b7280" />
                <Tooltip contentStyle={{ background: '#1f2937', border: 'none', fontSize: 11 }} />
                <ReferenceLine y={0.8} stroke="#22c55e" strokeDasharray="4 4" />
                <ReferenceLine y={0.5} stroke="#eab308" strokeDasharray="4 4" />
                <Line type="monotone" dataKey={m.key} stroke={m.color} dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>

      {/* Eval form */}
      <div className="bg-gray-800 rounded-xl p-6 space-y-3">
        <h3 className="font-medium text-sm">Run Evaluation</h3>
        {(['question', 'answer', 'contexts', 'ground_truth'] as const).map(field => (
          <div key={field}>
            <label className="text-xs text-gray-400 capitalize">{field.replace('_', ' ')}</label>
            <textarea rows={field === 'contexts' ? 3 : 2}
              value={evalForm[field] ?? ''}
              onChange={e => setEvalForm(p => ({ ...p, [field]: e.target.value }))}
              placeholder={field === 'contexts' ? 'One context per line' : ''}
              className="w-full mt-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm resize-none" />
          </div>
        ))}
        <button onClick={runEval} disabled={evaluating}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-sm px-4 py-2 rounded-lg">
          {evaluating ? 'Evaluating...' : 'Evaluate'}
        </button>
        {evalResult && (
          <div className="bg-gray-700 rounded-lg p-3 text-xs font-mono">
            {Object.entries(evalResult).map(([k, v]) => (
              <p key={k}>{k}: <span className="text-blue-300">{typeof v === 'number' ? v.toFixed(3) : v}</span></p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
