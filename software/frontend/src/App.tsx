import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { AScanPanel } from './components/AScanPanel'
import { ConnectionPanel } from './components/ConnectionPanel'
import { FrequencyPlot } from './components/FrequencyPlot'
import { MeasurementsPanel } from './components/MeasurementsPanel'
import { MockScenePanel } from './components/MockScenePanel'
import { ReferencePanel } from './components/ReferencePanel'
import { SweepPanel } from './components/SweepPanel'
import type { AScan, AScanOptions, RefKind, Status, Sweep, SweepSettings } from './types'

interface LogLine {
  t: string
  kind: 'info' | 'error'
  msg: string
}

const DEFAULT_SWEEP: SweepSettings = { start_hz: 500e6, stop_hz: 1500e6, points: 101, averages: 1 }
const DEFAULT_ASCAN: AScanOptions = {
  param: 's11', subtract_background: true, use_plate_for_eps: true, window: 'hann',
  gate_ns: 0, eps_r: 3.2, max_range_m: 3, min_sep_ns: 0.6,
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [settings, setSettings] = useState(DEFAULT_SWEEP)
  const [sweep, setSweep] = useState<Sweep | null>(null)
  const [background, setBackground] = useState<Sweep | null>(null)
  const [ascanOpts, setAscanOpts] = useState(DEFAULT_ASCAN)
  const [ascan, setAscan] = useState<AScan | null>(null)
  const [busy, setBusy] = useState(false)
  const [continuous, setContinuous] = useState(false)
  const [log, setLog] = useState<LogLine[]>([])
  const continuousRef = useRef(false)

  const push = useCallback((kind: LogLine['kind'], msg: string) => {
    setLog((l) => [{ t: new Date().toLocaleTimeString(), kind, msg }, ...l].slice(0, 50))
  }, [])
  const onError = useCallback((m: string) => push('error', m), [push])
  const onInfo = useCallback((m: string) => push('info', m), [push])

  useEffect(() => {
    api.status().then(setStatus).catch((e) => onError(`Backend not reachable: ${e.message}`))
  }, [onError])

  // Recompute the A-scan whenever the sweep, the options or the references change.
  useEffect(() => {
    if (!sweep) return
    api.ascan(sweep.id, ascanOpts).then(setAscan).catch((e) => onError(`A-scan: ${e.message}`))
  }, [sweep, ascanOpts, status?.references, onError])

  const doSweep = useCallback(async () => {
    setBusy(true)
    try {
      const s = await api.sweep(settings)
      setSweep(s)
      return true
    } catch (e) {
      onError(`Sweep failed: ${(e as Error).message}`)
      return false
    } finally {
      setBusy(false)
    }
  }, [settings, onError])

  useEffect(() => {
    continuousRef.current = continuous
    if (!continuous) return
    let alive = true
    ;(async () => {
      while (alive && continuousRef.current) {
        if (!(await doSweep())) {
          setContinuous(false)
          break
        }
      }
    })()
    return () => {
      alive = false
    }
  }, [continuous, doSweep])

  const setRef = async (kind: RefKind) => {
    if (!sweep) return
    try {
      setStatus(await api.setReference(kind, sweep.id))
      if (kind === 'background') setBackground(sweep)
      onInfo(`${kind} set from sweep ${sweep.id}`)
    } catch (e) {
      onError((e as Error).message)
    }
  }
  const clearRef = async (kind: RefKind) => {
    setStatus(await api.clearReference(kind))
    if (kind === 'background') setBackground(null)
  }

  const connected = !!status?.connected

  return (
    <div className="app">
      <header>
        <h1>MECH 421 Ice Radar</h1>
        <span className="sub">NanoVNA test bench</span>
      </header>
      <aside>
        <ConnectionPanel status={status} onStatus={(s) => { setStatus(s); onInfo(s.connected ? `Connected to ${s.port}` : 'Disconnected') }} onError={onError} />
        {status?.kind === 'mock' && <MockScenePanel onError={onError} />}
        <SweepPanel settings={settings} onChange={setSettings} onSweep={doSweep} continuous={continuous}
          onContinuous={setContinuous} busy={busy} disabled={!connected} />
        <ReferencePanel status={status} hasSweep={!!sweep} onSet={setRef} onClear={clearRef} />
        <MeasurementsPanel sweep={sweep} onLoaded={(s) => { setSweep(s); onInfo(`Loaded ${s.label}`) }} onError={onError} onInfo={onInfo} />
      </aside>
      <main>
        <FrequencyPlot sweep={sweep} background={background} />
        <AScanPanel ascan={ascan} options={ascanOpts} onOptions={setAscanOpts} />
        <section className="panel log">
          <h2>Log</h2>
          {log.length === 0 && <p className="hint">Messages appear here.</p>}
          {log.map((l, i) => (
            <div key={i} className={l.kind}><span>{l.t}</span> {l.msg}</div>
          ))}
        </section>
      </main>
    </div>
  )
}
