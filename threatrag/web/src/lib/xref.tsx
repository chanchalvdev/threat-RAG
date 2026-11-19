import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from './cn'
import type { SourceDoc } from './api'

/**
 * Cross-references: the model cites passages as [Source: <source> · <ID>].
 * Those markers become S-n chips that light up the matching source card, and back.
 */
interface XrefState {
  active: number | null
  setActive: (n: number | null) => void
  opened: { n: number; t: number } | null
  open: (n: number) => void
}
const Ctx = createContext<XrefState>({ active: null, setActive: () => undefined, opened: null, open: () => undefined })
export const useXref = () => useContext(Ctx)

/** Scope for one answer or report: chips and source cards inside it highlight each other. */
export function XrefProvider({ children, onOpen }: { children: ReactNode; onOpen?: (n: number) => void }) {
  const [active, setActive] = useState<number | null>(null)
  const [opened, setOpened] = useState<{ n: number; t: number } | null>(null)
  const value = useMemo(() => ({
    active, setActive, opened,
    open: (n: number) => { onOpen?.(n); setOpened({ n, t: Date.now() }) },
  }), [active, opened, onOpen])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

/** Ink colour per doc type: the coloured edge-tab of the index card. */
export const DOC_INK: Record<string, string> = {
  mitre_attack: 'bg-cobalt text-card',
  owasp_llm: 'bg-ochre-fill text-[rgb(24_25_26)]',
  cve: 'bg-verm text-card',
  custom: 'bg-green text-card',
}
export const docInk = (docType: string) => DOC_INK[docType] ?? DOC_INK.custom

const SEVERITY: Record<string, string> = {
  critical: 'bg-verm border-verm text-card', high: 'border-verm text-verm',
  medium: 'border-ochre text-ochre', low: 'border-green text-green',
}

const CITE = /\[Source:\s*([^\]]+?)\]/g

/** Index (1-based) of the source a citation refers to, matched by ID first, then by source title. */
export function resolveCitation(body: string, sources: SourceDoc[]): number {
  const [title, id] = body.split('·').map(s => s.trim())
  const byId = id ? sources.findIndex(s => s.ref_id && s.ref_id.toLowerCase() === id.toLowerCase()) : -1
  if (byId >= 0) return byId + 1
  const byTitle = sources.findIndex(s => s.source.toLowerCase() === (title ?? '').toLowerCase())
  return byTitle + 1
}

function CrossRef({ n, label, docType }: { n: number; label: string; docType?: string }) {
  const { active, setActive, open } = useXref()
  if (n === 0) return <span className="font-mono text-[0.85em] text-ink-3">[{label}]</span>
  return (
    <button type="button" title={`Source S-${n}: ${label}`} aria-label={`Show source S-${n}, ${label}`}
      onMouseEnter={() => setActive(n)} onMouseLeave={() => setActive(null)}
      onFocus={() => setActive(n)} onBlur={() => setActive(null)} onClick={() => open(n)}
      className={cn('chip-ref mx-0.5', docInk(docType ?? 'custom'), active === n && '-translate-y-0.5 ring-2 ring-offset-1 ring-ink/70 ring-offset-card')}>
      S-{n}<span className="font-normal opacity-80">{label.split('·').pop()?.trim()}</span>
    </button>
  )
}

const PROSE = cn(
  'prose prose-sm max-w-none text-ink prose-headings:text-ink prose-headings:font-extrabold prose-strong:text-ink',
  'prose-p:leading-relaxed prose-li:my-0.5 prose-a:text-cobalt prose-code:text-ink prose-code:font-mono',
  'prose-code:before:content-none prose-code:after:content-none prose-pre:bg-ground prose-pre:text-ink',
  'prose-pre:border prose-pre:border-rule prose-pre:rounded-none prose-th:text-ink prose-td:text-ink-2',
  'prose-hr:border-rule prose-blockquote:border-l prose-blockquote:border-rule-strong prose-blockquote:text-ink-2',
  'prose-headings:[font-variation-settings:"wdth"_80] prose-h2:text-lg prose-h3:text-base',
)

/** Markdown with citation markers turned into live cross-reference chips. */
export function CitedMarkdown({ content, sources, className }: { content: string; sources: SourceDoc[]; className?: string }) {
  const linked = content.replace(CITE, (_, body: string) => {
    const n = resolveCitation(body, sources)
    return `[${body.replace(/[[\]]/g, '')}](#xref-${n})`
  })
  return (
    <div className={cn(PROSE, className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
        strong: ({ children }) => {
          const word = String(children).trim().toLowerCase()
          const stamp = SEVERITY[word]
          return stamp
            ? <strong className={cn('inline-block font-extrabold uppercase tracking-[0.08em] text-[0.78em] px-1.5 py-px border-2 align-[1px]', stamp)}>{children}</strong>
            : <strong>{children}</strong>
        },
        a: ({ href, children }) => {
          const m = href?.match(/^#xref-(\d+)$/)
          if (!m) return <a href={href} target="_blank" rel="noreferrer">{children}</a>
          const n = Number(m[1])
          return <CrossRef n={n} label={String(children)} docType={sources[n - 1]?.doc_type} />
        },
      }}>{linked}</ReactMarkdown>
    </div>
  )
}
