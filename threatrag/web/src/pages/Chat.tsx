import { useEffect, useRef, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import SearchSuggestions from '../components/SearchSuggestions'
import { streamQuery } from '../lib/api'
import type { SourceDoc, SSEEvent } from '../lib/api'
import type { ToolCallEntry } from '../components/ToolCallTimeline'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDoc[]
  thoughts?: string[]
  toolCalls?: ToolCallEntry[]
  isStreaming?: boolean
  error?: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const sessionRef = useRef<string | undefined>(sessionStorage.getItem('session_id') ?? undefined)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages])

  const patchLast = (patch: Partial<Message>) =>
    setMessages(prev => {
      const msgs = [...prev]
      msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }
      return msgs
    })

  const submit = async (text: string) => {
    if (!text.trim() || loading) return
    setInput('')
    setLoading(true)
    setMessages(prev => [...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true, sources: [], thoughts: [], toolCalls: [] },
    ])

    const sources: SourceDoc[] = []
    const thoughts: string[] = []
    const toolCalls: ToolCallEntry[] = []
    let content = ''
    const sync = () => patchLast({ content, sources: [...sources], thoughts: [...thoughts], toolCalls: toolCalls.map(t => ({ ...t })) })

    try {
      const newSessionId = await streamQuery(text, (evt: SSEEvent) => {
        if (evt.type === 'source') sources.push(evt.data)
        if (evt.type === 'thought') { thoughts.push(evt.data); sync() }
        if (evt.type === 'tool_call') { toolCalls.push({ ...evt.data, result: undefined }); sync() }
        if (evt.type === 'tool_result') {
          const tc = toolCalls.find(t => t.tool_use_id === evt.tool_use_id)
          if (tc) tc.result = evt.data
          sync()
        }
        if (evt.type === 'error') throw new Error(evt.data)
        if (evt.type === 'chunk') { content += evt.data; sync() }
      }, sessionRef.current)

      if (newSessionId) {
        sessionRef.current = newSessionId
        sessionStorage.setItem('session_id', newSessionId)
      }
      patchLast({ isStreaming: false, sources, thoughts, toolCalls })
    } catch (err) {
      patchLast({
        isStreaming: false,
        error: err instanceof Error ? err.message : 'Request failed: the API did not answer. Check that the backend is running.',
      })
    } finally {
      setLoading(false)
    }
  }

  const newConversation = () => {
    sessionRef.current = undefined
    sessionStorage.removeItem('session_id')
    setMessages([])
  }

  return (
    <div className="flex flex-col min-h-full">
      <div className="flex-1 px-4 md:px-8 pt-8 md:pt-10 pb-6">
        <div className="max-w-3xl mx-auto">
          <header className="flex items-end justify-between gap-4 border-b border-rule-strong pb-4">
            <div>
              <h1 className="display text-4xl md:text-5xl">Ask the index</h1>
              {messages.length > 0 && (
                <p className="text-xs text-ink-3 mt-2">{Math.ceil(messages.length / 2)} question{messages.length > 2 ? 's' : ''} filed this session</p>
              )}
            </div>
            {messages.length > 0 && (
              <button type="button" onClick={newConversation} disabled={loading} className="btn-line text-xs shrink-0">
                <RotateCcw size={13} /> New conversation
              </button>
            )}
          </header>

          {messages.length === 0 ? (
            <div className="pt-6 animate-file-in">
              <p className="text-ink-2 max-w-[60ch] leading-relaxed mb-8">
                Answers are grounded in MITRE ATT&amp;CK and the OWASP LLM Top 10, with CVEs looked up live from NVD.
                Every claim carries a cross-reference: hover an <span className="chip-ref bg-cobalt text-card cursor-default">S-1</span> chip to see the passage behind it.
              </p>
              <SearchSuggestions onSelect={submit} />
            </div>
          ) : (
            <div className="space-y-2">
              {messages.map((msg, i) => (
                <div key={i} className="animate-file-in">
                  <ChatMessage {...msg} serial={Math.floor(i / 2) + 1} />
                </div>
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput value={input} loading={loading} onChange={setInput} onSubmit={() => submit(input)} />
    </div>
  )
}
