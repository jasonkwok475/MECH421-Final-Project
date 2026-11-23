import { useState } from 'react'
import { api } from '../api'
import type { MockScene, SceneKind } from '../types'

export function MockScenePanel({ onError }: { onError: (m: string) => void }) {
  const [scene, setScene] = useState<MockScene>({
    kind: 'sky', distance_m: 0.5, ice_thickness_m: 0.25, eps_ice: 3.2, noise: 0.002,
  })

  const apply = async (s: MockScene) => {
    setScene(s)
    try {
      await api.mockScene(s)
    } catch (e) {
      onError((e as Error).message)
    }
  }

  return (
    <section className="panel mock">
      <h2>Simulator scene</h2>
      <p className="hint">Only for the "mock" port: choose what the fake antenna is looking at.</p>
      <div className="row">
        {(['sky', 'plate', 'ice'] as SceneKind[]).map((k) => (
          <button key={k} className={scene.kind === k ? 'primary' : ''} onClick={() => apply({ ...scene, kind: k })}>
            {k}
          </button>
        ))}
      </div>
      <div className="grid2">
        <label>
          Distance [m]
          <input type="number" step={0.05} min={0.05} value={scene.distance_m}
            onChange={(e) => apply({ ...scene, distance_m: +e.target.value })} />
        </label>
        <label>
          Ice thickness [m]
          <input type="number" step={0.01} min={0.01} value={scene.ice_thickness_m}
            onChange={(e) => apply({ ...scene, ice_thickness_m: +e.target.value })} />
        </label>
      </div>
    </section>
  )
}
