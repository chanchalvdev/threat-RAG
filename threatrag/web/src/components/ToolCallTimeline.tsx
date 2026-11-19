import { useState } from 'react'
import { Database, ShieldAlert, Globe, Fingerprint, Radar, ChevronDown, type LucideIcon } from 'lucide-react'
import { cn } from '../lib/cn'

export interface ToolCallEntry {
  tool_use_id: string
  name: string
  input: string
  result?: string
}

const TOOL_META: Record<string, { Icon: LucideIcon; label: string }> = {
  threat_rag_search:       { Icon: Database,    label: 'Knowledge base search' },
  nvd_cve_lookup:          { Icon: ShieldAlert, label: 'NVD CVE lookup' },
  web_search:              { Icon: Globe,       label: 'Web search' },
  cve_exploitation_lookup: { Icon: Radar,       label: 'Exploitation status (KEV, EPSS)' },
  ip_intel_lookup:         { Icon: Globe,       label: 'IP intelligence' },
  domain_intel_lookup:     { Icon: Globe,       label: 'Domain intelligence' },
  hash_intel_lookup:       { Icon: Fingerprint, label: 'File hash intelligence' },
}

/** The lookup ledger: one ruled line per tool call, L-n serials, result on demand. */
export default function ToolCallTimeline({ calls }: { calls: ToolCallEntry[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  if (calls.length === 0) return null

  return (
    <ol aria-label="Tool calls" className="border-y border-rule divide-y divide-rule text-xs">
      {calls.map((c, i) => {
        const { Icon, label } = TOOL_META[c.name] ?? { Icon: Database, label: c.name }
        const open = expanded === c.tool_use_id
        const pending = c.result === undefined
        return (
          <li key={c.tool_use_id} className="animate-file-in">
            <button type="button" disabled={pending} onClick={() => setExpanded(open ? null : c.tool_use_id)}
              aria-expanded={open}
              className="w-full grid grid-cols-[2.25rem_auto_1fr_auto] items-center gap-2.5 py-2 text-left
                         enabled:hover:bg-card-2 disabled:cursor-progress transition-colors">
              <span className="font-mono text-ink-3 pl-1">L-{i + 1}</span>
              <span className="flex items-center gap-1.5 font-semibold text-ink">
                <Icon size={13} strokeWidth={1.75} className="text-cobalt" />{label}
              </span>
              <span className="font-mono text-ink-2 truncate">{c.input.slice(0, 90)}</span>
              {pending
                ? <span className="relative h-[3px] w-10 overflow-hidden bg-rule mr-1" aria-label="Running">
                    <span className="absolute inset-y-0 w-1/2 bg-cobalt animate-rule-run" />
                  </span>
                : <ChevronDown size={13} className={cn('text-ink-3 mr-1 transition-transform', open && 'rotate-180')} />}
            </button>
            {open && !pending && (
              <div className="pl-[3.6rem] pr-3 pb-3 font-mono whitespace-pre-wrap animate-file-in">
                <p className="text-ink-3 mb-1">in: {c.input}</p>
                <p className="text-ink-2 max-h-48 overflow-y-auto">{c.result!.slice(0, 600)}</p>
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
