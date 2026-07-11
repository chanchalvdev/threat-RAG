import { useState } from 'react'
import { Database, Shield, Globe, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'

export interface ToolCallEntry {
  tool_use_id: string
  name: string
  input: string
  result?: string
}

const TOOL_META: Record<string, { icon: React.ReactNode; label: string }> = {
  threat_rag_search: { icon: <Database size={13} />, label: 'Knowledge base search' },
  nvd_cve_lookup:    { icon: <Shield size={13} />,   label: 'NVD CVE lookup' },
  web_search:        { icon: <Globe size={13} />,    label: 'Web search' },
}

export default function ToolCallTimeline({ calls }: { calls: ToolCallEntry[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  if (calls.length === 0) return null

  return (
    <div className="space-y-1.5 mt-1 border-l-2 border-line pl-3">
      {calls.map(c => {
        const meta = TOOL_META[c.name] ?? { icon: <Database size={13} />, label: c.name }
        const open = expanded === c.tool_use_id
        return (
          <div key={c.tool_use_id} className="card rounded-lg overflow-hidden animate-slide-in">
            <button onClick={() => setExpanded(open ? null : c.tool_use_id)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-surface-700 transition-colors">
              <span className="text-accent">{meta.icon}</span>
              <span className="text-slate-300 font-medium shrink-0">{meta.label}</span>
              <span className="text-slate-500 font-mono truncate flex-1">{c.input.slice(0, 80)}</span>
              {c.result === undefined
                ? <Loader2 size={12} className="text-accent animate-spin shrink-0" />
                : open ? <ChevronUp size={12} className="text-slate-500" /> : <ChevronDown size={12} className="text-slate-500" />}
            </button>
            {open && c.result !== undefined && (
              <div className="px-3 py-2.5 text-xs border-t border-line font-mono whitespace-pre-wrap animate-fade-in">
                <p className="text-slate-500 mb-1.5">Input: {c.input}</p>
                <p className="text-slate-300 max-h-48 overflow-y-auto">{c.result.slice(0, 500)}</p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
