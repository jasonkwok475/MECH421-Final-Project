"""FastAPI backend for the MECH 421 ice radar.

Run (from software/backend):
    uvicorn app.main:app --reload --port 8000
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import os
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import processing
from .touchstone import read_touchstone, write_s2p
from .vna import MockVNA, NanoVNA, NanoVNAError, Sweep, SweepSettings, VNA, list_ports

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("VNA_DATA_DIR", REPO_ROOT / "data" / "measurements"))

app = FastAPI(title="MECH 421 Ice Radar Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------- state
class State:
    def __init__(self) -> None:
        self.vna: VNA | None = None
        self.sweeps: OrderedDict[str, Sweep] = OrderedDict()
        self.references: dict[str, str] = {}  # "background" | "plate" -> sweep id
        self.lock = threading.Lock()

    def add(self, sw: Sweep, keep: int = 100) -> Sweep:
        self.sweeps[sw.id] = sw
        # Keep memory bounded, but never drop a sweep used as a reference.
        droppable = [k for k in self.sweeps if k not in self.references.values()]
        for k in droppable[: max(0, len(self.sweeps) - keep)]:
            del self.sweeps[k]
        return sw

    def get(self, sweep_id: str | None) -> Sweep:
        if not self.sweeps:
            raise HTTPException(404, "No sweeps yet - run a sweep first")
        if sweep_id is None:
            return next(reversed(self.sweeps.values()))
        if sweep_id not in self.sweeps:
            raise HTTPException(404, f"Unknown sweep id {sweep_id}")
        return self.sweeps[sweep_id]

    def require_vna(self) -> VNA:
        if self.vna is None:
            raise HTTPException(409, "Not connected to a VNA")
        return self.vna


state = State()


def sweep_json(sw: Sweep, include_data: bool = True) -> dict:
    d = {
        "id": sw.id, "timestamp": sw.timestamp, "source": sw.source, "label": sw.label,
        "settings": sw.settings.__dict__, "points": int(len(sw.freq_hz)),
    }
    if include_data:
        d.update({
            "freq_hz": sw.freq_hz.tolist(),
            "s11": {"re": sw.s11.real.tolist(), "im": sw.s11.imag.tolist()},
            "s21": {"re": sw.s21.real.tolist(), "im": sw.s21.imag.tolist()},
            "s11_db": processing.to_db(sw.s11).tolist(),
            "s21_db": processing.to_db(sw.s21).tolist(),
            "swr": processing.swr(sw.s11).tolist(),
        })
    return d


# ----------------------------------------------------------------- connection
class ConnectRequest(BaseModel):
    port: str = Field(..., description='Serial port (e.g. "COM5") or "mock" for the simulator')
    max_points_per_scan: int = Field(101, ge=11, le=1001,
                                     description="101 for NanoVNA-H; up to 401 for H4 on DiSlord firmware")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/ports")
def ports() -> list[dict]:
    return list_ports() + [{"device": "mock", "description": "Simulated VNA (no hardware)",
                            "hwid": "", "likely_nanovna": False}]


@app.post("/api/connect")
def connect(req: ConnectRequest) -> dict:
    with state.lock:
        if state.vna is not None:
            state.vna.close()
            state.vna = None
        try:
            state.vna = MockVNA() if req.port == "mock" else NanoVNA(
                req.port, max_points_per_scan=req.max_points_per_scan)
        except (NanoVNAError, OSError) as e:
            raise HTTPException(502, f"Could not open {req.port}: {e}")
        except Exception as e:  # pyserial raises SerialException (an OSError subclass on most versions)
            raise HTTPException(502, f"Could not open {req.port}: {e}")
        return status()


@app.post("/api/disconnect")
def disconnect() -> dict:
    with state.lock:
        if state.vna is not None:
            state.vna.close()
        state.vna = None
    return status()


@app.get("/api/status")
def status() -> dict:
    vna = state.vna
    return {
        "connected": vna is not None,
        "port": vna.port if vna else None,
        "kind": vna.kind if vna else None,
        "info": vna.info() if vna else None,
        "references": {k: sweep_json(state.sweeps[v], False)
                       for k, v in state.references.items() if v in state.sweeps},
        "sweep_count": len(state.sweeps),
        "data_dir": str(DATA_DIR),
    }


# ---------------------------------------------------------------------- sweep
class SweepRequest(BaseModel):
    start_hz: float = Field(500e6, gt=0)
    stop_hz: float = Field(1.5e9, gt=0)
    points: int = Field(101, ge=4, le=4001)
    averages: int = Field(1, ge=1, le=64)


@app.post("/api/sweep")
def sweep(req: SweepRequest) -> dict:
    if req.stop_hz <= req.start_hz:
        raise HTTPException(422, "stop_hz must be greater than start_hz")
    vna = state.require_vna()
    try:
        with state.lock:
            sw = vna.sweep(SweepSettings(req.start_hz, req.stop_hz, req.points, req.averages))
    except NanoVNAError as e:
        raise HTTPException(502, str(e))
    state.add(sw)
    return sweep_json(sw)


@app.get("/api/sweeps")
def sweeps() -> list[dict]:
    return [sweep_json(s, False) for s in reversed(state.sweeps.values())]


@app.get("/api/sweeps/{sweep_id}")
def get_sweep(sweep_id: str) -> dict:
    return sweep_json(state.get(None if sweep_id == "latest" else sweep_id))


# ----------------------------------------------------------------- references
RefKind = Literal["background", "plate"]


class ReferenceRequest(BaseModel):
    sweep_id: str | None = Field(None, description="Defaults to the latest sweep")


@app.post("/api/references/{kind}")
def set_reference(kind: RefKind, req: ReferenceRequest) -> dict:
    sw = state.get(req.sweep_id)
    state.references[kind] = sw.id
    return status()


@app.delete("/api/references/{kind}")
def clear_reference(kind: RefKind) -> dict:
    state.references.pop(kind, None)
    return status()


def _matching_ref(kind: str, sw: Sweep, param: str) -> np.ndarray | None:
    rid = state.references.get(kind)
    if rid is None or rid not in state.sweeps:
        return None
    ref = state.sweeps[rid]
    if len(ref.freq_hz) != len(sw.freq_hz) or not np.allclose(ref.freq_hz, sw.freq_hz, rtol=1e-6):
        raise HTTPException(409, f"The {kind} sweep has different frequencies - "
                                 f"record it again with the same start/stop/points")
    return getattr(ref, param)


# --------------------------------------------------------------------- A-scan
class AScanRequest(BaseModel):
    sweep_id: str | None = None
    param: Literal["s11", "s21"] = "s11"
    subtract_background: bool = True
    use_plate_for_eps: bool = True
    window: Literal["hann", "hamming", "blackman", "rect"] = "hann"
    gate_ns: float = Field(0.0, ge=0)
    eps_r: float = Field(3.2, gt=1)
    max_range_m: float = Field(5.0, gt=0)
    min_sep_ns: float = Field(0.6, ge=0)


@app.post("/api/ascan")
def ascan(req: AScanRequest) -> dict:
    sw = state.get(req.sweep_id)
    s = getattr(sw, req.param)
    bg = _matching_ref("background", sw, req.param) if req.subtract_background else None
    plate = _matching_ref("plate", sw, req.param) if req.use_plate_for_eps else None
    if state.references.get("background") == sw.id and bg is not None:
        bg = None  # A-scan of the background itself: show it raw
    result = processing.ascan(sw.freq_hz, s, background=bg, plate=plate, window=req.window,
                              gate_ns=req.gate_ns, eps_r=req.eps_r,
                              max_range_m=req.max_range_m, min_sep_ns=req.min_sep_ns)
    result["sweep_id"] = sw.id
    result["background_subtracted"] = bg is not None
    return result


# --------------------------------------------------------------- measurements
class SaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    sweep_id: str | None = None
    notes: str = ""


def _safe(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    if not s:
        raise HTTPException(422, "Invalid measurement name")
    return s


@app.post("/api/measurements")
def save_measurement(req: SaveRequest) -> dict:
    sw = state.get(req.sweep_id)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe(req.name)
    path = DATA_DIR / f"{stem}.s2p"
    if path.exists():
        raise HTTPException(409, f"{path.name} already exists - pick another name")
    write_s2p(path, sw.freq_hz, sw.s11, sw.s21,
              comments=[f"MECH421 ice radar | {sw.timestamp} | source={sw.source}",
                        f"notes: {req.notes}"])
    meta = {**sweep_json(sw, False), "name": stem, "notes": req.notes}
    (DATA_DIR / f"{stem}.json").write_text(json.dumps(meta, indent=2))
    return {"name": stem, "path": str(path)}


@app.get("/api/measurements")
def list_measurements() -> list[dict]:
    if not DATA_DIR.exists():
        return []
    out = []
    for p in sorted(DATA_DIR.glob("*.s?p"), key=lambda p: p.stat().st_mtime, reverse=True):
        meta_path = p.with_suffix(".json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        out.append({"name": p.stem, "file": p.name, "timestamp": meta.get("timestamp"),
                    "notes": meta.get("notes", ""), "points": meta.get("points")})
    return out


@app.post("/api/measurements/{name}/load")
def load_measurement(name: str) -> dict:
    stem = _safe(name)
    for ext in (".s2p", ".s1p"):
        p = DATA_DIR / f"{stem}{ext}"
        if p.exists():
            f, s11, s21 = read_touchstone(p)
            sw = Sweep(freq_hz=f, s11=s11, s21=s21, source="file", label=stem,
                       settings=SweepSettings(float(f[0]), float(f[-1]), len(f)))
            state.add(sw)
            return sweep_json(sw)
    raise HTTPException(404, f"No measurement named {stem}")


# ------------------------------------------------------------------ simulator
class SceneRequest(BaseModel):
    kind: Literal["sky", "plate", "ice"] | None = None
    distance_m: float | None = Field(None, gt=0, le=10)
    ice_thickness_m: float | None = Field(None, gt=0, le=2)
    eps_ice: float | None = Field(None, gt=1, le=10)
    noise: float | None = Field(None, ge=0, le=0.1)


@app.post("/api/mock/scene")
def mock_scene(req: SceneRequest) -> dict:
    vna = state.require_vna()
    if not isinstance(vna, MockVNA):
        raise HTTPException(409, "Scenes only apply to the simulated VNA")
    vna.set_scene(**req.model_dump())
    return vna.info()
