import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../lib/api'
import { cn } from '../lib/cn'

export default function HealthDot({ className }: { className?: string }) {
  const { data, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  const ok = !isError && data?.status === 'ok'
  return (
    <span className={cn('flex items-center gap-2', className)} role="status">
      <span className={cn('w-2 h-2 rounded-full shrink-0',
        isLoading ? 'bg-rail-ink2' : ok ? 'bg-[#5BB37B]' : 'bg-[#E5573C]')} />
      {isLoading ? 'Checking' : ok ? 'Online' : 'Offline'}
    </span>
  )
}
