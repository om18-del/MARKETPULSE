import type { IChartApi } from 'lightweight-charts'

/**
 * Stop the user zooming out past the data.
 *
 * lightweight-charts allows `minBarSpacing` down to 0 by default, so a scroll
 * or pinch gesture can shrink the series to a sliver and leave most of the
 * canvas empty. The floor we want is simply "the spacing at which every bar
 * fits across the pane" — i.e. fitContent(). So we measure that spacing and
 * use it as the minimum.
 *
 * Recomputed on resize because `autoSize` means the pane width is not known
 * until the chart has laid out.
 */
export function clampZoomToData(
  chart: IChartApi,
  barCount: number,
  paneWidth?: number,
): void {
  if (barCount < 2) return
  const ts = chart.timeScale()
  const width = paneWidth ?? chart.paneSize().width
  if (!width) return

  // Spacing when the whole series is visible. A hair under 1.0 factor keeps
  // the last bar off the right-hand price scale edge.
  const fitSpacing = (width * 0.92) / barCount
  // Never go below 0.5 — that is the library floor and still legible.
  const minBarSpacing = Math.max(0.5, fitSpacing)

  ts.applyOptions({ minBarSpacing })

  // fitContent may now exceed the new floor after a resize; re-apply so the
  // view never starts out violating the clamp we just set.
  const spacing = ts.options().barSpacing
  if (spacing < minBarSpacing) ts.applyOptions({ barSpacing: minBarSpacing })
}