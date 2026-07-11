import { useEffect, useRef, useState } from 'react'
import { Shield, RotateCcw } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import SearchSuggestions from '../components/SearchSuggestions'
import ToolCallTimeline from '../components/ToolCallTimeline'
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

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

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

    try {
      const newSessionId = await streamQuery(text, (evt: SSEEvent) => {
        if (evt.type === 'source') sources.push(evt.data)
        if (evt.type === 'thought') thoughts.push(evt.data)
        if (evt.type === 'tool_call') toolCalls.push({ ...evt.data, result: undefined })
        if (evt.type === 'tool_result') {
          const tc = toolCalls.find(t => t.tool_use_id === evt.tool_use_id)
          if (tc) tc.result = evt.data
        }
        if (evt.type === 'error') throw new Error(evt.data)
        if (evt.type === 'chunk') {
          content += evt.data
          patchLast({ content, sources: [...sources], thoughts: [...thoughts], toolCalls: [...toolCalls] })
        }
      }, sessionRef.current)

      if (newSessionId) {
        sessionRef.current = newSessionId
        sessionStorage.setItem('session_id', newSessionId)
      }
      patchLast({ isStreaming: false, sources, thoughts, toolCalls })
    } catch (err) {
      patchLast({
        isStreaming: false,
        error: err instanceof Error ? err.message : 'Request failed — is the backend running?',
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
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="text-center mt-16 animate-fade-in px-4">
            <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-accent-faint/50 border border-accent-dim/40 flex items-center justify-center shadow-glow">
              <Shield className="text-accent" size={26} />
            </div>
            <h2 className="text-2xl font-semibold text-slate-100 mb-2">Ask a security question</h2>
            <p className="text-slate-500 text-sm">
              Grounded in MITRE ATT&amp;CK, OWASP and CVE intelligence — every answer cites its sources
            </p>
            <SearchSuggestions onSelect={submit} />
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            <div className="flex justify-end mb-4">
              <button onClick={newConversation}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-200 transition-colors">
                <RotateCcw size={12} /> New conversation
              </button>
            </div>
            {messages.map((msg, i) => (
              <div key={i} className="animate-slide-in">
                <ChatMessage {...msg} />
                {msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mb-4 pl-11"><ToolCallTimeline calls={msg.toolCalls} /></div>
                )}
              </div>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput value={input} loading={loading} onChange={setInput} onSubmit={() => submit(input)} />
    </div>
  )
}
