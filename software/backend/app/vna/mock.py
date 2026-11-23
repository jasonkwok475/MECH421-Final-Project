"""A fake VNA for developing the GUI and processing without hardware.

It models one antenna on port 1 (S11): the antenna's own mismatch and ringing,
plus echoes from whatever "scene" is in front of it, plus noise. S21 is noise
unless the scene says two antennas are used.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .base import VNA, Sweep, SweepSettings

C0 = 299_792_458.0


@dataclass
class MockScene:
    kind: str = "sky"          # "sky" | "plate" | "ice"
    distance_m: float = 0.5    # antenna to plate / ice surface
    ice_thickness_m: float = 0.25
    eps_ice: float = 3.2
    noise: float = 2e-3


class MockVNA(VNA):
    kind = "mock"

    def __init__(self, seed: int = 0):
        self.port = "mock"
        self.scene = MockScene()
        self._rng = np.random.default_rng(seed)

    def info(self) -> dict:
        return {"version": "mock-1.0", "info": ["Simulated NanoVNA"], "port": self.port,
                "kind": self.kind, "scene": asdict(self.scene), "max_points_per_scan": 101,
                "scan_command": True}

    def set_scene(self, **kw) -> MockScene:
        for k, v in kw.items():
            if v is not None and hasattr(self.scene, k):
                setattr(self.scene, k, v)
        return self.scene

    # ------------------------------------------------------------------ model
    @staticmethod
    def _antenna(f: np.ndarray) -> np.ndarray:
        """Antenna passband (~0.75-3.2 GHz) used to shape the echoes."""
        return np.exp(-((f - 2.0e9) / 1.2e9) ** 4)

    @staticmethod
    def _self_reflection(f: np.ndarray) -> np.ndarray:
        """Mismatch + ringing: poor match below ~0.7 GHz, decaying internal reflections."""
        low = 0.9 / (1 + (f / 0.65e9) ** 6)
        ring = sum(a * np.exp(-2j * np.pi * f * t)
                   for a, t in [(0.18, 0.15e-9), (0.10, 0.6e-9), (0.05, 1.1e-9), (0.025, 1.8e-9)])
        return low + ring

    def _echoes(self, f: np.ndarray) -> np.ndarray:
        s = self.scene
        h = self._antenna(f)
        spread = 0.08 / max(s.distance_m, 0.05)  # weaker echo further away
        t_s = 2 * s.distance_m / C0
        if s.kind == "plate":
            return h * spread * -1.0 * np.exp(-2j * np.pi * f * t_s)
        if s.kind == "ice":
            n = np.sqrt(s.eps_ice)
            r_s = (1 - n) / (1 + n)
            r_b = (n - np.sqrt(80)) / (n + np.sqrt(80))
            t_b = t_s + 2 * s.ice_thickness_m * n / C0
            return h * spread * (r_s * np.exp(-2j * np.pi * f * t_s)
                                 + 0.9 * (1 - r_s**2) * r_b * np.exp(-2j * np.pi * f * t_b))
        return np.zeros_like(f, dtype=complex)

    def _noise(self, n: int) -> np.ndarray:
        return self.scene.noise * (self._rng.standard_normal(n) + 1j * self._rng.standard_normal(n))

    def sweep(self, settings: SweepSettings) -> Sweep:
        f = settings.frequencies()
        avg = max(1, settings.averages)
        noise11 = sum(self._noise(len(f)) for _ in range(avg)) / avg
        s11 = self._self_reflection(f) + self._echoes(f) + noise11
        # Nothing on port 2: S21 sits at the noise floor (~ -80 dB).
        s21 = 1e-4 * (self._rng.standard_normal(len(f)) + 1j * self._rng.standard_normal(len(f)))
        return Sweep(freq_hz=f, s11=s11, s21=s21, settings=settings, source=self.kind,
                     label=f"mock:{self.scene.kind}")
