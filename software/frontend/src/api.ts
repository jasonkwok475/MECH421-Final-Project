import type {
  AScan, AScanOptions, Measurement, MockScene, PortInfo, RefKind, Status, Sweep, SweepSettings,
} from './types'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ ok: boolean }>('GET', '/health'),
  ports: () => request<PortInfo[]>('GET', '/ports'),
  status: () => request<Status>('GET', '/status'),
  connect: (port: string, maxPointsPerScan: number) =>
    request<Status>('POST', '/connect', { port, max_points_per_scan: maxPointsPerScan }),
  disconnect: () => request<Status>('POST', '/disconnect'),
  sweep: (s: SweepSettings) => request<Sweep>('POST', '/sweep', s),
  setReference: (kind: RefKind, sweepId?: string) =>
    request<Status>('POST', `/references/${kind}`, { sweep_id: sweepId ?? null }),
  clearReference: (kind: RefKind) => request<Status>('DELETE', `/references/${kind}`),
  ascan: (sweepId: string, o: AScanOptions) =>
    request<AScan>('POST', '/ascan', { sweep_id: sweepId, ...o }),
  measurements: () => request<Measurement[]>('GET', '/measurements'),
  save: (name: string, sweepId: string, notes: string) =>
    request<{ name: string; path: string }>('POST', '/measurements', { name, sweep_id: sweepId, notes }),
  load: (name: string) => request<Sweep>('POST', `/measurements/${encodeURIComponent(name)}/load`),
  mockScene: (scene: Partial<MockScene>) => request<Record<string, unknown>>('POST', '/mock/scene', scene),
}
