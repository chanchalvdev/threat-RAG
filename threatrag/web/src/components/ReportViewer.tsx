import { useState } from 'react'
import { Copy, Check, Printer, Download } from 'lucide-react'
import { cn } from '../lib/cn'
import { CitedMarkdown, XrefProvider } from '../lib/xref'
import { downloadStix, type SourceDoc } from '../lib/api'
import SourceCard from './SourceCard'

interface Props {
  reportChunks: string[]
  isStreaming: boolean
  sources: SourceDoc[]
  reportId?: string | null
  iterations?: number
  ioc?: string
}

export const reportSerial = (id: string) => 'R-' + id.replace(/-/g, '').slice(0, 6).toUpperCase()

/** The assessment card and its source tray; citations in the text light the cards in the tray. */
export default function ReportViewer({ reportChunks, isStreaming, sources, reportId, iterations, ioc }: Props) {
  const content = reportChunks.join('')
  // The Reporter opens with "# Threat Intelligence Report: <ioc>"; lift that line into the card's headline.
  const h1 = content.match(/^\s*#\s+(.+)\n/)
  const headline = h1 ? h1[1].trim() : ioc
  const body = h1 ? content.slice(h1[0].length) : content
  const [copied, setCopied] = useState(false)
  const [stixError, setStixError] = useState(false)
  const done = !isStreaming

  const copyMd = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <XrefProvider>
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_22rem] gap-6 items-start">
        <article className="card mt-[13px] px-5 md:px-8 py-6">
          <span aria-hidden className="tab bg-ochre-fill" />
          <div className="flex flex-wrap items-center gap-3 pb-3 mb-5 border-b border-rule">
            <span className="font-mono text-xs font-bold text-ink-2">{reportId ? reportSerial(reportId) : 'R-draft'}</span>
            <div className="no-print flex flex-wrap gap-2 ml-auto">
              <button type="button" onClick={copyMd} disabled={!content} className="btn-line text-xs">
                {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}{copied ? 'Copied' : 'Copy Markdown'}
              </button>
              <button type="button" onClick={() => window.print()} disabled={!done} className="btn-line text-xs">
                <Printer size={13} /> Export PDF
              </button>
              {reportId && (
                <button type="button" className="btn-line text-xs"
                  onClick={() => { setStixError(false); downloadStix(reportId).catch(() => setStixError(true)) }}>
                  <Download size={13} /> Export STIX 2.1
                </button>
              )}
            </div>
          </div>
          {headline && (
            <div className="mb-6">
              <h2 className="display text-2xl md:text-3xl [font-variation-settings:'wdth'_80] text-ink">{headline}</h2>
              <p className="text-sm text-ink-2 mt-1.5">
                {isStreaming ? <span className="text-ochre font-semibold">The Reporter is writing</span> : 'Assessment filed'}
                {iterations ? ` · ${iterations} research pass${iterations > 1 ? 'es' : ''}` : ''}
                {done ? ` · ${sources.length} cross-reference${sources.length === 1 ? '' : 's'}` : ''}
              </p>
            </div>
          )}
          {stixError && <p role="alert" className="text-xs text-verm mb-3">STIX export failed. The report may not have been saved; try again in a moment.</p>}
          <CitedMarkdown content={body} sources={sources} className={cn('prose-base max-w-[72ch]', isStreaming && '[&>*:last-child]:typing')} />
          {done && (
            <p className="mt-6 pt-3 border-t border-rule text-xs text-ink-3">
              {reportId ? `Saved as ${reportSerial(reportId)}` : 'Not saved: report storage is unavailable'}
            </p>
          )}
        </article>

        <aside aria-label="Cross-references" className="xl:sticky xl:top-6">
          <h2 className="label mb-1">Cross-references{sources.length ? ` · ${sources.length}` : ''}</h2>
          {sources.length === 0 ? (
            <p className="text-sm text-ink-3 border-t border-rule pt-3 mt-2">
              {isStreaming ? 'Source cards are filed when the report is complete.' : 'No knowledge base passages were cited.'}
            </p>
          ) : (
            <div className="grid gap-3">
              {sources.map((s, i) => <SourceCard key={i} source={s} index={i + 1} />)}
            </div>
          )}
        </aside>
      </div>
    </XrefProvider>
  )
}
