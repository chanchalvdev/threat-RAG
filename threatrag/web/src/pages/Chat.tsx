import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
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
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const sessionRef = useRef<string | undefined>(sessionStorage.getItem('session_id') ?? undefined)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const submit = async (text: string) => {
    if (!text.trim() || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { role: 'user', content: text }
    const assistantMsg: Message = { role: 'assistant', content: '', isStreaming: true, sources: [], thoughts: [], toolCalls: [] }
    setMessages(prev => [...prev, userMsg, assistantMsg])

    const sources: SourceDoc[] = []
    const thoughts: string[] = []
    const toolCalls: ToolCallEntry[] = []

    const newSessionId = await streamQuery(text, (evt: SSEEvent) => {
      if (evt.type === 'source') sources.push(evt.data)
      if (evt.type === 'thought') thoughts.push(evt.data)
      if (evt.type === 'tool_call') toolCalls.push({ ...evt.data, result: undefined })
      if (evt.type === 'tool_result') {
        const tc = toolCalls.find(t => t.tool_use_id === evt.tool_use_id)
        if (tc) tc.result = evt.data
      }
      if (evt.type === 'chunk') {
        setMessages(prev => {
          const msgs = [...prev]
          const last = { ...msgs[msgs.length - 1] }
          last.content += evt.data
          last.sources = [...sources]
          last.thoughts = [...thoughts]
          last.toolCalls = [...toolCalls]
          msgs[msgs.length - 1] = last
          return msgs
        })
      }
    }, sessionRef.current)

    if (newSessionId) {
      sessionRef.current = newSessionId
      sessionStorage.setItem('session_id', newSessionId)
    }

    setMessages(prev => {
      const msgs = [...prev]
      const last = { ...msgs[msgs.length - 1], isStreaming: false, sources, thoughts, toolCalls }
      msgs[msgs.length - 1] = last
      return msgs
    })
    setLoading(false)
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
        {messages.length === 0 && (
          <div className="text-center mt-12">
            <h2 className="text-xl font-semibold text-gray-200 mb-2">Ask a security question</h2>
            <p className="text-gray-500 text-sm mb-6">Powered by MITRE ATT&CK, OWASP, and CVE intelligence</p>
            <SearchSuggestions onSelect={text => submit(text)} />
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            <ChatMessage {...msg} />
            {msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0 && (
              <div className="max-w-3xl mb-4">
                <ToolCallTimeline calls={msg.toolCalls} />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 px-4 py-3 bg-gray-900">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <button onClick={newConversation} className="text-xs text-gray-500 hover:text-gray-300 shrink-0 pb-2">
            New chat
          </button>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(input) } }}
            placeholder="Ask about MITRE techniques, CVEs, or threat intel..."
            rows={1}
            className="flex-1 resize-none bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 max-h-40 overflow-y-auto"
          />
          <button onClick={() => submit(input)} disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-xl p-2.5 shrink-0">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
