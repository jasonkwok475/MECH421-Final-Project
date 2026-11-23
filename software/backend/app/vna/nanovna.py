"""Serial driver for NanoVNA (H / H4 / DiSlord firmware and the original edy555 firmware).

The NanoVNA exposes a text shell over USB serial:

    ch> version            <- we send "version\\r"
    version                <- the device echoes the command
    1.2.27                 <- response lines
    ch>                    <- prompt = response finished

Sweeps use the `scan` command when the firmware has it:

    scan <start_hz> <stop_hz> <points> 7

which returns one line per point: "freq s11_re s11_im s21_re s21_im".
Older firmware falls back to `sweep` + `frequencies` + `data 0` + `data 1`.

The data the NanoVNA returns already has the on-device calibration applied
(the "C0 D R S" letters on screen), so calibrate on the device over the range
you will sweep.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from .base import VNA, Sweep, SweepSettings

PROMPT = b"ch> "
STM32_VCP = (0x0483, 0x5740)  # USB VID:PID of the NanoVNA virtual COM port


class NanoVNAError(RuntimeError):
    pass


class NanoVNA(VNA):
    kind = "nanovna"

    def __init__(self, port: str, transport=None, max_points_per_scan: int = 101,
                 timeout_s: float = 10.0):
        """`transport` is anything with write(bytes), read(n), reset_input_buffer(),
        close() and an `in_waiting` attribute (a pyserial Serial, or a fake in tests)."""
        self.port = port
        self.max_points_per_scan = max_points_per_scan
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        if transport is None:
            import serial  # pyserial

            transport = serial.Serial(port, baudrate=115200, timeout=0.05)
        self._ser = transport
        self._has_scan: bool | None = None
        self._sync()
        self._info = self._read_info()

    # ------------------------------------------------------------------ shell
    def _sync(self) -> None:
        """Get to a clean prompt (the device may be mid-output from a previous session)."""
        self._ser.reset_input_buffer()
        self._ser.write(b"\r")
        try:
            self._read_until_prompt(timeout_s=2.0)
        except NanoVNAError:
            # Some firmware does not answer a bare CR; try once more.
            self._ser.write(b"\r")
            self._read_until_prompt(timeout_s=2.0)

    def _read_until_prompt(self, timeout_s: float | None = None) -> bytes:
        deadline = time.monotonic() + (timeout_s or self.timeout_s)
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = self._ser.read(max(1, getattr(self._ser, "in_waiting", 0) or 1))
            if chunk:
                buf += chunk
                if buf.endswith(PROMPT):
                    return bytes(buf[: -len(PROMPT)])
        raise NanoVNAError(f"Timed out waiting for the NanoVNA prompt (got {bytes(buf[-80:])!r})")

    def command(self, cmd: str, timeout_s: float | None = None) -> list[str]:
        """Send one shell command and return the response lines (echo removed)."""
        with self._lock:
            self._ser.reset_input_buffer()
            self._ser.write(cmd.encode("ascii") + b"\r")
            raw = self._read_until_prompt(timeout_s)
        lines = [ln.strip() for ln in raw.decode("ascii", "replace").replace("\r", "").split("\n")]
        lines = [ln for ln in lines if ln]
        if lines and lines[0] == cmd.strip():
            lines = lines[1:]
        return lines

    # ------------------------------------------------------------------- info
    def _read_info(self) -> dict:
        version = self.command("version", timeout_s=3.0)
        info = self.command("info", timeout_s=3.0)
        return {"version": version[0] if version else "unknown", "info": info}

    def info(self) -> dict:
        return {**self._info, "port": self.port, "kind": self.kind,
                "max_points_per_scan": self.max_points_per_scan,
                "scan_command": self._has_scan}

    # ------------------------------------------------------------------ sweep
    def sweep(self, settings: SweepSettings) -> Sweep:
        freqs = settings.frequencies()
        s11 = np.zeros(len(freqs), complex)
        s21 = np.zeros(len(freqs), complex)
        for _ in range(max(1, settings.averages)):
            f, a, b = self._sweep_once(freqs)
            s11 += a
            s21 += b
        n = max(1, settings.averages)
        return Sweep(freq_hz=f, s11=s11 / n, s21=s21 / n, settings=settings, source=self.kind)

    def _sweep_once(self, freqs: np.ndarray):
        """Sweep in segments of at most max_points_per_scan points (like NanoVNA-Saver)."""
        fs, s11s, s21s = [], [], []
        step = self.max_points_per_scan
        for i in range(0, len(freqs), step):
            seg = freqs[i : i + step]
            if len(seg) == 1:  # the firmware needs >= 2 points per scan
                seg_f, a, b = self._scan(seg[0], seg[0] + 1.0, 2)
                seg_f, a, b = seg_f[:1], a[:1], b[:1]
            else:
                seg_f, a, b = self._scan(seg[0], seg[-1], len(seg))
            fs.append(seg_f), s11s.append(a), s21s.append(b)
        return np.concatenate(fs), np.concatenate(s11s), np.concatenate(s21s)

    def _scan(self, start: float, stop: float, points: int):
        if self._has_scan is not False:
            lines = self.command(f"scan {int(start)} {int(stop)} {points} 7", timeout_s=30.0)
            rows = parse_rows(lines, ncols=5)
            if len(rows) == points:
                self._has_scan = True
                return rows[:, 0], rows[:, 1] + 1j * rows[:, 2], rows[:, 3] + 1j * rows[:, 4]
            if self._has_scan is None:
                self._has_scan = False  # firmware without `scan`: use the fallback from now on
            else:
                raise NanoVNAError(f"scan returned {len(rows)} rows, expected {points}: {lines[:3]}")
        return self._legacy_scan(start, stop, points)

    def _legacy_scan(self, start: float, stop: float, points: int):
        self.command(f"sweep {int(start)} {int(stop)} {points}")
        time.sleep(0.2 + 0.02 * points)  # let at least one full sweep finish
        f = parse_rows(self.command("frequencies"), ncols=1)[:, 0]
        d0 = parse_rows(self.command("data 0"), ncols=2)
        d1 = parse_rows(self.command("data 1"), ncols=2)
        n = min(len(f), len(d0), len(d1))
        if n == 0:
            raise NanoVNAError("NanoVNA returned no sweep data")
        return f[:n], d0[:n, 0] + 1j * d0[:n, 1], d1[:n, 0] + 1j * d1[:n, 1]

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass


def parse_rows(lines: list[str], ncols: int) -> np.ndarray:
    """Parse whitespace-separated numeric lines, skipping anything that is not data."""
    rows = []
    for ln in lines:
        parts = ln.split()
        if len(parts) < ncols:
            continue
        try:
            rows.append([float(p) for p in parts[:ncols]])
        except ValueError:
            continue
    return np.array(rows, dtype=float).reshape(-1, ncols)


def list_ports() -> list[dict]:
    """Serial ports on this computer, with a flag for ports that look like a NanoVNA."""
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        return []
    out = []
    for p in lp.comports():
        likely = (p.vid, p.pid) == STM32_VCP or "nanovna" in (p.description or "").lower()
        out.append({"device": p.device, "description": p.description or "",
                    "hwid": p.hwid or "", "likely_nanovna": bool(likely)})
    out.sort(key=lambda d: (not d["likely_nanovna"], d["device"]))
    return out
