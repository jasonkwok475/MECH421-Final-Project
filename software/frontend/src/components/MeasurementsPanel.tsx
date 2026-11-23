import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Measurement, Sweep } from '../types'

interface Props {
  sweep: Sweep | null
  onLoaded: (s: Sweep) => void
  onError: (m: string) => void
  onInfo: (m: string) => void
}

export function MeasurementsPanel({ sweep, onLoaded, onError, onInfo }: Props) {
  const [items, setItems] = useState<Measurement[]>([])
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')

  const refresh = () => api.measurements().then(setItems).catch(() => {})
  useEffect(() => {
    refresh()
  }, [])

  const save = async () => {
    if (!sweep) return
    try {
      const r = await api.save(name, sweep.id, notes)
      onInfo(`Saved ${r.path}`)
      setName('')
      setNotes('')
      refresh()
    } catch (e) {
      onError((e as Error).message)
    }
  }

  const load = async (n: string) => {
    try {
      onLoaded(await api.load(n))
    } catch (e) {
      onError((e as Error).message)
    }
  }

  return (
    <section className="panel">
      <h2>Measurements</h2>
      <label>
        Name
        <input value={name} placeholder="e.g. tub_ice_30cm_h40" onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        Notes
        <input value={notes} placeholder="height, ice type, temperature…" onChange={(e) => setNotes(e.target.value)} />
      </label>
      <button onClick={save} disabled={!sweep || !name.trim()}>Save latest sweep (.s2p)</button>
      <ul className="list">
        {items.length === 0 && <li className="hint">No saved measurements yet</li>}
        {items.map((m) => (
          <li key={m.file}>
            <button className="link" onClick={() => load(m.name)} title={m.notes}>{m.name}</button>
            <span className="hint">{m.timestamp?.replace('T', ' ').slice(0, 16)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
