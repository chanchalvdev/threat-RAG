import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { UploadCloud, CheckCircle2, XCircle, Loader2, Swords, ShieldAlert, Layers } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { cn } from '../lib/cn'
import { getIngestStats, getIngestStatus, ingestMITRE, ingestOWASP, ingestPDF } from '../lib/api'
import type { IngestStatus } from '../lib/api'

interface JobCard {
  job_id: string
  label: string
  status: IngestStatus | null
}

export default function KnowledgeBase() {
  const [jobs, setJobs] = useState<JobCard[]>([])
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['ingest-stats'],
    queryFn: getIngestStats,
    refetchInterval: 5_000,
  })

  const addJob = (job_id: string, label: string) =>
    setJobs(prev => [...prev, { job_id, label, status: null }])

  useEffect(() => {
    const id = setInterval(async () => {
      for (const job of jobs) {
        if (job.status?.status === 'completed' || job.status?.status === 'failed') continue
        try {
          const s = await getIngestStatus(job.job_id)
          setJobs(prev => prev.map(j => j.job_id === job.job_id ? { ...j, status: s } : j))
          if (s.status === 'completed') refetchStats()
        } catch {}
      }
    }, 2_000)
    return () => clearInterval(id)
  }, [jobs, refetchStats])

  const uploadPDF = async (file: File | undefined) => {
    if (!file || !file.name.endsWith('.pdf')) return
    const { job_id } = await ingestPDF(file, 'custom')
    addJob(job_id, file.name)
  }

  const chartData = stats
    ? Object.entries(stats.doc_type_counts).map(([k, v]) => ({ name: k.replace('_', ' '), count: v }))
    : []

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl mx-auto">
      {/* Left: ingest */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold text-slate-100">Ingest data sources</h2>

        {/* Dropzone (click or drag) */}
        <button
          onClick={() => fileRef.current?.click()}
          onDrop={e => { e.preventDefault(); setDragOver(false); uploadPDF(e.dataTransfer.files[0]) }}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          className={cn('w-full border-2 border-dashed rounded-xl p-8 text-center transition-all',
            dragOver ? 'border-accent bg-accent-faint/20 shadow-glow' : 'border-line hover:border-accent-dim')}>
          <UploadCloud className={cn('mx-auto mb-2 transition-colors', dragOver ? 'text-accent' : 'text-slate-500')} size={28} />
          <p className="text-sm text-slate-300 font-medium">Drop a PDF here, or click to browse</p>
          <p className="text-xs text-slate-500 mt-1">Ingested as custom threat intel</p>
        </button>
        <input ref={fileRef} type="file" accept=".pdf" className="hidden"
          onChange={e => { uploadPDF(e.target.files?.[0]); e.target.value = '' }} />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <button onClick={async () => { const { job_id } = await ingestMITRE(); addJob(job_id, 'MITRE ATT&CK') }}
            className="btn-secondary flex items-center justify-center gap-2 text-sm py-2.5">
            <Swords size={15} className="text-purple-400" /> MITRE ATT&amp;CK
          </button>
          <button onClick={async () => { const { job_id } = await ingestOWASP(); addJob(job_id, 'OWASP LLM Top 10') }}
            className="btn-secondary flex items-center justify-center gap-2 text-sm py-2.5">
            <ShieldAlert size={15} className="text-orange-400" /> OWASP LLM Top 10
          </button>
        </div>

        {jobs.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Ingestion jobs</p>
            {jobs.map(j => <JobProgressCard key={j.job_id} label={j.label} status={j.status} />)}
          </div>
        )}
      </section>

      {/* Right: stats */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold text-slate-100">Knowledge base</h2>
        {stats ? (
          <>
            <div className="card p-6 flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl bg-accent-faint/50 border border-accent-dim/40 flex items-center justify-center">
                <Layers className="text-accent" size={20} />
              </div>
              <div>
                <p className="text-3xl font-bold text-slate-100 font-mono">{stats.total_vectors.toLocaleString()}</p>
                <p className="text-xs text-slate-500 mt-0.5">vectors in <span className="font-mono">{stats.collection}</span></p>
              </div>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Vectors by source</p>
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#697894' }} stroke="#22304F" />
                  <YAxis tick={{ fontSize: 11, fill: '#697894' }} stroke="#22304F" />
                  <Tooltip cursor={{ fill: 'rgba(34,211,238,0.06)' }}
                    contentStyle={{ background: '#111A2C', border: '1px solid #1D2A45', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" fill="#22D3EE" radius={[4, 4, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div className="card p-6 text-sm text-slate-500">Loading stats…</div>
        )}
      </section>
    </div>
  )
}

function JobProgressCard({ label, status }: { label: string; status: IngestStatus | null }) {
  const pct = status && status.total_chunks > 0
    ? Math.round((status.chunks_processed / status.total_chunks) * 100) : 0
  const active = !status || status.status === 'pending' || status.status === 'processing'

  return (
    <div className="card p-3 animate-slide-in">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-slate-200 truncate">{label}</span>
        {active && <Loader2 size={14} className="animate-spin text-accent shrink-0" />}
        {status?.status === 'completed' && <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />}
        {status?.status === 'failed' && <XCircle size={14} className="text-red-400 shrink-0" />}
      </div>
      <div className="w-full h-1.5 bg-surface-600 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-500',
          status?.status === 'failed' ? 'bg-red-500' : status?.status === 'completed' ? 'bg-emerald-400' : 'bg-accent')}
          style={{ width: `${status?.status === 'completed' ? 100 : pct}%` }} />
      </div>
      {status && status.total_chunks > 0 && active && (
        <p className="text-[11px] text-slate-500 mt-1 font-mono">{status.chunks_processed}/{status.total_chunks} chunks</p>
      )}
      {status?.error && <p className="text-xs text-red-400 mt-1.5">{status.error}</p>}
    </div>
  )
}
