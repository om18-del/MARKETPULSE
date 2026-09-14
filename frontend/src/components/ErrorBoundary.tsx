import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Accessible label used in logs and the fallback card. */
  name?: string
}

interface State {
  error: Error | null
}

/**
 * Keeps a crashing child (e.g. a chart hitting a bad data shape) from
 * unmounting the whole app — the rest of the page stays usable and the
 * failure is contained to a visible card instead of a blank screen.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    console.error(`[${this.props.name ?? 'ErrorBoundary'}]`, error, info?.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card" style={{ padding: 16 }}>
          <div className="card-title">This panel couldn't render</div>
          <p className="muted" style={{ margin: '6px 0 10px' }}>
            {this.props.name ?? 'Panel'} failed: {this.state.error.message}
          </p>
          <button className="btn ghost" onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
