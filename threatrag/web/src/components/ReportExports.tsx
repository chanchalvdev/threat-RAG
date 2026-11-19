import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, FileText, Printer, Send } from 'lucide-react'
import { downloadStix } from '../lib/api'
import { downloadPdf, getExportOptions, notifyChannel, type Channel } from '../lib/exports'

interface Props { reportId?: string | null; serial: string; done: boolean }

const CHANNEL_NAMES: Record<Channel, string> = { slack: 'Slack', teams: 'Teams' }

/** STIX, PDF and channel posts for a saved report; an unsaved draft can still be printed. */
export default function ReportExports({ reportId, serial, done }: Props) {
  const options = useQuery({ queryKey: ['export-options'], queryFn: getExportOptions, retry: false, staleTime: 60_000 })
  const [note, setNote] = useState<{ text: string; failed: boolean } | null>(null)

  const run = (ok: string, failed: string, work: () => Promise<unknown>) => {
    setNote(null)
    work().then(() => setNote({ text: ok, failed: false })).catch(() => setNote({ text: failed, failed: true }))
  }

  if (!reportId) {
    return (
      <button type="button" onClick={() => window.print()} disabled={!done} className="btn-line text-xs">
        <Printer size={13} /> Print
      </button>
    )
  }
  const channels = (['slack', 'teams'] as const).filter(c => options.data?.[c])
  return (
    <>
      <button type="button" className="btn-line text-xs" onClick={() => run('PDF downloaded', 'PDF export failed. Try again in a moment.', () => downloadPdf(reportId, `threatrag-${serial}.pdf`))}>
        <FileText size={13} /> Export PDF
      </button>
      <button type="button" className="btn-line text-xs" onClick={() => run('STIX downloaded', 'STIX export failed. Try again in a moment.', () => downloadStix(reportId))}>
        <Download size={13} /> Export STIX 2.1
      </button>
      {channels.map(c => (
        <button key={c} type="button" className="btn-line text-xs" onClick={() => run(`Posted to ${CHANNEL_NAMES[c]}`, `${CHANNEL_NAMES[c]} did not accept the message.`, () => notifyChannel(reportId, c))}>
          <Send size={13} /> Send to {CHANNEL_NAMES[c]}
        </button>
      ))}
      {note && <span role={note.failed ? 'alert' : 'status'} className={note.failed ? 'basis-full text-xs text-verm' : 'basis-full text-xs text-green'}>{note.text}</span>}
    </>
  )
}
