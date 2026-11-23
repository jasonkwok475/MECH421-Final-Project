import type { RefKind, Status } from '../types'

interface Props {
  status: Status | null
  hasSweep: boolean
  onSet: (k: RefKind) => void
  onClear: (k: RefKind) => void
}

const HELP: Record<RefKind, string> = {
  background: 'Antenna pointed at open sky / empty space. Subtracted from every sweep to remove antenna ringing.',
  plate: 'Metal plate where the ice surface will be. Used to measure the ice permittivity from the surface echo.',
}

export function ReferencePanel({ status, hasSweep, onSet, onClear }: Props) {
  return (
    <section className="panel">
      <h2>References</h2>
      {(['background', 'plate'] as RefKind[]).map((k) => {
        const ref = status?.references?.[k]
        return (
          <div key={k} className="ref">
            <div className="row spread">
              <strong>{k === 'background' ? 'Background' : 'Metal plate'}</strong>
              <span className={`tag ${ref ? 'ok' : ''}`}>{ref ? `set · ${ref.points} pts` : 'not set'}</span>
            </div>
            <p className="hint">{HELP[k]}</p>
            <div className="row">
              <button onClick={() => onSet(k)} disabled={!hasSweep}>Use latest sweep</button>
              {ref && <button className="ghost" onClick={() => onClear(k)}>Clear</button>}
            </div>
          </div>
        )
      })}
    </section>
  )
}
