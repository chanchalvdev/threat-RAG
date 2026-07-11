import { Crosshair, Bug, ShieldAlert, Network, GitCompare, Boxes } from 'lucide-react'

const SUGGESTIONS = [
  { text: 'Explain T1055 Process Injection',            Icon: Crosshair },
  { text: 'What CVEs affect Apache Log4j?',             Icon: Bug },
  { text: 'OWASP LLM01: Prompt Injection explained',    Icon: ShieldAlert },
  { text: 'How does ransomware spread laterally?',      Icon: Network },
  { text: 'Compare T1078 and T1133',                    Icon: GitCompare },
  { text: 'Latest supply chain attack techniques',      Icon: Boxes },
]

interface Props {
  onSelect: (text: string) => void
}

export default function SearchSuggestions({ onSelect }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-2xl mx-auto mt-8">
      {SUGGESTIONS.map(({ text, Icon }) => (
        <button key={text} onClick={() => onSelect(text)}
          className="group flex items-center gap-3 text-left text-sm card px-4 py-3
                     hover:border-accent-dim/50 hover:bg-surface-700 transition-all">
          <span className="w-8 h-8 rounded-lg bg-surface-700 border border-line flex items-center justify-center shrink-0
                           text-slate-400 group-hover:text-accent group-hover:border-accent-dim/40 transition-colors">
            <Icon size={15} />
          </span>
          <span className="text-slate-300 group-hover:text-slate-100 transition-colors">{text}</span>
        </button>
      ))}
    </div>
  )
}
