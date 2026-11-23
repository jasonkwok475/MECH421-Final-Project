import type { AScan, AScanOptions } from '../types'
import { LineChart, type VMarker } from './LineChart'

interface Props {
  ascan: AScan | null
  options: AScanOptions
  onOptions: (o: AScanOptions) => void
}

export function AScanPanel({ ascan, options, onOptions }: Props) {
  const set = <K extends keyof AScanOptions>(k: K, v: AScanOptions[K]) => onOptions({ ...options, [k]: v })
  const p = ascan?.picks
  const markers: VMarker[] = []
  if (ascan && p) {
    const toRange = (ns: number) => (ns * 1e-9 * 299792458) / 2
    markers.push({ x: toRange(p.surface_ns), label: 'surface', color: '#1c7ed6' })
    if (p.bottom_ns !== null) markers.push({ x: toRange(p.bottom_ns), label: 'bottom', color: '#2f9e44' })
  }

  return (
    <section className="panel plot">
      <div className="row spread">
        <h2>Time domain (A-scan)</h2>
        <span className={`tag ${ascan?.background_subtracted ? 'ok' : 'warn'}`}>
          {ascan?.background_subtracted ? 'background subtracted' : 'raw (no background)'}
        </span>
      </div>
      <div className="options">
        <label>
          Trace
          <select value={options.param} onChange={(e) => set('param', e.target.value as AScanOptions['param'])}>
            <option value="s11">S11 (one antenna)</option>
            <option value="s21">S21 (two antennas)</option>
          </select>
        </label>
        <label>
          Window
          <select value={options.window} onChange={(e) => set('window', e.target.value as AScanOptions['window'])}>
            <option value="hann">Hann</option>
            <option value="hamming">Hamming</option>
            <option value="blackman">Blackman</option>
            <option value="rect">None</option>
          </select>
        </label>
        <label>
          Gate [ns]
          <input type="number" step={0.1} min={0} value={options.gate_ns} onChange={(e) => set('gate_ns', +e.target.value)} />
        </label>
        <label>
          <span>ε<sub>r</sub> (if no plate)</span>
          <input type="number" step={0.05} min={1.01} value={options.eps_r} onChange={(e) => set('eps_r', +e.target.value)} />
        </label>
        <label>
          Range [m]
          <input type="number" step={0.5} min={0.5} value={options.max_range_m} onChange={(e) => set('max_range_m', +e.target.value)} />
        </label>
        <label className="check">
          <input type="checkbox" checked={options.subtract_background} onChange={(e) => set('subtract_background', e.target.checked)} />
          Subtract background
        </label>
        <label className="check">
          <input type="checkbox" checked={options.use_plate_for_eps} onChange={(e) => set('use_plate_for_eps', e.target.checked)} />
          ε from plate
        </label>
      </div>
      {ascan ? (
        <LineChart
          series={[{ name: options.param.toUpperCase(), x: ascan.range_m, y: ascan.mag_db, color: '#d9480f' }]}
          xLabel="Distance in air (one-way) [m]"
          yLabel="Echo [dB]"
          markers={markers}
          formatX={(v) => v.toFixed(2)}
          formatY={(v) => v.toFixed(0)}
        />
      ) : (
        <p className="hint">No A-scan yet.</p>
      )}
      {p && (
        <div className="readouts">
          <div><span>Surface</span><b>{p.surface_ns.toFixed(2)} ns</b></div>
          <div><span>Bottom</span><b>{p.bottom_ns !== null ? `${p.bottom_ns.toFixed(2)} ns` : '—'}</b></div>
          <div><span>Δt</span><b>{p.delay_ns !== null ? `${p.delay_ns.toFixed(2)} ns` : '—'}</b></div>
          <div><span>ε<sub>r</sub> ({p.eps_source})</span><b>{p.eps_r.toFixed(2)}</b></div>
          <div className="big"><span>Ice thickness</span><b>{p.thickness_m !== null ? `${(p.thickness_m * 100).toFixed(1)} cm` : '—'}</b></div>
        </div>
      )}
      {ascan?.warnings.map((w) => <p key={w} className="warning">{w}</p>)}
    </section>
  )
}
