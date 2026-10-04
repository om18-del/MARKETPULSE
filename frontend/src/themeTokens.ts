/**
 * lightweight-charts needs literal color strings, so it cannot consume CSS
 * `var(--token)` references the way the rest of the app does. This resolves
 * the design tokens off the live element so charts stay in sync with the
 * active theme instead of hardcoding a palette that drifts out of date.
 */

function read(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/** Chart chrome: axis text, gridlines, scale borders. */
export function chartChrome() {
  return {
    text: read('--text-faint', '#7f9188'),
    grid: read('--chart-grid', 'rgba(226,244,234,0.075)'),
    border: read('--chart-border', 'rgba(226,244,234,0.14)'),
    font: read('--font-num', "'DM Mono', monospace"),
  }
}

/** Rising/falling series colors plus a transparent fade for the area fill. */
export function seriesColors(rising: boolean) {
  const pos = read('--pos', '#73e5ad')
  const neg = read('--neg', '#ff8582')
  const hex = rising ? pos : neg
  return {
    line: hex,
    top: withAlpha(hex, 0.3),
    bottom: withAlpha(hex, 0),
  }
}

/**
 * Distinct-but-related hues for the Compare page's multi-series lines.
 * Warm spread so the series never collide with the terracotta accent.
 */
export const COMPARE_SERIES = ['--series-1', '--series-2', '--series-3', '--series-4'] as const

export function compareSeriesColors(): string[] {
  return COMPARE_SERIES.map(
    (token, i) => read(token, ['#82e6b4', '#73e5ad', '#f2c66d', '#ad9cff'][i]),
  )
}

/** #rrggbb -> rgba() with the given alpha. Passes through non-hex values. */
function withAlpha(color: string, alpha: number): string {
  const m = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i)
  if (!m) return color
  let hex = m[1]
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('')
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}