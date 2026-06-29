import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '../lib/cn'
import SourceCard from './SourceCard'
import type { SourceDoc } from '../lib/api'

interface Props {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDoc[]
  thoughts?: string[]
  isStreaming?: boolean
}

export default function ChatMessage({ role, content, sources, thoughts, isStreaming }: Props) {
  const [showSources, setShowSources] = useState(false)
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-xl bg-blue-700 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col mb-4 group">
      {/* Thoughts (agent mode) */}
      {thoughts && thoughts.length > 0 && (
        <div className="mb-1 space-y-0.5">
          {thoughts.map((t, i) => (
            <p key={i} className="text-xs italic text-gray-500">{t}</p>
          ))}
        </div>
      )}

      {/* Answer */}
      <div className="max-w-3xl bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm relative">
        <div className={cn('prose prose-sm prose-invert max-w-none', isStreaming && 'blink-cursor')}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>

        {/* Copy button */}
        {!isStreaming && (
          <button onClick={copy}
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-100"
            title={copied ? 'Copied!' : 'Copy'}>
            <Copy size={14} className={copied ? 'text-green-400' : ''} />
          </button>
        )}
      </div>

      {/* Sources */}
      {sources && sources.length > 0 && (
        <div className="mt-2 max-w-3xl">
          <button onClick={() => setShowSources(!showSources)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-100 mb-2">
            {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            Sources ({sources.length})
          </button>
          {showSources && (
            <div className="space-y-2">
              {sources.map((s, i) => <SourceCard key={i} source={s} index={i + 1} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
