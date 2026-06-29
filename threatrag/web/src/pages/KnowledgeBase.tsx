import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { UploadCloud, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getIngestStats, getIngestStatus, ingestMITRE, ingestOWASP, ingestPDF } from '../lib/api'
import type { IngestStatus } from '../lib/api'

interface JobCard {
  job_id: string
  label: string
  status: IngestStatus | null
}

export default function KnowledgeBase() {
  const [jobs, setJobs] = useState<JobCard[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['ingest-stats'],
    queryFn: getIngestStats,
    refetchInterval: 5_000,
  })

  const addJob = (job_id: string, label: string) =>
    setJobs(prev => [...prev, { job_id, label, status: null }])

  useEffect(() => {
    intervalRef.current = setInterval(async () => {
      setJobs(prev => prev.map(j => ({ ...j })))
      for (const job of jobs) {
        if (job.status?.status === 'completed' || job.status?.status === 'failed') continue
        try {
          const s = await getIngestStatus(job.job_id)
          setJobs(prev => prev.map(j => j.job_id === job.job_id ? { ...j, status: s } : j))
          if (s.status === 'completed') refetchStats()
        } catch {}
      }
    }, 2_000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [jobs, refetchStats])

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (!file || !file.name.endsWith('.pdf')) return
    const { job_id } = await ingestPDF(file, 'custom')
    addJob(job_id, file.name)
  }, [])

  const chartData = stats
    ? Object.entries(stats.doc_type_counts).map(([k, v]) => ({ name: k.replace('_', ' '), count: v }))
    : []

  return (
    <div className="p-6 grid grid-cols-2 gap-6 max-w-5xl">
      {/* Left: upload */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Ingest Data Sources</h2>

        {/* Dropzone */}
        <div onDrop={onDrop} onDragOver={e => e.preventDefault()}
          className="border-2 border-dashed border-gray-700 rounded-xl p-8 text-center hover:border-blue-500 transition-colors cursor-pointer">
          <UploadCloud className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-400">Drop a PDF here to ingest</p>
        </div>

        <div className="flex gap-2">
          <button onClick={async () => { const { job_id } = await ingestMITRE(); addJob(job_id, 'MITRE ATT&CK') }}
            className="flex-1 bg-purple-700 hover:bg-purple-600 text-white text-sm py-2 rounded-lg">
            Ingest MITRE ATT&CK
          </button>
          <button onClick={async () => { const { job_id } = await ingestOWASP(); addJob(job_id, 'OWASP LLM Top 10') }}
            className="flex-1 bg-orange-700 hover:bg-orange-600 text-white text-sm py-2 rounded-lg">
            Ingest OWASP LLM
          </button>
        </div>

        {/* Job progress cards */}
        <div className="space-y-2">
          {jobs.map(j => <JobProgressCard key={j.job_id} label={j.label} status={j.status} />)}
        </div>
      </div>

      {/* Right: stats */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Knowledge Base Stats</h2>
        {stats && (
          <>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <p className="text-4xl font-bold text-blue-400">{stats.total_vectors.toLocaleString()}</p>
              <p className="text-sm text-gray-400 mt-1">Total vectors in {stats.collection}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-3">Vectors by source</p>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="#6b7280" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#6b7280" />
                  <Tooltip contentStyle={{ background: '#1f2937', border: 'none' }} />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function JobProgressCard({ label, status }: { label: string; status: IngestStatus | null }) {
  const pct = status && status.total_chunks > 0
    ? Math.round((status.chunks_processed / status.total_chunks) * 100) : 0

  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-gray-200">{label}</span>
        {!status && <Loader2 size={14} className="animate-spin text-blue-400" />}
        {status?.status === 'completed' && <CheckCircle2 size={14} className="text-green-400" />}
        {status?.status === 'failed' && <XCircle size={14} className="text-red-400" />}
        {status?.status === 'processing' && <Loader2 size={14} className="animate-spin text-blue-400" />}
      </div>
      <div className="w-full h-1.5 bg-gray-700 rounded-full">
        <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${pct || (status ? 100 : 0)}%` }} />
      </div>
      {status?.error && <p className="text-xs text-red-400 mt-1">{status.error}</p>}
    </div>
  )
}
