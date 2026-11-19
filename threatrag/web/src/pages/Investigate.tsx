import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { listReports } from '../lib/api'
import { useInvestigation, type IOCType } from '../lib/useInvestigation'
import IocSlip from '../components/IocSlip'
import AgentFile from '../components/AgentFile'
import ReportViewer, { reportSerial } from '../components/ReportViewer'
import SimilarReports from '../components/SimilarReports'
import SendBack from '../components/SendBack'

export default function Investigate() {
  const { nodes, iteration, trail, sendBacks, reportChunks, running, error, result, start } = useInvestigation()
  const [subject, setSubject] = useState<{ ioc: string; type: IOCType } | null>(null)
  const recent = useQuery({ queryKey: ['reports'], queryFn: () => listReports(6), retry: false })

  const { refetch } = recent
  useEffect(() => { if (result) refetch() }, [result, refetch])

  const begin = (ioc: string, type: IOCType) => { setSubject({ ioc, type }); start(ioc, type) }
  const started = subject !== null

  return (
    <div className="px-4 md:px-8 pt-8 md:pt-10 pb-16 max-w-[90rem] mx-auto space-y-8">
      <header className="border-b border-rule-strong pb-4">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <h1 className="display text-4xl md:text-5xl">Investigate an indicator</h1>
          {subject && (
            <p className="serial">
              {result?.report_id ? `File ${reportSerial(result.report_id)}` : 'File open'} · <span className="text-ink">{subject.ioc}</span>
            </p>
          )}
        </div>
        {!started && (
          <p className="text-ink-2 mt-3 max-w-[64ch] leading-relaxed">
            Three agents work the case. The Researcher pulls from the index, NVD and threat feeds; the Critic checks the
            findings and sends gaps back; the Reporter files a cited assessment you can export as STIX 2.1.
          </p>
        )}
      </header>

      <IocSlip running={running} onSubmit={begin} />

      {error && (
        <p role="alert" className="card-quiet flex items-start gap-2.5 px-4 py-3 text-sm text-verm font-medium">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {error}
        </p>
      )}

      {started && <AgentFile nodes={nodes} iteration={iteration} trail={trail} sendBacks={sendBacks} />}

      {reportChunks.length > 0 && (
        <ReportViewer reportChunks={reportChunks} isStreaming={running} sources={result?.sources ?? []}
          reportId={result?.report_id} iterations={result?.iterations} ioc={subject?.ioc} />
      )}

      {result?.report_id && !running && subject && (
        <SendBack key={result.report_id} criticFeedback={result.critic_feedback ?? ''} disabled={running}
          onSend={gaps => start(subject.ioc, subject.type, { gaps, parentId: result.report_id as string })} />
      )}

      <SimilarReports title="Similar past investigations" reports={result?.similar ?? []}
        onPick={running ? undefined : r => begin(r.ioc, r.ioc_type as IOCType)} />
      {!running && !result && (
        <SimilarReports title="Recent investigations" reports={recent.data ?? []} onPick={r => begin(r.ioc, r.ioc_type as IOCType)} />
      )}
    </div>
  )
}
