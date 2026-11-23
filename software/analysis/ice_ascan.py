"""
ice_ascan.py - turn VNA sweeps into an A-scan and an ice-thickness estimate.

Pipeline (same idea as Meng et al., 2025, Water Resources Research):
  1. Load the sweep (Touchstone .s1p / .s2p from NanoVNA-Saver, or any CSV).
  2. Subtract a background sweep (antenna pointed at open sky / no ice).
  3. Band-pass window in frequency (reduces sidelobes / ringing).
  4. Inverse FFT -> time-domain trace (the "A-scan").
  5. Pick the ice-surface and ice-bottom echoes.
  6. Thickness  h = c * dt / (2 * sqrt(eps_r)).
  Optional: estimate eps_r from the surface echo vs. a metal-plate reference.

Usage:
  python ice_ascan.py ice.s1p --bg sky.s1p [--plate plate.s1p] [--param S11|S21]
                      [--eps 3.2] [--gate 1.0] [--plot ascan.png]

Requires: numpy, scipy, matplotlib  (pip install numpy scipy matplotlib)
"""
import argparse
import numpy as np
from scipy.signal import find_peaks, windows

C0 = 299_792_458.0  # m/s


# --------------------------------------------------------------------------
# 1. Loading
# --------------------------------------------------------------------------
def load_touchstone(path, param="S11"):
    """Minimal Touchstone reader (.s1p/.s2p). Returns (freq_Hz, complex S)."""
    unit_scale = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}
    scale, fmt = 1e9, "MA"  # Touchstone defaults: GHz, magnitude-angle
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.split("!")[0].strip()
            if not line:
                continue
            if line.startswith("#"):
                tok = line[1:].upper().split()
                for t in tok:
                    if t in unit_scale:
                        scale = unit_scale[t]
                    if t in ("RI", "MA", "DB"):
                        fmt = t
                continue
            rows.append([float(x) for x in line.split()])
    d = np.array(rows)
    f = d[:, 0] * scale
    # column pairs: S11 (1,2), S21 (3,4), S12 (5,6), S22 (7,8)
    col = {"S11": 1, "S21": 3, "S12": 5, "S22": 7}[param.upper()]
    a, b = d[:, col], d[:, col + 1]
    if fmt == "RI":
        s = a + 1j * b
    elif fmt == "MA":
        s = a * np.exp(1j * np.deg2rad(b))
    else:  # DB
        s = 10 ** (a / 20) * np.exp(1j * np.deg2rad(b))
    return f, s


# --------------------------------------------------------------------------
# 2-4. Frequency domain -> time domain
# --------------------------------------------------------------------------
def to_time_domain(f, s, bg=None, window="hann", pad=16):
    """Background-subtract, window and inverse-FFT a sweep.

    Returns t (s) and the complex time trace. Plot np.abs() of it for the
    envelope. Uses 'band-pass' mode: works for any start frequency.
    """
    x = s - bg if bg is not None else s.copy()
    n = len(f)
    w = windows.get_window(window, n) if window else np.ones(n)
    df = np.mean(np.diff(f))
    nfft = int(2 ** np.ceil(np.log2(n * pad)))           # zero-pad -> smooth trace
    trace = np.fft.ifft(x * w, nfft) * nfft / np.sum(w)  # keep amplitude scale
    t = np.arange(nfft) / (nfft * df)                    # max time = 1/df
    return t, trace


# --------------------------------------------------------------------------
# 5. Echo picking
# --------------------------------------------------------------------------
def pick_echoes(t, trace, gate_ns=0.0, min_sep_ns=0.6, first_frac=0.25):
    """Surface = FIRST strong peak after the gate (first arrival);
    bottom = strongest peak after the surface.

    The bottom echo is often STRONGER than the surface echo (ice-water
    contrast is larger than air-ice), so "strongest peak" is not the surface.

    gate_ns     : ignore everything before this time (antenna ringing).
    min_sep_ns  : bottom must be at least this much later than the surface
                  (0.6 ns ~ 5 cm of ice).
    first_frac  : a peak counts as the first arrival if it is above this
                  fraction of the largest echo after the gate.
    """
    env = np.abs(trace)
    dt = t[1] - t[0]
    start = int(gate_ns * 1e-9 / dt)
    pk, _ = find_peaks(env, height=0.02 * env[start:].max(),
                       distance=max(1, int(0.2e-9 / dt)))
    pk = pk[pk >= start]
    strong = pk[env[pk] >= first_frac * env[pk].max()] if len(pk) else pk
    if len(strong) < 1:
        raise RuntimeError("No echoes found - check gate/background.")
    surf = strong[0]
    later = pk[t[pk] > t[surf] + min_sep_ns * 1e-9]
    if len(later) == 0:
        raise RuntimeError("No bottom echo found after the surface echo.")
    btm = later[np.argmax(env[later])]
    return _refine(t, env, surf), _refine(t, env, btm), env


def _refine(t, env, i):
    """Parabolic interpolation of a peak -> sub-sample timing."""
    if 0 < i < len(env) - 1:
        a, b, c = env[i - 1], env[i], env[i + 1]
        p = 0.5 * (a - c) / (a - 2 * b + c)
        return t[i] + p * (t[1] - t[0]), b
    return t[i], env[i]


# --------------------------------------------------------------------------
# 6. Physics
# --------------------------------------------------------------------------
def thickness(dt_s, eps_r):
    return C0 * dt_s / (2 * np.sqrt(eps_r))


def eps_from_surface(surface_amp, plate_amp):
    """eps_r from |R| = surface echo / metal-plate echo (same height, same setup)."""
    R = surface_amp / plate_amp
    return ((1 + R) / (1 - R)) ** 2


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ice")
    ap.add_argument("--bg", required=True, help="background sweep (open sky)")
    ap.add_argument("--plate", help="metal plate at the ice-surface height")
    ap.add_argument("--param", default="S11")
    ap.add_argument("--eps", type=float, default=3.2)
    ap.add_argument("--gate", type=float, default=0.0, help="gate start [ns]")
    ap.add_argument("--plot", help="save the A-scan plot to this file")
    a = ap.parse_args()

    f, s = load_touchstone(a.ice, a.param)
    _, sbg = load_touchstone(a.bg, a.param)
    t, tr = to_time_domain(f, s, sbg)
    (ts, As), (tb, Ab), env = pick_echoes(t, tr, gate_ns=a.gate)

    eps = a.eps
    if a.plate:
        _, sp = load_touchstone(a.plate, a.param)
        tp, trp = to_time_domain(f, sp, sbg)
        envp = np.abs(trp)
        gate = int(a.gate * 1e-9 / (tp[1] - tp[0]))
        eps = eps_from_surface(As, envp[gate:].max())
        print(f"eps_r from surface echo : {eps:.2f}")

    dt = tb - ts
    print(f"surface echo   : {ts*1e9:.3f} ns")
    print(f"bottom echo    : {tb*1e9:.3f} ns")
    print(f"two-way delay  : {dt*1e9:.3f} ns")
    print(f"ice thickness  : {thickness(dt, eps)*100:.1f} cm  (eps_r = {eps:.2f})")

    if a.plot:
        plot_ascan(t, env, ts, tb, eps, a.plot)


def plot_ascan(t, env, ts, tb, eps, path, tmax_ns=None):
    import matplotlib.pyplot as plt
    tmax_ns = tmax_ns or (tb * 1e9 + 3)
    m = t * 1e9 <= tmax_ns
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(t[m] * 1e9, 20 * np.log10(env[m] / env.max() + 1e-6), color="#d9480f")
    for x, lab in ((ts, "ice surface"), (tb, "ice bottom")):
        ax.axvline(x * 1e9, color="#1c7ed6", ls="--", lw=1)
        ax.text(x * 1e9, 1, lab, ha="center", va="bottom", color="#1c7ed6")
    ax.set_xlabel("Two-way time [ns]")
    ax.set_ylabel("Echo strength [dB]")
    ax.set_ylim(-50, 6)
    h = thickness(tb - ts, eps) * 100
    ax.set_title(f"A-scan: Δt = {(tb-ts)*1e9:.2f} ns  →  h = {h:.1f} cm (ε = {eps:.2f})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=200)


if __name__ == "__main__":
    main()
