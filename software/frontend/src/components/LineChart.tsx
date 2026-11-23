import { useEffect, useMemo, useRef, useState } from 'react'

export interface Series {
  name: string
  x: number[]
  y: number[]
  color: string
  dashed?: boolean
}

export interface VMarker {
  x: number
  label: string
  color?: string
}

interface Props {
  series: Series[]
  xLabel: string
  yLabel: string
  height?: number
  yDomain?: [number, number]
  xDomain?: [number, number]
  markers?: VMarker[]
  formatX?: (v: number) => string
  formatY?: (v: number) => string
}

const M = { top: 12, right: 16, bottom: 40, left: 56 }

function niceTicks(lo: number, hi: number, count = 6): number[] {
  if (!isFinite(lo) || !isFinite(hi) || hi <= lo) return [lo]
  const raw = (hi - lo) / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw
  const ticks: number[] = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) ticks.push(+v.toPrecision(12))
  return ticks
}

function extent(values: number[]): [number, number] {
  let lo = Infinity
  let hi = -Infinity
  for (const v of values) {
    if (!isFinite(v)) continue
    if (v < lo) lo = v
    if (v > hi) hi = v
  }
  if (lo === hi) return [lo - 1, hi + 1]
  return [lo, hi]
}

const fmt = (v: number) => (Math.abs(v) >= 1000 || (Math.abs(v) < 0.01 && v !== 0) ? v.toExponential(1) : `${+v.toFixed(2)}`)

export function LineChart({
  series, xLabel, yLabel, height = 280, yDomain, xDomain, markers = [], formatX = fmt, formatY = fmt,
}: Props) {
  const wrap = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(640)
  const [hover, setHover] = useState<number | null>(null)

  useEffect(() => {
    if (!wrap.current) return
    const ro = new ResizeObserver((e) => setWidth(Math.max(320, e[0].contentRect.width)))
    ro.observe(wrap.current)
    return () => ro.disconnect()
  }, [])

  const [x0, x1] = useMemo(() => xDomain ?? extent(series.flatMap((s) => s.x)), [series, xDomain])
  const [y0, y1] = useMemo(() => {
    if (yDomain) return yDomain
    const [lo, hi] = extent(series.flatMap((s) => s.y))
    const pad = (hi - lo) * 0.06
    return [lo - pad, hi + pad]
  }, [series, yDomain])

  const w = width - M.left - M.right
  const h = height - M.top - M.bottom
  const sx = (v: number) => M.left + ((v - x0) / (x1 - x0)) * w
  const sy = (v: number) => M.top + (1 - (Math.min(Math.max(v, y0), y1) - y0) / (y1 - y0)) * h

  const paths = series.map((s) => {
    let d = ''
    for (let i = 0; i < s.x.length; i++) {
      if (s.x[i] < x0 || s.x[i] > x1 || !isFinite(s.y[i])) continue
      d += `${d ? 'L' : 'M'}${sx(s.x[i]).toFixed(1)},${sy(s.y[i]).toFixed(1)}`
    }
    return d
  })

  const xt = niceTicks(x0, x1, Math.max(3, Math.floor(w / 90)))
  const yt = niceTicks(y0, y1, Math.max(3, Math.floor(h / 45)))

  const hoverValues =
    hover === null
      ? []
      : series.map((s) => {
          let best = 0
          for (let i = 1; i < s.x.length; i++) if (Math.abs(s.x[i] - hover) < Math.abs(s.x[best] - hover)) best = i
          return { name: s.name, color: s.color, x: s.x[best], y: s.y[best] }
        })

  return (
    <div className="chart" ref={wrap}>
      <svg
        width={width}
        height={height}
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
          const px = e.clientX - r.left
          setHover(px < M.left || px > M.left + w ? null : x0 + ((px - M.left) / w) * (x1 - x0))
        }}
        onMouseLeave={() => setHover(null)}
      >
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line x1={M.left} x2={M.left + w} y1={sy(t)} y2={sy(t)} className="grid" />
            <text x={M.left - 6} y={sy(t) + 4} textAnchor="end" className="tick">{formatY(t)}</text>
          </g>
        ))}
        {xt.map((t) => (
          <g key={`x${t}`}>
            <line x1={sx(t)} x2={sx(t)} y1={M.top} y2={M.top + h} className="grid" />
            <text x={sx(t)} y={M.top + h + 16} textAnchor="middle" className="tick">{formatX(t)}</text>
          </g>
        ))}
        <rect x={M.left} y={M.top} width={w} height={h} className="frame" />
        <text x={M.left + w / 2} y={height - 6} textAnchor="middle" className="axis-label">{xLabel}</text>
        <text transform={`translate(14 ${M.top + h / 2}) rotate(-90)`} textAnchor="middle" className="axis-label">
          {yLabel}
        </text>
        {markers.filter((m) => m.x >= x0 && m.x <= x1).map((m) => (
          <g key={m.label}>
            <line x1={sx(m.x)} x2={sx(m.x)} y1={M.top} y2={M.top + h} stroke={m.color ?? '#1c7ed6'} strokeDasharray="5 4" />
            <text x={sx(m.x) + 4} y={M.top + 14} className="marker-label" fill={m.color ?? '#1c7ed6'}>{m.label}</text>
          </g>
        ))}
        {series.map((s, i) => (
          <path key={s.name} d={paths[i]} fill="none" stroke={s.color} strokeWidth={1.8} strokeDasharray={s.dashed ? '6 4' : undefined} />
        ))}
        {hover !== null && <line x1={sx(hover)} x2={sx(hover)} y1={M.top} y2={M.top + h} className="crosshair" />}
      </svg>
      <div className="legend">
        {series.map((s) => (
          <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>
        ))}
        {hoverValues.length > 0 && (
          <span className="readout">
            {xLabel.split(' [')[0]} = {formatX(hoverValues[0].x)}
            {hoverValues.map((v) => ` · ${v.name}: ${formatY(v.y)}`)}
          </span>
        )}
      </div>
    </div>
  )
}
