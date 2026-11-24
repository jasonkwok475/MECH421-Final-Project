# MECH421 Final Project - common commands (Python via uv, frontend via npm)
#
#   make help      list everything
#   make setup     install backend (uv sync) + frontend (npm install)
#   make dev       run backend + GUI together  ->  http://localhost:5173
#
# Works with GNU make on Windows (PowerShell/cmd) and on macOS/Linux.

BACKEND  := software/backend
FRONTEND := software/frontend
ANALYSIS := software/analysis
PORT     ?= 8000

# Analysis scripts run in the backend's uv environment
UV_ANALYSIS := uv run --project ../backend python

ifeq ($(OS),Windows_NT)
  CLEAN_PY := powershell -NoProfile -Command "Get-ChildItem -Recurse -Directory -Include __pycache__,.pytest_cache | Remove-Item -Recurse -Force"
  RMDIR     = powershell -NoProfile -Command "if (Test-Path '$(1)') { Remove-Item -Recurse -Force '$(1)' }"
  OPEN     := start ""
else
  CLEAN_PY := find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
  RMDIR     = rm -rf $(1)
  OPEN     := $(if $(shell command -v xdg-open 2>/dev/null),xdg-open,open)
endif

.DEFAULT_GOAL := help
.PHONY: help setup setup-backend setup-frontend dev backend frontend api-docs \
        test build lint check synth ascan overlap-sim clean clean-all

help:
	@echo "MECH421 Final Project"
	@echo ""
	@echo "  Setup"
	@echo "    make setup            Backend (uv sync) + frontend (npm install)"
	@echo "    make setup-backend    uv sync in software/backend"
	@echo "    make setup-frontend   npm install in software/frontend"
	@echo ""
	@echo "  Run"
	@echo "    make dev              Backend + GUI in parallel (Ctrl+C stops both)"
	@echo "    make backend          Backend only:  http://127.0.0.1:$(PORT)  (PORT=8000)"
	@echo "    make frontend         GUI only:      http://localhost:5173 (needs the backend)"
	@echo "    make api-docs         Open the interactive API docs"
	@echo ""
	@echo "  Check"
	@echo "    make test             Backend tests (processing, NanoVNA protocol, API with simulator)"
	@echo "    make build            Frontend type-check + production build"
	@echo "    make lint             Frontend lint (oxlint)"
	@echo "    make check            test + build"
	@echo ""
	@echo "  Analysis (software/analysis, works on saved .s1p/.s2p files)"
	@echo "    make synth            Write fake ice.s1p / sky.s1p / plate.s1p (25 cm ice)"
	@echo "    make ascan ICE=ice.s1p BG=sky.s1p [PLATE=plate.s1p] [PARAM=S11] [GATE=1.0]"
	@echo "                          A-scan + thickness; saves ascan.png in software/analysis"
	@echo "    make overlap-sim      One antenna 20 cm above 20 cm ice: ringing vs bandwidth plot"
	@echo ""
	@echo "  Housekeeping"
	@echo "    make clean            Remove caches and build output"
	@echo "    make clean-all        clean + delete .venv and node_modules"

# ---------------------------------------------------------------- setup
setup: setup-backend setup-frontend

setup-backend:
	cd $(BACKEND) && uv sync

setup-frontend:
	cd $(FRONTEND) && npm install

# ------------------------------------------------------------------ run
dev:
	$(MAKE) -j2 backend frontend

backend:
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port $(PORT)

frontend:
	cd $(FRONTEND) && npm run dev

api-docs:
	$(OPEN) http://127.0.0.1:$(PORT)/docs

# ---------------------------------------------------------------- check
test:
	cd $(BACKEND) && uv run pytest -q

build:
	cd $(FRONTEND) && npm run build

lint:
	cd $(FRONTEND) && npm run lint

check: test build

# ------------------------------------------------------------- analysis
ICE   ?= ice.s1p
BG    ?= sky.s1p
PLATE ?=
PARAM ?= S11
GATE  ?= 0.0

synth:
	cd $(ANALYSIS) && $(UV_ANALYSIS) make_synthetic.py

ascan:
	cd $(ANALYSIS) && $(UV_ANALYSIS) ice_ascan.py $(ICE) --bg $(BG) $(if $(PLATE),--plate $(PLATE)) --param $(PARAM) --gate $(GATE) --plot ascan.png

overlap-sim:
	cd $(ANALYSIS) && $(UV_ANALYSIS) overlap_sim.py

# ---------------------------------------------------------- housekeeping
clean:
	$(CLEAN_PY)
	$(call RMDIR,$(FRONTEND)/dist)

clean-all: clean
	$(call RMDIR,$(BACKEND)/.venv)
	$(call RMDIR,$(FRONTEND)/node_modules)
