"""Driver tests against a fake serial port that behaves like the NanoVNA shell."""
import numpy as np
import pytest

from app.vna import NanoVNA, SweepSettings
from app.vna.nanovna import parse_rows


class FakeNanoVNA:
    """Answers shell commands like the firmware: echo, lines, then 'ch> '."""

    def __init__(self, has_scan=True, max_points=101):
        self.has_scan = has_scan
        self.max_points = max_points
        self.out = bytearray()
        self.commands = []
        self.sweep_range = (50e3, 900e6, 101)
        self.in_waiting = 0

    def reset_input_buffer(self):
        self.out.clear()

    def write(self, data: bytes):
        cmd = data.decode().strip()
        self.commands.append(cmd)
        lines = self._respond(cmd) if cmd else []
        echo = (cmd + "\r\n") if cmd else ""
        self.out += (echo + "".join(f"{ln}\r\n" for ln in lines) + "ch> ").encode()
        self.in_waiting = len(self.out)

    def read(self, n=1):
        chunk = bytes(self.out[:n])
        del self.out[:n]
        self.in_waiting = len(self.out)
        return chunk

    def close(self):
        pass

    @staticmethod
    def _s(f):
        return 0.2 * np.exp(-2j * np.pi * f * 3e-9), 1e-3 * np.exp(-2j * np.pi * f * 1e-9)

    def _respond(self, cmd):
        parts = cmd.split()
        if parts[0] == "version":
            return ["1.2.27"]
        if parts[0] == "info":
            return ["Board: NanoVNA-H", "Version: 1.2.27"]
        if parts[0] == "scan":
            if not self.has_scan:
                return ["scan?"]
            start, stop, pts = float(parts[1]), float(parts[2]), int(parts[3])
            assert pts <= self.max_points, "driver must segment sweeps"
            f = np.linspace(start, stop, pts)
            a, b = self._s(f)
            return [f"{fi:.0f} {x.real:.9f} {x.imag:.9f} {y.real:.9f} {y.imag:.9f}"
                    for fi, x, y in zip(f, a, b)]
        if parts[0] == "sweep":
            self.sweep_range = (float(parts[1]), float(parts[2]), int(parts[3]))
            return []
        if parts[0] == "frequencies":
            return [f"{fi:.0f}" for fi in np.linspace(*self.sweep_range)]
        if parts[0] == "data":
            a, b = self._s(np.linspace(*self.sweep_range))
            x = a if parts[1] == "0" else b
            return [f"{v.real:.9f} {v.imag:.9f}" for v in x]
        return [f"{parts[0]}?"]


def test_connect_reads_version():
    vna = NanoVNA("FAKE", transport=FakeNanoVNA())
    assert vna.info()["version"] == "1.2.27"


@pytest.mark.parametrize("has_scan", [True, False])
def test_sweep_matches_model(has_scan):
    fake = FakeNanoVNA(has_scan=has_scan)
    vna = NanoVNA("FAKE", transport=fake)
    sw = vna.sweep(SweepSettings(500e6, 1.5e9, 101))
    a, b = FakeNanoVNA._s(sw.freq_hz)
    assert len(sw.freq_hz) == 101
    assert np.allclose(sw.s11, a, atol=1e-6)
    assert np.allclose(sw.s21, b, atol=1e-6)


def test_long_sweep_is_segmented():
    fake = FakeNanoVNA(max_points=101)
    vna = NanoVNA("FAKE", transport=fake, max_points_per_scan=101)
    sw = vna.sweep(SweepSettings(500e6, 1.5e9, 301))
    assert len(sw.freq_hz) == 301
    assert np.allclose(sw.freq_hz, np.linspace(500e6, 1.5e9, 301), atol=2)
    assert sum(c.startswith("scan") for c in fake.commands) == 3


def test_parse_rows_skips_junk():
    rows = parse_rows(["scan 1 2 3 7", "1 0.1 0.2", "ch>", "2 0.3 0.4"], ncols=3)
    assert rows.shape == (2, 3)
