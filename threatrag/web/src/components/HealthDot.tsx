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
    <span className="flex items-center gap-1.5 text-xs text-gray-400">
      <span className={cn('w-2 h-2 rounded-full', ok ? 'bg-green-500' : 'bg-red-500')} />
      {ok ? 'Online' : 'Offline'}
    </span>
  )
}
