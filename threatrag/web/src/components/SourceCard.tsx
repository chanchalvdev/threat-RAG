import { useState } from 'react'
import { Copy, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '../lib/cn'
import type { SourceDoc } from '../lib/api'

const DOC_TYPE_COLORS: Record<string, string> = {
  mitre_attack: 'bg-purple-900 text-purple-300',
  owasp_llm:    'bg-orange-900 text-orange-300',
  cve:          'bg-red-900    text-red-300',
  custom:       'bg-blue-900   text-blue-300',
}

interface Props {
  source: SourceDoc
  index: number
  defaultExpanded?: boolean
}

export default function SourceCard({ source, index, defaultExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [copied, setCopied] = useState(false)
  const color = DOC_TYPE_COLORS[source.doc_type] ?? DOC_TYPE_COLORS.custom
  const pct = Math.round(source.score * 100)

  const copy = () => {
    navigator.clipboard.writeText(source.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 text-sm overflow-hidden">
      {/* Header */}
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-750 text-left">
        <span className="text-gray-400 font-mono text-xs">[{index}]</span>
        <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium shrink-0', color)}>
          {source.doc_type.replace('_', ' ')}
        </span>
        <span className="text-gray-300 truncate flex-1">{source.source}</span>
        <span className="text-gray-500 text-xs shrink-0">{pct}%</span>
        {/* Relevance bar */}
        <div className="w-12 h-1.5 bg-gray-700 rounded-full shrink-0">
          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
        </div>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-gray-700">
          <div className="prose prose-sm prose-invert max-w-none mt-2 text-gray-300 font-mono text-xs leading-relaxed whitespace-pre-wrap">
            {source.text}
          </div>
          <button onClick={copy}
            className="mt-2 flex items-center gap-1 text-xs text-gray-400 hover:text-gray-100">
            <Copy size={12} />
            {copied ? 'Copied!' : 'Copy text'}
          </button>
        </div>
      )}
    </div>
  )
}
