export interface PortInfo {
  device: string
  description: string
  hwid: string
  likely_nanovna: boolean
}

export interface SweepSettings {
  start_hz: number
  stop_hz: number
  points: number
  averages: number
}

export interface SweepSummary {
  id: string
  timestamp: string
  source: string
  label: string | null
  settings: SweepSettings
  points: number
}

export interface Sweep extends SweepSummary {
  freq_hz: number[]
  s11: { re: number[]; im: number[] }
  s21: { re: number[]; im: number[] }
  s11_db: number[]
  s21_db: number[]
  swr: number[]
}

export interface Status {
  connected: boolean
  port: string | null
  kind: string | null
  info: Record<string, unknown> | null
  references: Partial<Record<RefKind, SweepSummary>>
  sweep_count: number
  data_dir: string
}

export type RefKind = 'background' | 'plate'

export interface Picks {
  surface_ns: number
  bottom_ns: number | null
  surface_db: number
  bottom_db: number | null
  delay_ns: number | null
  thickness_m: number | null
  eps_r: number
  eps_source: 'assumed' | 'plate'
}

export interface AScanOptions {
  param: 's11' | 's21'
  subtract_background: boolean
  use_plate_for_eps: boolean
  window: 'hann' | 'hamming' | 'blackman' | 'rect'
  gate_ns: number
  eps_r: number
  max_range_m: number
  min_sep_ns: number
}

export interface AScan {
  sweep_id: string
  t_ns: number[]
  range_m: number[]
  mag_db: number[]
  picks: Picks | null
  warnings: string[]
  background_subtracted: boolean
}

export interface Measurement {
  name: string
  file: string
  timestamp: string | null
  notes: string
  points: number | null
}

export type SceneKind = 'sky' | 'plate' | 'ice'

export interface MockScene {
  kind: SceneKind
  distance_m: number
  ice_thickness_m: number
  eps_ice: number
  noise: number
}
