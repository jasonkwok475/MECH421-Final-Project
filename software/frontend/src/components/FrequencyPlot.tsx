import { useState } from 'react'
import type { Sweep } from '../types'
import { LineChart, type Series } from './LineChart'

type View = 's11_db' | 'swr' | 's21_db'

const VIEWS: Record<View, { label: string; y: string; domain?: [number, number] }> = {
  s11_db: { label: 'S11 [dB]', y: 'S11 [dB]' },
  swr: { label: 'SWR', y: 'SWR', domain: [1, 5] },
  s21_db: { label: 'S21 [dB]', y: 'S21 [dB]' },
}

export function FrequencyPlot({ sweep, background }: { sweep: Sweep | null; background: Sweep | null }) {
  const [view, setView] = useState<View>('s11_db')
  if (!sweep) return <section className="panel plot empty">Run a sweep to see the frequency response.</section>

  const ghz = sweep.freq_hz.map((f) => f / 1e9)
  const series: Series[] = [{ name: 'latest', x: ghz, y: sweep[view], color: '#d9480f' }]
  if (background && background.id !== sweep.id && background.points === sweep.points) {
    series.push({ name: 'background', x: background.freq_hz.map((f) => f / 1e9), y: background[view], color: '#868e96', dashed: true })
  }

  return (
    <section className="panel plot">
      <div className="row spread">
        <h2>Frequency domain</h2>
        <div className="tabs">
          {(Object.keys(VIEWS) as View[]).map((v) => (
            <button key={v} className={view === v ? 'active' : ''} onClick={() => setView(v)}>{VIEWS[v].label}</button>
          ))}
        </div>
      </div>
      <LineChart series={series} xLabel="Frequency [GHz]" yLabel={VIEWS[view].y} yDomain={VIEWS[view].domain}
        formatX={(v) => v.toFixed(2)} formatY={(v) => v.toFixed(view === 'swr' ? 2 : 1)} />
      <p className="hint">
        {sweep.label ?? sweep.source} · {sweep.points} pts · {sweep.timestamp}
        {view === 'swr' && ' · SWR ≤ 2 (≈ −10 dB) is a good antenna match'}
      </p>
    </section>
  )
}
