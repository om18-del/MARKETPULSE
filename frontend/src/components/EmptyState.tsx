import type { ReactNode } from 'react'

/**
 * A deliberate nothing-here state. Bare muted text reads as a bug; this gives
 * the user an icon, a reason, and — where it makes sense — a way forward.
 */
export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      {icon ? (
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <h3 className="empty-state-title">{title}</h3>
      {children ? <p className="empty-state-text">{children}</p> : null}
      {action}
    </div>
  )
}