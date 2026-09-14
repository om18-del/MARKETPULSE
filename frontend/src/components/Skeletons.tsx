export function CardSkeleton({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} />
}

export function GridSkeleton({ count = 8, height = 140 }: { count?: number; height?: number }) {
  return (
    <div className="grid cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} height={height} />
      ))}
    </div>
  )
}

export function LineSkeleton({ height = 16 }: { height?: number }) {
  return <div className="skeleton" style={{ height, marginBottom: 10 }} />
}

export function PageSkeleton() {
  return (
    <div>
      <div className="skeleton" style={{ height: 220, marginBottom: 16 }} />
      <GridSkeleton />
    </div>
  )
}
