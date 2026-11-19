import { ArrowRight } from 'lucide-react'

const SUGGESTIONS = [
  { ref: 'T1055',      kind: 'ATT&CK',   text: 'Explain T1055 Process Injection' },
  { ref: 'CVE',        kind: 'NVD',      text: 'What CVEs affect Apache Log4j?' },
  { ref: 'LLM01',      kind: 'OWASP',    text: 'OWASP LLM01: Prompt Injection explained' },
  { ref: 'TA0008',     kind: 'ATT&CK',   text: 'How does ransomware spread laterally?' },
  { ref: 'T1078·T1133', kind: 'ATT&CK',  text: 'Compare T1078 and T1133' },
  { ref: 'T1195',      kind: 'ATT&CK',   text: 'Latest supply chain attack techniques' },
]

interface Props {
  onSelect: (text: string) => void
}

/** A drawer of starter questions, filed by the reference each one leans on. */
export default function SearchSuggestions({ onSelect }: Props) {
  return (
    <div className="card mt-[13px]">
    <span aria-hidden className="tab bg-ochre-fill" />
    <ul className="divide-y divide-rule" aria-label="Example questions">
      {SUGGESTIONS.map(({ ref, kind, text }) => (
        <li key={text}>
          <button type="button" onClick={() => onSelect(text)}
            className="group w-full grid grid-cols-[7.5rem_1fr_auto] items-center gap-4 px-5 py-3.5 text-left hover:bg-card-2 transition-colors">
            <span className="leading-tight">
              <span className="block font-mono text-sm font-bold text-ink">{ref}</span>
              <span className="label">{kind}</span>
            </span>
            <span className="text-[15px] text-ink-2 group-hover:text-ink transition-colors">{text}</span>
            <ArrowRight size={16} strokeWidth={1.75} className="text-ink-3 group-hover:text-act group-hover:translate-x-0.5 transition-[transform,color] duration-200" />
          </button>
        </li>
      ))}
    </ul>
    </div>
  )
}
