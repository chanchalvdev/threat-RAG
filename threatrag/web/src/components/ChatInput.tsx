import { useRef } from 'react'
import { ArrowUp, Square } from 'lucide-react'
import { cn } from '../lib/cn'

interface Props {
  value: string
  loading: boolean
  onChange: (v: string) => void
  onSubmit: () => void
}

const MIN_LENGTH = 10

export default function ChatInput({ value, loading, onChange, onSubmit }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const trimmed = value.trim()
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_LENGTH

  const autoGrow = () => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  const handleSubmit = () => {
    if (loading || !trimmed || tooShort) return
    onSubmit()
    requestAnimationFrame(autoGrow)
  }

  return (
    <div className="no-print sticky bottom-0 bg-ground/95 backdrop-blur-[2px] px-4 md:px-8 pt-3 pb-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end bg-card border-t-[3px] border-rule-strong focus-within:border-act transition-colors">
          <span className="font-mono text-xs text-ink-3 pl-4 pb-[15px] shrink-0 select-none" aria-hidden>Q</span>
          <textarea
            ref={ref}
            value={value}
            onChange={e => { onChange(e.target.value); autoGrow() }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
            }}
            placeholder="Ask about an ATT&CK technique, a CVE, or an OWASP LLM risk"
            rows={1}
            aria-label="Message"
            className="flex-1 bg-transparent resize-none px-3 py-3.5 text-[15px] leading-relaxed text-ink max-h-[180px] overflow-y-auto focus:outline-none focus-visible:outline-none"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || !trimmed || tooShort}
            aria-label="Send message"
            className="btn-act h-12 w-12 px-0 shrink-0"
          >
            {loading ? <Square size={15} fill="currentColor" /> : <ArrowUp size={18} strokeWidth={2.25} />}
          </button>
        </div>
        <p className={cn('text-xs mt-2', tooShort ? 'text-ochre font-bold' : 'text-ink-3')}>
          {tooShort
            ? `Ask a bit more: at least ${MIN_LENGTH} characters`
            : 'Enter files the question · Shift+Enter adds a line · answers cite ATT&CK, OWASP and NVD'}
        </p>
      </div>
    </div>
  )
}
