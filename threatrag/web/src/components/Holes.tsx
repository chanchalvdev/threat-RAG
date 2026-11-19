import { cn } from '../lib/cn'

/** A row of punched index holes: a fixed five-step magnitude ramp (or a count of passes). */
export default function Holes({ filled, total = 5, label, className }: {
  filled: number
  total?: number
  label?: string
  className?: string
}) {
  return (
    <span className={cn('inline-flex items-center gap-[3px] shrink-0', className)} title={label} aria-label={label} role={label ? 'img' : undefined}>
      {Array.from({ length: total }, (_, i) => (
        <i key={i} className={cn('block w-2 h-2 rounded-full border-[1.5px] border-current transition-colors duration-200',
          i < filled ? 'bg-current' : 'bg-transparent opacity-50')} />
      ))}
    </span>
  )
}

/** Similarity score (0-1) to a 1-5 hole magnitude. */
export const magnitude = (score: number) => Math.max(1, Math.min(5, Math.ceil(score * 5)))
