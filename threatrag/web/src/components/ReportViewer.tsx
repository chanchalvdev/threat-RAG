import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, FileDown } from 'lucide-react'

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

  useEffect(() => {
    if (isStreaming) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [reportChunks, isStreaming])

  const copyMd = () => navigator.clipboard.writeText(content)
  const exportPDF = () => window.print()

  return (
    <div className="relative">
      {/* Action bar */}
      <div className="sticky top-0 right-0 flex justify-end gap-2 pb-2">
        <button onClick={copyMd} className="flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded">
          <Copy size={12} /> Copy Markdown
        </button>
        <button onClick={exportPDF} className="flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded">
          <FileDown size={12} /> Export PDF
        </button>
      </div>

      {/* Markdown report */}
      <div className="prose prose-invert prose-sm max-w-none text-gray-200">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
      <div ref={bottomRef} />

      {/* RAGAs scores */}
      {ragasScores && !isStreaming && (
        <div className="mt-6 p-4 bg-gray-800 rounded-xl">
          <p className="text-xs font-medium text-gray-400 mb-3">Response Quality (RAGAs)</p>
          {[
            { label: 'Faithfulness', value: ragasScores.faithfulness },
            { label: 'Relevancy', value: ragasScores.answer_relevancy },
            { label: 'Context Precision', value: ragasScores.context_precision },
            ...(ragasScores.context_recall !== null
              ? [{ label: 'Context Recall', value: ragasScores.context_recall! }]
              : []),
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-3 mb-2">
              <span className="text-xs text-gray-400 w-36">{label}</span>
              <div className="flex-1 h-2 bg-gray-700 rounded-full">
                <div className={`h-full rounded-full ${value >= 0.8 ? 'bg-green-500' : value >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${value * 100}%` }} />
              </div>
              <span className="text-xs text-gray-300 w-10 text-right">{(value * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
