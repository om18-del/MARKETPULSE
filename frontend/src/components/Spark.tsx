export function Spark({ points, width = 110, height = 34 }: { points: number[]; width?: number; height?: number }) {
  if (!points || points.length < 2) return <svg width={width} height={height} />
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  const step = width / (points.length - 1)
  const coords = points.map((p, i) => [i * step, height - 3 - ((p - min) / span) * (height - 8)] as const)
  const d = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const up = points[points.length - 1] >= points[0]
  const color = up ? 'var(--pos)' : 'var(--neg)'
  const gid = `sg${up ? 'u' : 'd'}${Math.abs(points[0] * 1000).toFixed(0)}${points.length}`
  return (
    <svg width={width} height={height} className={up ? 'spark-up' : 'spark-down'} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${width},${height} L0,${height} Z`} fill={`url(#${gid})`} stroke="none" />
      <path d={d} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
