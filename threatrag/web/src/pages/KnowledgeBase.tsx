import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileUp, Check, X, Swords, ShieldAlert } from 'lucide-react'
import { cn } from '../lib/cn'
import { getIngestStats, getIngestStatus, ingestMITRE, ingestOWASP, ingestPDF } from '../lib/api'
import type { IngestStatus } from '../lib/api'
import IndexStats from '../components/IndexStats'

interface JobCard {
  job_id: string
  label: string
  status: IngestStatus | null
}

export default function KnowledgeBase() {
  const [jobs, setJobs] = useState<JobCard[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['ingest-stats'],
    queryFn: getIngestStats,
    refetchInterval: 5_000,
  })

  const addJob = (job_id: string, label: string) => setJobs(prev => [...prev, { job_id, label, status: null }])
  const run = async (label: string, fn: () => Promise<{ job_id: string }>) => {
    setFailure(null)
    try { addJob((await fn()).job_id, label) } catch { setFailure(`Could not start ${label}: the ingest API did not accept the job.`) }
  }

  useEffect(() => {
    const id = setInterval(async () => {
      for (const job of jobs) {
        if (job.status?.status === 'completed' || job.status?.status === 'failed') continue
        try {
          const s = await getIngestStatus(job.job_id)
          setJobs(prev => prev.map(j => j.job_id === job.job_id ? { ...j, status: s } : j))
          if (s.status === 'completed') refetchStats()
        } catch {
          // transient poll failure: retry on the next tick
        }
      }
    }, 2_000)
    return () => clearInterval(id)
  }, [jobs, refetchStats])

  const uploadPDF = (file: File | undefined) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) { setFailure(`${file.name} is not a PDF. Only PDF reports can be filed.`); return }
    run(file.name, () => ingestPDF(file, 'custom'))
  }

  return (
    <div className="px-4 md:px-8 pt-8 md:pt-10 pb-16 max-w-[90rem] mx-auto">
      <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-rule-strong pb-4 mb-8">
        <h1 className="display text-4xl md:text-5xl">Knowledge base</h1>
        <p className="text-sm text-ink-3">Qdrant vector store</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-8 items-start">
        <section aria-labelledby="ingest-h" className="space-y-5">
          <h2 id="ingest-h" className="label">File new sources</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button type="button" onClick={() => run('MITRE ATT&CK', ingestMITRE)} className="btn-line justify-start py-3 px-4 text-sm">
              <Swords size={16} strokeWidth={1.75} className="text-cobalt" /> Load MITRE ATT&amp;CK
            </button>
            <button type="button" onClick={() => run('OWASP LLM Top 10', ingestOWASP)} className="btn-line justify-start py-3 px-4 text-sm">
              <ShieldAlert size={16} strokeWidth={1.75} className="text-ochre" /> Load OWASP LLM Top 10
            </button>
          </div>

          <button type="button" onClick={() => fileRef.current?.click()}
            onDrop={e => { e.preventDefault(); setDragOver(false); uploadPDF(e.dataTransfer.files[0]) }}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            className={cn('w-full border border-dashed px-6 py-9 text-center transition-colors duration-150',
              dragOver ? 'border-act bg-card' : 'border-ink-3/60 hover:border-ink hover:bg-card/60')}>
            <FileUp className={cn('mx-auto mb-3', dragOver ? 'text-act' : 'text-ink-3')} size={26} strokeWidth={1.5} />
            <span className="block text-[15px] font-semibold text-ink">Drop a PDF report, or choose a file</span>
            <span className="block text-xs text-ink-3 mt-1">Filed as custom threat intel and cited like any other source</span>
          </button>
          <input ref={fileRef} type="file" accept=".pdf" className="hidden" aria-label="Choose a PDF"
            onChange={e => { uploadPDF(e.target.files?.[0]); e.target.value = '' }} />

          {failure && <p role="alert" className="text-sm text-verm font-medium">{failure}</p>}

          {jobs.length > 0 && (
            <div>
              <h3 className="label mb-1">Ingestion jobs</h3>
              <ul className="border-t border-rule-strong divide-y divide-rule">
                {jobs.map(j => <JobRow key={j.job_id} label={j.label} status={j.status} />)}
              </ul>
            </div>
          )}
        </section>

        <section aria-labelledby="index-h">
          <h2 id="index-h" className="label">The index</h2>
          <IndexStats stats={stats} />
        </section>
      </div>
    </div>
  )
}

function JobRow({ label, status }: { label: string; status: IngestStatus | null }) {
  const pct = status && status.total_chunks > 0 ? Math.round((status.chunks_processed / status.total_chunks) * 100) : 0
  const active = !status || status.status === 'pending' || status.status === 'processing'
  const failed = status?.status === 'failed'
  const done = status?.status === 'completed'

  return (
    <li className="py-3 animate-file-in">
      <div className="flex items-center gap-3 mb-2 text-sm">
        <span className="text-ink truncate flex-1">{label}</span>
        <span className={cn('font-mono text-xs', failed ? 'text-verm' : done ? 'text-green' : 'text-ink-2')}>
          {failed ? 'failed' : done ? 'filed' : status && status.total_chunks > 0 ? `${status.chunks_processed}/${status.total_chunks}` : 'queued'}
        </span>
        {done && <Check size={14} className="text-green" />}
        {failed && <X size={14} className="text-verm" />}
      </div>
      <div className="h-[3px] bg-rule relative overflow-hidden">
        {active && pct === 0
          ? <span className="absolute inset-y-0 w-1/3 bg-cobalt animate-rule-run" />
          : <span className={cn('block h-full transition-[width] duration-500 ease-expo', failed ? 'bg-verm' : done ? 'bg-green' : 'bg-cobalt')}
              style={{ width: `${done ? 100 : pct}%` }} />}
      </div>
      {status?.error && <p className="text-xs text-verm mt-1.5">{status.error}</p>}
    </li>
  )
}
