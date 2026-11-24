# MECH421-Project: UWB Ice Radar

A low-cost ultra-wideband radar for measuring freshwater lake-ice thickness and imaging inside the ice
(layers, air pockets, embedded objects). A VNA (NanoVNA / LiteVNA) acts as a stepped-frequency radar,
Vivaldi antennas look down at the ice, and a scanning gantry builds 2D/3D images.

## Repository layout

| Folder | What lives there |
|---|---|
| [`software/backend`](software/backend) | Python (FastAPI) server: talks to the VNA over USB serial, runs the radar processing, saves measurements |
| [`software/frontend`](software/frontend) | React + TypeScript (Vite) test GUI: connect, sweep, set references, view S11/SWR and A-scans |
| [`software/analysis`](software/analysis) | Stand-alone Python scripts (A-scan from Touchstone files, simulations) |
| [`firmware`](firmware) | Microcontroller firmware (gantry / RF switch controller) – not started |
| [`hardware`](hardware) | Antennas, mounts, gantry and PCB design files – not started |
| [`docs`](docs) | Design brief, papers, test notes |
| [`data`](data) | Measurements saved by the backend (`data/measurements`, git-ignored) |
| `Makefile` | Setup, run, test and analysis commands (`make help`) |

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), **Node.js 20+**, and GNU make
(Windows: `winget install astral-sh.uv` and `choco install make`).

```powershell
make setup    # uv sync (backend) + npm install (frontend)
make dev      # backend on http://127.0.0.1:8000, GUI on http://localhost:5173
make help     # every other command
```

Without make:

```powershell
cd software\backend;  uv sync;  uv run uvicorn app.main:app --reload --port 8000
cd software\frontend; npm install; npm run dev
```

## First test with the NanoVNA

1. **Calibrate on the NanoVNA itself** (OPEN / SHORT / LOAD at the end of your cable) over the range you
   will sweep, and save it (`SAVE 0`). The data sent over USB already has this calibration applied.
2. Close NanoVNA-Saver if it is open (only one program can hold the serial port).
3. In the GUI pick the port marked **★ NanoVNA** and click **Connect**. Use `mock` to try everything without hardware.
4. Sweep 500–1500 MHz, 101 points (NanoVNA-H). Check the SWR tab.
5. Point the antenna at open sky → **Single sweep** → **Background: Use latest sweep**.
6. Point it at a wall / metal plate / ice → **Single sweep**. The A-scan shows echoes vs distance,
   with the background subtracted.
7. Save sweeps you want to keep under **Measurements** (Touchstone `.s2p` in `data/measurements`).

## Tests

```powershell
make test     # backend: processing, NanoVNA serial protocol (fake port), API workflow with the simulator
make build    # frontend: type-check + production build
```
