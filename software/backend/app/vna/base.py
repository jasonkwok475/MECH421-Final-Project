"""Common types for VNA drivers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np


@dataclass
class SweepSettings:
    start_hz: float
    stop_hz: float
    points: int
    averages: int = 1

    def frequencies(self) -> np.ndarray:
        return np.linspace(self.start_hz, self.stop_hz, self.points)


@dataclass
class Sweep:
    """One measured sweep: complex S11 and S21 at each frequency."""

    freq_hz: np.ndarray
    s11: np.ndarray
    s21: np.ndarray
    settings: SweepSettings
    source: str = "nanovna"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    label: str | None = None


class VNA:
    """Interface every VNA driver implements."""

    kind = "base"
    port: str = ""

    def info(self) -> dict:
        raise NotImplementedError

    def sweep(self, settings: SweepSettings) -> Sweep:
        raise NotImplementedError

    def close(self) -> None:
        pass
