import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Shield, MessageSquare, Database, Search, BarChart2, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../lib/cn'
import HealthDot from './HealthDot'

const NAV = [
  { to: '/chat',           label: 'Chat',           Icon: MessageSquare },
  { to: '/knowledge-base', label: 'Knowledge Base',  Icon: Database       },
  { to: '/investigate',    label: 'Investigate',     Icon: Search         },
  { to: '/analytics',      label: 'Analytics',       Icon: BarChart2      },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className={cn('flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-200', collapsed ? 'w-16' : 'w-60')}>
        {/* Logo */}
        <div className="flex items-center gap-2 px-3 py-4 border-b border-gray-800">
          <Shield className="text-blue-400 shrink-0" size={22} />
          {!collapsed && <span className="font-semibold text-sm tracking-wide">ThreatRAG</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 space-y-1 px-2">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              cn('flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors',
                isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100')
            }>
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Collapse toggle */}
        <button onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center py-3 border-t border-gray-800 text-gray-400 hover:text-gray-100">
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="flex items-center justify-between px-4 h-12 border-b border-gray-800 bg-gray-900">
          <span className="text-sm text-gray-400">kimi-k2-5 · ThreatRAG</span>
          <HealthDot />
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
