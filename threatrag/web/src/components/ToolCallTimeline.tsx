import { useState } from 'react'
import { Database, Shield, Globe, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { cn } from '../lib/cn'

export interface ToolCallEntry {
  tool_use_id: string
  name: string
  input: string
  result?: string
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  threat_rag_search: <Database size={14} />,
  nvd_cve_lookup:    <Shield size={14} />,
  web_search:        <Globe size={14} />,
}

export default function ToolCallTimeline({ calls }: { calls: ToolCallEntry[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  if (calls.length === 0) return null

  return (
    <div className="space-y-2 mt-2">
      {calls.map(c => (
        <div key={c.tool_use_id}
          className={cn('rounded-lg border border-gray-700 bg-gray-850 overflow-hidden animate-slide-in')}>
          <button onClick={() => setExpanded(expanded === c.tool_use_id ? null : c.tool_use_id)}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-gray-800">
            <span className="text-gray-400">{TOOL_ICONS[c.name] ?? <Database size={14} />}</span>
            <span className="bg-gray-700 text-gray-200 px-1.5 py-0.5 rounded font-mono">{c.name}</span>
            <span className="text-gray-400 truncate flex-1">{c.input.slice(0, 80)}</span>
            {c.result === undefined
              ? <Loader2 size={12} className="text-blue-400 animate-spin" />
              : expanded === c.tool_use_id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {expanded === c.tool_use_id && c.result !== undefined && (
            <div className="px-3 pb-2 text-xs text-gray-300 border-t border-gray-700 font-mono whitespace-pre-wrap">
              <p className="text-gray-500 mb-1">Input: {c.input}</p>
              <p>{c.result.slice(0, 500)}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
