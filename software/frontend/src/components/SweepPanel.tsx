import type { SweepSettings } from '../types'

interface Props {
  settings: SweepSettings
  onChange: (s: SweepSettings) => void
  onSweep: () => void
  continuous: boolean
  onContinuous: (v: boolean) => void
  busy: boolean
  disabled: boolean
}

export function SweepPanel({ settings, onChange, onSweep, continuous, onContinuous, busy, disabled }: Props) {
  const set = (k: keyof SweepSettings, v: number) => onChange({ ...settings, [k]: v })
  const df = (settings.stop_hz - settings.start_hz) / Math.max(1, settings.points - 1)
  const bw = settings.stop_hz - settings.start_hz

  return (
    <section className="panel">
      <h2>Sweep</h2>
      <div className="grid2">
        <label>
          Start [MHz]
          <input type="number" value={settings.start_hz / 1e6} min={0.05} step={10}
            onChange={(e) => set('start_hz', +e.target.value * 1e6)} />
        </label>
        <label>
          Stop [MHz]
          <input type="number" value={settings.stop_hz / 1e6} min={1} step={10}
            onChange={(e) => set('stop_hz', +e.target.value * 1e6)} />
        </label>
        <label>
          Points
          <input type="number" value={settings.points} min={11} max={4001} step={10}
            onChange={(e) => set('points', Math.round(+e.target.value))} />
        </label>
        <label>
          Averages
          <input type="number" value={settings.averages} min={1} max={64}
            onChange={(e) => set('averages', Math.round(+e.target.value))} />
        </label>
      </div>
      <p className="hint">
        Step {(df / 1e6).toFixed(1)} MHz → max range {(299.792458 / (2 * df / 1e6)).toFixed(1)} m ·
        resolution in ice ≈ {(299792458 / (2 * bw * Math.sqrt(3.2)) * 100).toFixed(1)} cm
      </p>
      <div className="row">
        <button className="primary" onClick={onSweep} disabled={disabled || busy || continuous}>
          {busy && !continuous ? 'Sweeping…' : 'Single sweep'}
        </button>
        <label className="check">
          <input type="checkbox" checked={continuous} disabled={disabled}
            onChange={(e) => onContinuous(e.target.checked)} />
          Continuous
        </label>
      </div>
    </section>
  )
}
