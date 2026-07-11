import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, FileDown } from 'lucide-react'
import { cn } from '../lib/cn'

interface RagasScores {
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number | null
  overall: number
}

interface Props {
  reportChunks: string[]
  isStreaming: boolean
  ragasScores?: RagasScores
}

export default function ReportViewer({ reportChunks, isStreaming, ragasScores }: Props) {
  const content = reportChunks.join('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (isStreaming) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [reportChunks, isStreaming])

  const copyMd = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="relative">
      {/* Action bar */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
        <p className="text-xs text-slate-500 uppercase tracking-wider">
          Investigation report {isStreaming && <span className="text-accent normal-case tracking-normal">· streaming…</span>}
        </p>
        <div className="flex gap-2">
          <button onClick={copyMd} className="btn-secondary flex items-center gap-1.5 text-xs px-2.5 py-1.5">
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy Markdown'}
          </button>
          <button onClick={() => window.print()} className="btn-secondary flex items-center gap-1.5 text-xs px-2.5 py-1.5">
            <FileDown size={12} /> Export PDF
          </button>
        </div>
      </div>

      {/* Markdown report */}
      <div className={cn(
        'prose prose-invert prose-sm max-w-none prose-headings:text-slate-100 prose-p:leading-relaxed',
        'prose-pre:bg-surface-950 prose-pre:border prose-pre:border-line prose-a:text-accent',
        isStreaming && 'blink-cursor')}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
      <div ref={bottomRef} />

      {/* RAGAs scores */}
      {ragasScores && !isStreaming && (
        <div className="mt-6 p-4 bg-surface-900 border border-line rounded-xl">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Response quality (RAGAs)</p>
          {[
            { label: 'Faithfulness', value: ragasScores.faithfulness },
            { label: 'Relevancy', value: ragasScores.answer_relevancy },
            { label: 'Context Precision', value: ragasScores.context_precision },
            ...(ragasScores.context_recall !== null
              ? [{ label: 'Context Recall', value: ragasScores.context_recall }]
              : []),
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-3 mb-2">
              <span className="text-xs text-slate-400 w-36">{label}</span>
              <div className="flex-1 h-2 bg-surface-600 rounded-full overflow-hidden">
                <div className={cn('h-full rounded-full',
                  value >= 0.8 ? 'bg-emerald-400' : value >= 0.5 ? 'bg-yellow-400' : 'bg-red-500')}
                  style={{ width: `${value * 100}%` }} />
              </div>
              <span className="text-xs text-slate-200 font-mono w-10 text-right">{(value * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
