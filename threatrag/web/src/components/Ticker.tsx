import { useRef } from 'react'

/**
 * A value that updates in place: each character sits in a fixed cell and only the
 * characters that changed re-animate, like a flap on a departure board.
 */
export default function Ticker({ value, className }: { value: string; className?: string }) {
  const prev = useRef(value)
  const version = useRef(0)
  if (prev.current !== value) version.current += 1
  const before = prev.current
  prev.current = value

  return (
    <span className={className}>
      {value.split('').map((ch, i) => {
        const changed = before[i] !== ch && version.current > 0
        return (
          <span key={changed ? `${i}-${version.current}` : i}
            className={changed ? 'inline-block animate-tick' : undefined}>{ch}</span>
        )
      })}
    </span>
  )
}
