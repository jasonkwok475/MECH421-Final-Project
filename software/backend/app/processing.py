"""Radar signal processing: frequency-domain sweep -> time-domain A-scan -> echo picks.

Same pipeline as Meng et al. (2025, Water Resources Research):
background subtraction -> window -> inverse FFT -> pick surface / bottom echoes
-> thickness h = c * dt / (2 * sqrt(eps_r)).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks, windows

C0 = 299_792_458.0


def to_db(x: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    return 20 * np.log10(np.maximum(np.abs(x), floor))


def swr(s11: np.ndarray) -> np.ndarray:
    g = np.minimum(np.abs(s11), 0.999)
    return (1 + g) / (1 - g)


def time_domain(freq_hz: np.ndarray, s: np.ndarray, background: np.ndarray | None = None,
                window: str = "hann", pad: int = 16) -> tuple[np.ndarray, np.ndarray]:
    """Band-pass inverse FFT. Returns (t_s, complex trace). Works for any start frequency."""
    x = s - background if background is not None else np.asarray(s, complex)
    n = len(freq_hz)
    if n < 4:
        raise ValueError("Need at least 4 frequency points for a time-domain transform")
    w = windows.get_window(window, n) if window and window != "rect" else np.ones(n)
    df = float(np.mean(np.diff(freq_hz)))
    nfft = int(2 ** np.ceil(np.log2(n * pad)))
    trace = np.fft.ifft(x * w, nfft) * nfft / np.sum(w)
    t = np.arange(nfft) / (nfft * df)  # max unambiguous time = 1/df
    return t, trace


@dataclass
class Picks:
    surface_ns: float
    bottom_ns: float | None
    surface_db: float
    bottom_db: float | None
    delay_ns: float | None
    thickness_m: float | None
    eps_r: float
    eps_source: str  # "assumed" | "plate"


def _refine(t: np.ndarray, env: np.ndarray, i: int) -> tuple[float, float]:
    """Parabolic interpolation of a peak -> sub-sample time and amplitude."""
    if 0 < i < len(env) - 1:
        a, b, c = env[i - 1], env[i], env[i + 1]
        den = a - 2 * b + c
        p = 0.5 * (a - c) / den if den != 0 else 0.0
        return float(t[i] + p * (t[1] - t[0])), float(b - 0.25 * (a - c) * p)
    return float(t[i]), float(env[i])


def pick_echoes(t: np.ndarray, trace: np.ndarray, gate_ns: float = 0.0,
                min_sep_ns: float = 0.6, first_frac: float = 0.25,
                max_ns: float | None = None) -> tuple[tuple[float, float], tuple[float, float] | None]:
    """Surface = FIRST strong peak after the gate; bottom = strongest peak after it.

    The bottom (ice-water) echo is often STRONGER than the surface (air-ice) echo,
    so "biggest peak" is not the surface.
    Returns ((t_surface_s, amp), (t_bottom_s, amp) or None).
    """
    env = np.abs(trace)
    dt = t[1] - t[0]
    lo = int(max(gate_ns, 0) * 1e-9 / dt)
    hi = int(max_ns * 1e-9 / dt) if max_ns else len(env)
    region = env[lo:hi]
    if region.size == 0 or region.max() <= 0:
        raise ValueError("Nothing to pick in the gated window")
    pk, _ = find_peaks(env[:hi], height=0.02 * region.max(), distance=max(1, int(0.2e-9 / dt)))
    pk = pk[pk >= lo]
    if len(pk) == 0:
        raise ValueError("No echoes found after the gate")
    strong = pk[env[pk] >= first_frac * env[pk].max()]
    surf = strong[0]
    later = pk[t[pk] > t[surf] + min_sep_ns * 1e-9]
    bottom = _refine(t, env, later[np.argmax(env[later])]) if len(later) else None
    return _refine(t, env, surf), bottom


def thickness(delay_s: float, eps_r: float) -> float:
    return C0 * delay_s / (2 * np.sqrt(eps_r))


def eps_from_reflection(surface_amp: float, plate_amp: float) -> float:
    """eps_r of the top layer from |R| = surface echo / metal-plate echo at the same height."""
    r = min(abs(surface_amp / plate_amp), 0.95)
    return float(((1 + r) / (1 - r)) ** 2)


def ascan(freq_hz: np.ndarray, s: np.ndarray, background: np.ndarray | None = None,
          plate: np.ndarray | None = None, window: str = "hann", gate_ns: float = 0.0,
          eps_r: float = 3.2, max_range_m: float = 5.0, min_sep_ns: float = 0.6) -> dict:
    """Full A-scan + picks, ready to send to the GUI."""
    t, tr = time_domain(freq_hz, s, background, window)
    keep = t <= 2 * max_range_m / C0
    out: dict = {
        "t_ns": (t[keep] * 1e9).tolist(),
        "range_m": (t[keep] * C0 / 2).tolist(),  # one-way distance in air
        "mag_db": to_db(tr[keep]).tolist(),
        "picks": None,
        "warnings": [],
    }
    if background is None:
        out["warnings"].append("No background subtracted: echoes within ~1 m may be hidden "
                               "by the antenna's own reflection and ringing.")
    try:
        (ts, a_s), bottom = pick_echoes(t, tr, gate_ns=gate_ns, min_sep_ns=min_sep_ns,
                                        max_ns=2 * max_range_m / C0 * 1e9)
    except ValueError as e:
        out["warnings"].append(str(e))
        return out

    eps, src = eps_r, "assumed"
    if plate is not None:
        tp, trp = time_domain(freq_hz, plate, background, window)
        envp = np.abs(trp)
        i = int(np.argmin(np.abs(tp - ts)))
        win = max(1, int(0.5e-9 / (tp[1] - tp[0])))
        plate_amp = envp[max(0, i - win): i + win].max()
        if plate_amp > 0:
            eps, src = eps_from_reflection(a_s, plate_amp), "plate"

    picks = Picks(surface_ns=ts * 1e9, bottom_ns=None, surface_db=float(to_db(a_s)),
                  bottom_db=None, delay_ns=None, thickness_m=None, eps_r=eps, eps_source=src)
    if bottom is not None:
        tb, a_b = bottom
        picks.bottom_ns = tb * 1e9
        picks.bottom_db = float(to_db(a_b))
        picks.delay_ns = (tb - ts) * 1e9
        picks.thickness_m = thickness(tb - ts, eps)
    out["picks"] = picks.__dict__
    return out
