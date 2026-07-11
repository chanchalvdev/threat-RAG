import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../lib/api'
import { cn } from '../lib/cn'

export default function HealthDot() {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  const ok = !isError && data?.status === 'ok'
  return (
    <span className="flex items-center gap-2 text-xs text-slate-400">
      <span className="relative flex h-2 w-2">
        {ok && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-40" />}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', ok ? 'bg-emerald-400' : 'bg-red-500')} />
      </span>
      {ok ? 'Online' : 'Offline'}
    </span>
  )
}
