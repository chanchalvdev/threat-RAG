import { useEffect, useRef, useState } from 'react'
import { Copy, Check, ChevronDown } from 'lucide-react'
import { cn } from '../lib/cn'
import { docInk, useXref } from '../lib/xref'
import type { SourceDoc } from '../lib/api'
import Holes, { magnitude } from './Holes'

interface Props {
  source: SourceDoc
  index: number
  defaultExpanded?: boolean
}

/** One retrieved passage, filed as an index card: S-n serial, coloured tab, typed ID, relevance holes. */
export default function SourceCard({ source, index, defaultExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [copied, setCopied] = useState(false)
  const { active, setActive, opened } = useXref()
  const ref = useRef<HTMLDivElement>(null)
  const pct = Math.round(source.score * 100)
  const lit = active === index
  const ink = docInk(source.doc_type)

  useEffect(() => {
    if (opened?.n !== index) return
    setExpanded(true)
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [opened, index])

  const copy = () => {
    navigator.clipboard.writeText(source.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div ref={ref} onMouseEnter={() => setActive(index)} onMouseLeave={() => setActive(null)}
      className={cn('card-quiet mt-[13px] text-sm transition-[transform,box-shadow] duration-200 ease-expo',
        lit && '-translate-y-0.5 shadow-[0_6px_14px_-6px_rgb(0_0_0/0.35)] ring-2 ring-ink/60 ring-offset-2 ring-offset-ground')}>
      <span aria-hidden className={cn('tab transition-[height,top] duration-200 ease-expo', ink.split(' ')[0], lit ? '-top-[15px] h-[14px]' : '-top-[11px]')} />
      <button type="button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}
        className="w-full grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 px-3.5 py-3 text-left hover:bg-card-2 transition-colors">
        <span className="font-mono text-xs font-bold text-ink-2">S-{index}</span>
        <span className="flex items-center gap-2 min-w-0 flex-wrap">
          {source.ref_id && <span className="font-mono font-bold text-ink shrink-0">{source.ref_id}</span>}
          <span className="text-ink-2 truncate min-w-0">{source.source}</span>
        </span>
        <ChevronDown size={15} strokeWidth={1.75} className={cn('text-ink-3 transition-transform duration-200', expanded && 'rotate-180')} />
        <span />
        <span className="flex items-center gap-3 text-xs text-ink-3">
          <span className="label">{source.doc_type.replace('_', ' ')}</span>
          {source.exact ? (
            <span title="Retrieved because the question names this ID" className="font-semibold text-green">exact ID match</span>
          ) : (
            <span className="flex items-center gap-2" title={`Cosine similarity ${pct}%`}>
              <Holes filled={magnitude(source.score)} className="text-ink-2" />
              <span className="font-mono">sim {pct}%</span>
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="px-3.5 pb-3.5 border-t border-rule animate-file-in">
          <p className="mt-3 text-ink-2 font-mono text-xs leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">{source.text}</p>
          <button type="button" onClick={copy} className="btn-text text-xs mt-2.5">
            {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy passage'}
          </button>
        </div>
      )}
    </div>
  )
}
