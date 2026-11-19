import { useCallback, useState } from 'react'
import { Copy, Check, ChevronDown, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/cn'
import { CitedMarkdown, XrefProvider } from '../lib/xref'
import SourceCard from './SourceCard'
import Rate from './Rate'
import ToolCallTimeline, { type ToolCallEntry } from './ToolCallTimeline'
import type { SourceDoc } from '../lib/api'

interface Props {
  role: 'user' | 'assistant'
  serial: number
  content: string
  sources?: SourceDoc[]
  thoughts?: string[]
  toolCalls?: ToolCallEntry[]
  isStreaming?: boolean
  error?: string
  /** Where a vote on this answer is filed: '<session>:<turn>' and the question it answered. */
  feedback?: { targetId: string; question: string }
}

const pad = (n: number) => String(n)

export default function ChatMessage({ role, serial, content, sources = [], thoughts, toolCalls = [], isStreaming, error, feedback }: Props) {
  const [showSources, setShowSources] = useState(false)
  const [copied, setCopied] = useState(false)
  const openSources = useCallback(() => setShowSources(true), [])

  if (role === 'user') {
    return (
      <div className="flex gap-4 items-baseline pt-8 pb-3">
        <span className="font-mono text-xs text-ink-3 w-10 shrink-0">Q-{pad(serial)}</span>
        <p className="display text-xl md:text-2xl text-ink [font-variation-settings:'wdth'_80] leading-tight">{content}</p>
      </div>
    )
  }

  const copy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <XrefProvider onOpen={openSources}>
      <div className="md:pl-14 space-y-4">
        {thoughts && thoughts.length > 0 && (
          <p className="text-xs text-ink-3 italic">{thoughts[thoughts.length - 1]}</p>
        )}
        <ToolCallTimeline calls={toolCalls} />

        <article className="card mt-[13px] px-5 py-4 group">
          <span aria-hidden className="tab bg-cobalt" />
          <div className="flex items-center gap-3 mb-2">
            <span className="font-mono text-xs font-bold text-ink-2">A-{pad(serial)}</span>
            {isStreaming && <span className="label text-cobalt">Filing answer</span>}
            {!isStreaming && !error && content && (
              <button type="button" onClick={copy} aria-label="Copy answer"
                className="btn-text text-xs ml-auto opacity-70 group-hover:opacity-100 focus-visible:opacity-100">
                {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}{copied ? 'Copied' : 'Copy'}
              </button>
            )}
          </div>
          {error ? (
            <p role="alert" className="flex items-start gap-2 text-verm text-sm font-medium">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" /> {error}
            </p>
          ) : isStreaming && !content ? (
            <span className="flex items-center gap-3 text-sm text-ink-3 py-1" aria-label="Thinking">
              <span className="relative h-[3px] w-16 overflow-hidden bg-rule"><span className="absolute inset-y-0 w-1/2 bg-cobalt animate-rule-run" /></span>
              Searching the index
            </span>
          ) : (
            <CitedMarkdown content={content} sources={sources} className={cn(isStreaming && '[&>*:last-child]:typing')} />
          )}
        </article>

        {feedback && !isStreaming && !error && content && (
          <Rate target="answer" targetId={feedback.targetId} question={feedback.question} answer={content} />
        )}

        {sources.length > 0 && (
          <div>
            <button type="button" onClick={() => setShowSources(!showSources)} aria-expanded={showSources}
              className="btn-text text-xs">
              <ChevronDown size={13} className={cn('transition-transform', showSources && 'rotate-180')} />
              {sources.length} cited source{sources.length > 1 ? 's' : ''}
            </button>
            {showSources && (
              <div className="grid gap-3 mt-1 animate-file-in">
                {sources.map((s, i) => <SourceCard key={i} source={s} index={i + 1} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </XrefProvider>
  )
}
