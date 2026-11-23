import { useEffect, useState } from 'react'
import { api } from '../api'
import type { PortInfo, Status } from '../types'

interface Props {
  status: Status | null
  onStatus: (s: Status) => void
  onError: (msg: string) => void
}

export function ConnectionPanel({ status, onStatus, onError }: Props) {
  const [ports, setPorts] = useState<PortInfo[]>([])
  const [port, setPort] = useState('')
  const [maxPts, setMaxPts] = useState(101)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    try {
      const p = await api.ports()
      setPorts(p)
      if (!port || !p.some((x) => x.device === port)) setPort(p[0]?.device ?? '')
    } catch (e) {
      onError(`Backend not reachable: ${(e as Error).message}`)
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const run = async (fn: () => Promise<Status>) => {
    setBusy(true)
    try {
      onStatus(await fn())
    } catch (e) {
      onError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const info = status?.info as { version?: string; info?: string[] } | null | undefined

  return (
    <section className="panel">
      <h2>Connection</h2>
      <label>
        Port
        <div className="row">
          <select value={port} onChange={(e) => setPort(e.target.value)} disabled={status?.connected}>
            {ports.map((p) => (
              <option key={p.device} value={p.device}>
                {p.device} {p.likely_nanovna ? '★ NanoVNA' : ''} {p.description && `– ${p.description}`}
              </option>
            ))}
          </select>
          <button className="ghost" onClick={refresh} disabled={status?.connected} title="Rescan ports">↻</button>
        </div>
      </label>
      <label>
        Max points per scan
        <select value={maxPts} onChange={(e) => setMaxPts(+e.target.value)} disabled={status?.connected}>
          <option value={101}>101 (NanoVNA-H)</option>
          <option value={401}>401 (H4, DiSlord firmware)</option>
        </select>
      </label>
      {status?.connected ? (
        <button onClick={() => run(api.disconnect)} disabled={busy}>Disconnect</button>
      ) : (
        <button className="primary" onClick={() => run(() => api.connect(port, maxPts))} disabled={busy || !port}>
          {busy ? 'Connecting…' : 'Connect'}
        </button>
      )}
      <p className={`status ${status?.connected ? 'ok' : ''}`}>
        {status?.connected
          ? `Connected: ${status.port} (${status.kind}) · firmware ${info?.version ?? '?'}`
          : 'Not connected'}
      </p>
    </section>
  )
}
