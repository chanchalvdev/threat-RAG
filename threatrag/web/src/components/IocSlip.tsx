import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import type { IOCType } from '../lib/useInvestigation'

const TYPES: { id: IOCType; label: string }[] = [
  { id: 'cve', label: 'CVE' }, { id: 'technique', label: 'Technique' }, { id: 'ip', label: 'IP address' },
  { id: 'hash', label: 'File hash' }, { id: 'domain', label: 'Domain' },
]

const EXAMPLES: { ioc: string; type: IOCType; note: string }[] = [
  { ioc: 'CVE-2021-44228', type: 'cve', note: 'Log4Shell' },
  { ioc: 'T1059.001', type: 'technique', note: 'PowerShell' },
  { ioc: '185.220.101.1', type: 'ip', note: 'Tor exit relay' },
  { ioc: '44d88612fea8a8f36de82e1278abb02f', type: 'hash', note: 'EICAR test file' },
]

/** Recognise the indicator's type from what was typed; null when unsure. */
export function detectType(v: string): IOCType | null {
  const s = v.trim()
  if (/^CVE-\d{4}-\d{4,}$/i.test(s)) return 'cve'
  if (/^T\d{4}(\.\d{3})?$/i.test(s)) return 'technique'
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(s) || /^[0-9a-f:]+:[0-9a-f:]+$/i.test(s)) return 'ip'
  if (/^([a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})$/i.test(s)) return 'hash'
  if (/^([a-z0-9-]+\.)+[a-z]{2,}$/i.test(s)) return 'domain'
  return null
}

interface Props {
  running: boolean
  onSubmit: (ioc: string, type: IOCType) => void
}

/** The request slip: indicator, its type (auto-detected, overridable), and the one action. */
export default function IocSlip({ running, onSubmit }: Props) {
  const [ioc, setIoc] = useState('')
  const [type, setType] = useState<IOCType>('cve')
  const [pinned, setPinned] = useState(false)

  const change = (v: string) => {
    setIoc(v)
    const t = detectType(v)
    if (t && !pinned) setType(t)
  }
  const go = (value = ioc, t = type) => { if (value.trim() && !running) onSubmit(value.trim(), t) }

  return (
    <div>
      <form onSubmit={e => { e.preventDefault(); go() }}
        className="card flex flex-col sm:flex-row sm:items-stretch focus-within:border-act transition-colors">
        <label className="sr-only" htmlFor="ioc-type">IOC type</label>
        <select id="ioc-type" value={type} onChange={e => { setType(e.target.value as IOCType); setPinned(true) }}
          className="bg-transparent text-sm font-bold px-4 py-3 sm:w-40 border-b sm:border-b-0 sm:border-r border-rule focus:outline-none focus-visible:bg-card-2 cursor-pointer">
          {TYPES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <label className="sr-only" htmlFor="ioc-value">Indicator</label>
        <input id="ioc-value" value={ioc} onChange={e => change(e.target.value)} autoComplete="off" spellCheck={false}
          placeholder="CVE-2021-44228, T1055, 185.220.101.1…"
          className="flex-1 min-w-0 bg-transparent font-mono text-lg px-4 py-3 focus:outline-none focus-visible:outline-none" />
        <button type="submit" disabled={running || !ioc.trim()} className="btn-act sm:px-7 py-3.5 text-[15px]">
          {running ? 'Investigating…' : 'Investigate'} {!running && <ArrowRight size={17} strokeWidth={2.25} />}
        </button>
      </form>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-3 text-sm">
        <span className="label">Try</span>
        {EXAMPLES.map(e => (
          <button key={e.ioc} type="button" disabled={running}
            onClick={() => { setIoc(e.ioc); setType(e.type); setPinned(false); go(e.ioc, e.type) }}
            className="group flex items-baseline gap-1.5 disabled:opacity-45">
            <span className="font-mono text-ink underline decoration-rule-strong/40 group-hover:decoration-act group-enabled:group-hover:text-act transition-colors">
              {e.ioc.length > 20 ? e.ioc.slice(0, 12) + '…' : e.ioc}
            </span>
            <span className="text-ink-3 text-xs">{e.note}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
