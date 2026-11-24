# Analysis scripts

Stand-alone tools that work on saved Touchstone files (no backend server needed). They use the
backend's uv environment: `make synth`, `make ascan ...`, `make overlap-sim`, or
`uv run --project ../backend python <script>.py` from this folder.

| Script | Purpose |
|---|---|
| `ice_ascan.py` | A-scan + ice thickness from `.s1p`/`.s2p` files: `ice_ascan.py ice.s1p --bg sky.s1p [--plate plate.s1p] --plot out.png` |
| `make_synthetic.py` | Writes fake `ice.s1p`, `sky.s1p`, `plate.s1p` (25 cm ice) for testing |
| `overlap_sim.py` | Simulates one antenna 20 cm above 20 cm ice: ringing vs bandwidth |

The same processing is used by the backend (`software/backend/app/processing.py`).
