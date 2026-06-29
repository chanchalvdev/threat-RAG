const SUGGESTIONS = [
  'Explain T1055 Process Injection',
  'What CVEs affect Apache Log4j?',
  'OWASP LLM01: Prompt Injection explained',
  'How does ransomware spread laterally?',
  'Compare T1078 and T1133',
  'Latest supply chain attack techniques',
]

interface Props {
  onSelect: (text: string) => void
}

export default function SearchSuggestions({ onSelect }: Props) {
  return (
    <div className="grid grid-cols-2 gap-2 max-w-2xl mx-auto mt-4">
      {SUGGESTIONS.map(s => (
        <button key={s} onClick={() => onSelect(s)}
          className="text-left text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-lg px-3 py-2 transition-colors">
          {s}
        </button>
      ))}
    </div>
  )
}
