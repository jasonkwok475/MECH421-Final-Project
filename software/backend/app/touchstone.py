"""Read and write Touchstone files (.s1p / .s2p), the format NanoVNA-Saver also uses."""
from __future__ import annotations

from pathlib import Path

import numpy as np

UNITS = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}


def write_s2p(path: Path, freq_hz: np.ndarray, s11: np.ndarray, s21: np.ndarray,
              comments: list[str] | None = None) -> None:
    """Write a 2-port file. The NanoVNA measures only S11 and S21, so S12 = S21 and S22 = 0."""
    lines = [f"! {c}" for c in (comments or [])]
    lines.append("# HZ S RI R 50")
    for f, a, b in zip(freq_hz, s11, s21):
        lines.append(f"{f:.0f} {a.real:.9e} {a.imag:.9e} {b.real:.9e} {b.imag:.9e} "
                     f"{b.real:.9e} {b.imag:.9e} 0 0")
    Path(path).write_text("\n".join(lines) + "\n")


def read_touchstone(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (freq_hz, s11, s21). s21 is zeros for a .s1p file."""
    scale, fmt = 1e9, "MA"
    rows = []
    for line in Path(path).read_text().splitlines():
        line = line.split("!")[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            for tok in line[1:].upper().split():
                if tok in UNITS:
                    scale = UNITS[tok]
                elif tok in ("RI", "MA", "DB"):
                    fmt = tok
            continue
        rows.append([float(x) for x in line.split()])
    d = np.array(rows)

    def cplx(a, b):
        if fmt == "RI":
            return a + 1j * b
        mag = a if fmt == "MA" else 10 ** (a / 20)
        return mag * np.exp(1j * np.deg2rad(b))

    f = d[:, 0] * scale
    s11 = cplx(d[:, 1], d[:, 2])
    s21 = cplx(d[:, 3], d[:, 4]) if d.shape[1] >= 5 else np.zeros_like(s11)
    return f, s11, s21
