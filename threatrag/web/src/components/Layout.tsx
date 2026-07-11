import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Shield, MessageSquare, Database, Search, BarChart2, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { cn } from '../lib/cn'
import HealthDot from './HealthDot'

const NAV = [
  { to: '/chat',           label: 'Chat',           desc: 'Ask the threat intel assistant',      Icon: MessageSquare },
  { to: '/knowledge-base', label: 'Knowledge Base', desc: 'Ingest and inspect intel sources',    Icon: Database },
  { to: '/investigate',    label: 'Investigate',    desc: 'Multi-agent IOC investigation',       Icon: Search },
  { to: '/analytics',      label: 'Analytics',      desc: 'RAGAs answer-quality evaluation',     Icon: BarChart2 },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const { pathname } = useLocation()
  const current = NAV.find(n => pathname.startsWith(n.to)) ?? NAV[0]

  return (
    <div className="flex h-screen bg-surface-950 text-slate-100">
      {/* Sidebar */}
      <aside className={cn(
        'flex flex-col bg-surface-900 border-r border-line-soft transition-all duration-200',
        collapsed ? 'w-[60px]' : 'w-60'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-3.5 h-14 border-b border-line-soft shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent-faint/60 border border-accent-dim/40 flex items-center justify-center shrink-0">
            <Shield className="text-accent" size={17} />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <span className="font-semibold text-sm tracking-wide">ThreatRAG</span>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">Intel Console</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 space-y-1 px-2">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} title={collapsed ? label : undefined} className={({ isActive }) =>
              cn('flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors',
                collapsed && 'justify-center',
                isActive
                  ? 'bg-accent-faint/50 text-accent-bright border border-accent-dim/30'
                  : 'text-slate-400 border border-transparent hover:bg-surface-800 hover:text-slate-100')
            }>
              <Icon size={17} className="shrink-0" />
              {!collapsed && <span className="font-medium">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Collapse toggle */}
        <button onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex items-center justify-center gap-2 py-3 border-t border-line-soft text-slate-500 hover:text-slate-200 text-xs transition-colors">
          {collapsed ? <PanelLeftOpen size={15} /> : <><PanelLeftClose size={15} /> Collapse</>}
        </button>
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <header className="flex items-center justify-between px-5 h-14 border-b border-line-soft bg-surface-900 shrink-0">
          <div className="leading-tight min-w-0">
            <h1 className="text-sm font-semibold text-slate-100">{current.label}</h1>
            <p className="text-xs text-slate-500 truncate">{current.desc}</p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <span className="hidden sm:inline text-[11px] font-mono text-slate-500 bg-surface-800 border border-line rounded-md px-2 py-1">
              kimi-k2-5
            </span>
            <HealthDot />
          </div>
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
