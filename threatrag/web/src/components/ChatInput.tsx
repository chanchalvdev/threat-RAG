import { useRef } from 'react'
import { Send, Square } from 'lucide-react'

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
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const handleSubmit = () => {
    if (loading || !trimmed || tooShort) return
    onSubmit()
    requestAnimationFrame(autoGrow)
  }

  return (
    <div className="border-t border-line-soft px-4 py-4 bg-surface-900">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            ref={ref}
            value={value}
            onChange={e => { onChange(e.target.value); autoGrow() }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
            }}
            placeholder="Ask about MITRE techniques, CVEs, or threat intel…"
            rows={1}
            aria-label="Message"
            className="input-base w-full resize-none rounded-xl px-4 py-3 pr-10 max-h-40 overflow-y-auto leading-relaxed"
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading || !trimmed || tooShort}
          aria-label="Send message"
          className="btn-primary rounded-xl p-3 shrink-0 shadow-glow"
        >
          {loading ? <Square size={16} /> : <Send size={16} />}
        </button>
      </div>
      <p className={`text-center text-[11px] mt-2 ${tooShort ? 'text-amber-400' : 'text-slate-600'}`}>
        {tooShort
          ? `Ask a bit more (at least ${MIN_LENGTH} characters)`
          : <>Enter to send · Shift+Enter for a new line · Answers cite MITRE ATT&amp;CK, OWASP &amp; CVE sources</>}
      </p>
    </div>
  )
}
