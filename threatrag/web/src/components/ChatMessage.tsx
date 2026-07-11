import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, ChevronDown, ChevronUp, Shield, User, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/cn'
import SourceCard from './SourceCard'
import type { SourceDoc } from '../lib/api'

interface Props {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDoc[]
  thoughts?: string[]
  isStreaming?: boolean
  error?: string
}

export default function ChatMessage({ role, content, sources, thoughts, isStreaming, error }: Props) {
  const [showSources, setShowSources] = useState(false)
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (role === 'user') {
    return (
      <div className="flex justify-end mb-5">
        <div className="flex items-start gap-2.5 max-w-xl">
          <div className="bg-accent-faint/60 border border-accent-dim/40 text-slate-100 rounded-2xl rounded-tr-md px-4 py-2.5 text-sm leading-relaxed">
            {content}
          </div>
          <span className="w-7 h-7 rounded-full bg-surface-700 border border-line flex items-center justify-center shrink-0 mt-0.5">
            <User size={13} className="text-slate-400" />
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2.5 mb-5 group">
      <span className="w-7 h-7 rounded-full bg-accent-faint/50 border border-accent-dim/40 flex items-center justify-center shrink-0 mt-0.5">
        <Shield size={13} className="text-accent" />
      </span>

      <div className="flex flex-col min-w-0 flex-1">
        {/* Thoughts (agent mode) */}
        {thoughts && thoughts.length > 0 && (
          <div className="mb-1.5 space-y-0.5">
            {thoughts.map((t, i) => (
              <p key={i} className="text-xs italic text-slate-500">{t}</p>
            ))}
          </div>
        )}

        {/* Answer / thinking / error */}
        <div className="card rounded-2xl rounded-tl-md px-4 py-3 text-sm relative">
          {error ? (
            <p className="flex items-center gap-2 text-red-400 text-sm">
              <AlertTriangle size={14} className="shrink-0" /> {error}
            </p>
          ) : isStreaming && !content ? (
            <span className="flex items-center gap-1.5 py-1" aria-label="Thinking">
              <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
            </span>
          ) : (
            <div className={cn('prose prose-sm prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-surface-950 prose-pre:border prose-pre:border-line',
              isStreaming && 'blink-cursor')}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}

          {!isStreaming && !error && content && (
            <button onClick={copy} aria-label="Copy answer"
              className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-slate-200">
              {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>
          )}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="mt-2">
            <button onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-200 mb-2 transition-colors">
              {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {sources.length} cited source{sources.length > 1 ? 's' : ''}
            </button>
            {showSources && (
              <div className="space-y-2 animate-slide-in">
                {sources.map((s, i) => <SourceCard key={i} source={s} index={i + 1} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
