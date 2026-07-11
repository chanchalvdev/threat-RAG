import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '../lib/cn'
import type { SourceDoc } from '../lib/api'

const DOC_TYPE_STYLE: Record<string, string> = {
  mitre_attack: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  owasp_llm:    'bg-orange-500/15 text-orange-300 border-orange-500/30',
  cve:          'bg-red-500/15    text-red-300    border-red-500/30',
  custom:       'bg-accent-faint/40 text-accent-bright border-accent-dim/40',
}

interface Props {
  source: SourceDoc
  index: number
  defaultExpanded?: boolean
}

export default function SourceCard({ source, index, defaultExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [copied, setCopied] = useState(false)
  const style = DOC_TYPE_STYLE[source.doc_type] ?? DOC_TYPE_STYLE.custom
  const pct = Math.round(source.score * 100)

  const copy = () => {
    navigator.clipboard.writeText(source.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="card text-sm overflow-hidden">
      {/* Header */}
      <button onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-surface-700 text-left transition-colors">
        <span className="text-slate-500 font-mono text-xs">[{index}]</span>
        <span className={cn('px-1.5 py-0.5 rounded border text-[11px] font-medium shrink-0', style)}>
          {source.doc_type.replace('_', ' ')}
        </span>
        <span className="text-slate-300 truncate flex-1">{source.source}</span>
        <span className="text-slate-500 text-xs font-mono shrink-0">{pct}%</span>
        <div className="w-12 h-1.5 bg-surface-600 rounded-full shrink-0" title={`Relevance ${pct}%`}>
          <div className="h-full bg-accent rounded-full" style={{ width: `${pct}%` }} />
        </div>
        {expanded ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-line animate-fade-in">
          <div className="mt-2.5 text-slate-300 font-mono text-xs leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
            {source.text}
          </div>
          <button onClick={copy}
            className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-200 transition-colors">
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy text'}
          </button>
        </div>
      )}
    </div>
  )
}
