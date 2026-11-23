# Backend (FastAPI)

Talks to the NanoVNA over USB serial, runs the radar processing and saves measurements.

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # API docs: http://127.0.0.1:8000/docs
pytest
```

## Layout

| File | Role |
|---|---|
| `app/vna/nanovna.py` | Serial driver: shell commands, `scan <start> <stop> <pts> 7` (falls back to `sweep` + `data 0/1` on old firmware), splits long sweeps into ≤101-point segments |
| `app/vna/mock.py` | Simulated VNA (antenna ringing + sky / plate / ice scenes) for working without hardware |
| `app/processing.py` | Background subtraction, window, inverse FFT, echo picking, thickness, ε from a plate reference |
| `app/touchstone.py` | Read / write `.s1p` / `.s2p` |
| `app/main.py` | REST API |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/ports` | Serial ports (NanoVNA flagged) + `mock` |
| POST | `/api/connect` | `{port, max_points_per_scan}` |
| POST | `/api/disconnect` | |
| GET | `/api/status` | Connection, firmware info, references |
| POST | `/api/sweep` | `{start_hz, stop_hz, points, averages}` → S11/S21, dB, SWR |
| POST/DELETE | `/api/references/{background\|plate}` | Use a sweep as background or metal-plate reference |
| POST | `/api/ascan` | Time-domain trace + surface/bottom picks + thickness |
| GET/POST | `/api/measurements` | List / save (`.s2p` + `.json` in `data/measurements`) |
| POST | `/api/measurements/{name}/load` | Load a saved sweep |
| POST | `/api/mock/scene` | Simulator only: `{kind: sky\|plate\|ice, distance_m, ice_thickness_m}` |

## Notes

- The NanoVNA applies its own calibration before sending data, so calibrate on the device over
  the range you sweep. If you change the range a lot, recalibrate.
- Only one program can use the serial port: close NanoVNA-Saver first.
- NanoVNA-H: 101 points per scan. The driver segments longer sweeps automatically.
