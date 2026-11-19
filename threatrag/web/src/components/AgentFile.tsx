import { Check, CornerDownLeft, FlaskConical, Gavel, PenLine, type LucideIcon } from 'lucide-react'
import { cn } from '../lib/cn'
import type { NodeId, NodeState, TrailEntry } from '../lib/useInvestigation'
import Holes from './Holes'

const AGENTS: { id: NodeId; serial: string; label: string; role: string; Icon: LucideIcon; tab: string; ink: string }[] = [
  { id: 'researcher', serial: 'AG-1', label: 'Researcher', role: 'Gathers intel from the index, NVD and the web', Icon: FlaskConical, tab: 'bg-cobalt', ink: 'text-cobalt' },
  { id: 'critic',     serial: 'AG-2', label: 'Critic',     role: 'Challenges findings and sends gaps back',     Icon: Gavel,        tab: 'bg-verm',   ink: 'text-verm' },
  { id: 'reporter',   serial: 'AG-3', label: 'Reporter',   role: 'Writes the final assessment',                 Icon: PenLine,      tab: 'bg-ochre-fill', ink: 'text-ochre' },
]

const STATUS: Record<NodeState['status'], string> = { idle: 'Waiting', active: 'Working', done: 'Filed' }

interface Props {
  nodes: Record<NodeId, NodeState>
  iteration: number
  trail: TrailEntry[]
  sendBacks: string[]
}

/** The three agents as cards filed left to right; the Critic's send-backs are shown, not hidden. */
export default function AgentFile({ nodes, iteration, trail, sendBacks }: Props) {
  return (
    <ol className="grid grid-cols-1 md:grid-cols-3 gap-x-0 gap-y-6 md:gap-y-0" aria-label="Agent pipeline">
      {AGENTS.map((a, i) => {
        const n = nodes[a.id]
        return (
          <li key={a.id} className={cn('card mt-[13px] px-4 pt-3.5 pb-4 min-h-[9.5rem] md:border-r md:border-r-rule',
            i === 2 && 'md:border-r-0', n.status === 'idle' && 'bg-card/70')}>
            <span aria-hidden className={cn('tab', a.tab, n.status === 'idle' && 'opacity-40')} />
            {n.status === 'active' && (
              <span aria-hidden className="absolute -top-[3px] inset-x-0 h-[3px] overflow-hidden">
                <span className={cn('absolute inset-y-0 w-2/5 animate-rule-run', a.tab)} />
              </span>
            )}
            <div className="flex items-center gap-2.5 pb-2.5 mb-3 border-b border-rule">
              <span className="font-mono text-xs text-ink-3">{a.serial}</span>
              <a.Icon size={16} strokeWidth={1.75} className={n.status === 'idle' ? 'text-ink-3' : a.ink} />
              <span className="display text-xl [font-variation-settings:'wdth'_80]">{a.label}</span>
              <span className={cn('ml-auto label flex items-center gap-1', n.status === 'done' ? 'text-green' : n.status === 'active' ? a.ink : '')}>
                {n.status === 'done' && <Check size={12} strokeWidth={2.5} />}{STATUS[n.status]}
              </span>
            </div>

            {a.id === 'researcher' && (
              <div className="space-y-1.5">
                {iteration > 0 && (
                  <p className="flex items-center gap-2 text-xs text-ink-2">
                    <Holes filled={iteration} total={Math.max(3, iteration)} className="text-cobalt" label={`Research pass ${iteration}`} />
                    pass {iteration}
                  </p>
                )}
                {trail.length === 0
                  ? <p className="text-xs text-ink-3">{a.role}</p>
                  : <ul className="font-mono text-xs text-ink-2 space-y-0.5">
                      {trail.slice(-4).map((t, k) => (
                        <li key={k} className="truncate animate-file-in"><span className="text-ink-3">→</span> {t.name} <span className="text-ink">{t.input}</span></li>
                      ))}
                    </ul>}
              </div>
            )}

            {a.id === 'critic' && (
              sendBacks.length > 0
                ? <ul className="space-y-1.5">
                    {sendBacks.map((r, k) => (
                      <li key={k} className="flex gap-2 text-xs text-ink-2 animate-file-in">
                        <CornerDownLeft size={13} className="text-verm shrink-0 mt-0.5" />
                        <span><b className="text-verm font-semibold">Returned to Researcher.</b> {r}</span>
                      </li>
                    ))}
                    {n.status === 'done' && <li className="text-xs text-ink-2">Accepted on pass {iteration}.</li>}
                  </ul>
                : <p className="text-xs text-ink-3 line-clamp-4">{n.detail || a.role}</p>
            )}

            {a.id === 'reporter' && (
              <p className={cn('text-xs line-clamp-4', n.detail ? 'text-ink-2' : 'text-ink-3')}>{n.detail || a.role}</p>
            )}
          </li>
        )
      })}
    </ol>
  )
}
