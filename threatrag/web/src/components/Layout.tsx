import { useEffect, type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileSearch, MessagesSquare, Library, Activity, Moon, Sun } from 'lucide-react'
import { cn } from '../lib/cn'
import { useTheme } from '../lib/theme'
import { getIngestStats, getRuntimeMetrics } from '../lib/api'
import HealthDot from './HealthDot'

export const NAV = [
  { to: '/investigate',    key: '1', label: 'Investigate',    Icon: FileSearch },
  { to: '/chat',           key: '2', label: 'Ask',            Icon: MessagesSquare },
  { to: '/knowledge-base', key: '3', label: 'Knowledge base', Icon: Library },
  { to: '/analytics',      key: '4', label: 'Analytics',      Icon: Activity },
]

const typing = (el: EventTarget | null) =>
  el instanceof HTMLElement && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { theme, toggle } = useTheme()
  const { data: metrics } = useQuery({ queryKey: ['runtime-metrics'], queryFn: getRuntimeMetrics, refetchInterval: 60_000 })
  const { data: stats } = useQuery({ queryKey: ['ingest-stats'], queryFn: getIngestStats, retry: false })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return
      const hit = NAV.find(n => n.key === e.key)
      if (hit) navigate(hit.to)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  const ThemeIcon = theme === 'dark' ? Sun : Moon
  const themeLabel = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'

  return (
    <div className="flex flex-col md:flex-row h-[100dvh] overflow-hidden bg-ground text-ink">
      <nav aria-label="Primary" className="bg-rail text-rail-ink md:w-[232px] shrink-0 flex flex-wrap items-center md:items-stretch md:flex-nowrap md:flex-col">
        <div className="flex-1 md:flex-none px-4 md:px-5 py-3 md:pt-6 md:pb-7">
          <div>
            <span className="display text-[1.6rem] md:text-[1.85rem] tracking-[0.02em] block">THREATRAG</span>
            <span className="hidden md:block text-2xs font-bold uppercase tracking-[0.14em] text-rail-ink2 mt-1.5">Cross-reference index</span>
          </div>
        </div>

        <ul className="order-last md:order-none w-full grid grid-cols-4 md:flex md:flex-col border-t border-rail-2 md:border-0">
          {NAV.map(({ to, key, label, Icon }) => (
            <li key={to} className="min-w-0">
              <NavLink to={to} className={({ isActive }) => cn(
                'group flex flex-col md:flex-row items-center justify-center md:justify-start gap-1 md:gap-3 h-14 md:h-11 px-1 md:px-5',
                'text-2xs md:text-sm transition-colors duration-150 relative',
                isActive ? 'bg-ground text-ink font-bold' : 'text-rail-ink/80 hover:bg-rail-2 hover:text-rail-ink')}>
                {({ isActive }) => (<>
                  <Icon size={17} strokeWidth={1.75} className="shrink-0" />
                  <span className="truncate max-w-full">{label}</span>
                  <kbd className={cn('hidden md:inline ml-auto font-mono text-2xs', isActive ? 'text-ink-3' : 'text-rail-ink2')}>{key}</kbd>
                </>)}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="md:mt-auto flex md:flex-col items-center md:items-stretch gap-3 px-4 md:px-5 md:pb-5 text-xs text-rail-ink2">
          <dl className="flex md:block items-center gap-3 md:space-y-1.5 md:border-t border-rail-2 md:pt-4 leading-snug">
            <div><dt className="sr-only">Service</dt><dd><HealthDot className="text-rail-ink" /></dd></div>
            {metrics?.llm.primary_model && (
              <div title="Primary model configured on the backend" className="hidden md:block"><dt className="sr-only">Model</dt><dd className="break-all font-mono">{metrics.llm.primary_model}</dd></div>
            )}
            {stats && <div className="hidden md:block"><dt className="sr-only">Index size</dt><dd>{stats.total_vectors.toLocaleString()} cards filed</dd></div>}
          </dl>
          <button onClick={toggle} aria-label={themeLabel} title={themeLabel}
            className="flex items-center gap-2 h-9 px-2 md:px-0 text-rail-ink2 hover:text-rail-ink transition-colors">
            <ThemeIcon size={15} strokeWidth={1.75} />
            <span className="hidden md:inline">{theme === 'dark' ? 'Light' : 'Dark'} theme</span>
          </button>
        </div>
      </nav>

      <main className="flex-1 overflow-auto min-w-0">{children}</main>
    </div>
  )
}
