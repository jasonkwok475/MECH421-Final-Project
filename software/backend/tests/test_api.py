"""End-to-end API flow using the simulated VNA."""
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    main.state = main.State()
    return TestClient(main.app)


SWEEP = {"start_hz": 0.75e9, "stop_hz": 3.0e9, "points": 226, "averages": 2}


def test_full_ice_workflow(client):
    assert client.post("/api/connect", json={"port": "mock"}).json()["connected"]

    client.post("/api/mock/scene", json={"kind": "sky"})
    assert client.post("/api/sweep", json=SWEEP).status_code == 200
    client.post("/api/references/background", json={})

    client.post("/api/mock/scene", json={"kind": "plate", "distance_m": 0.5})
    client.post("/api/sweep", json=SWEEP)
    client.post("/api/references/plate", json={})

    client.post("/api/mock/scene", json={"kind": "ice", "distance_m": 0.5, "ice_thickness_m": 0.3})
    sw = client.post("/api/sweep", json=SWEEP).json()
    assert len(sw["s11_db"]) == 226 and len(sw["swr"]) == 226

    res = client.post("/api/ascan", json={"sweep_id": sw["id"]}).json()
    assert res["background_subtracted"]
    assert abs(res["picks"]["thickness_m"] - 0.30) < 0.02

    saved = client.post("/api/measurements", json={"name": "ice 30cm", "notes": "mock"}).json()
    assert saved["name"] == "ice_30cm"
    assert client.get("/api/measurements").json()[0]["name"] == "ice_30cm"
    loaded = client.post("/api/measurements/ice_30cm/load").json()
    assert loaded["points"] == 226


def test_sweep_requires_connection(client):
    assert client.post("/api/sweep", json=SWEEP).status_code == 409


def test_reference_frequency_mismatch(client):
    client.post("/api/connect", json={"port": "mock"})
    client.post("/api/sweep", json=SWEEP)
    client.post("/api/references/background", json={})
    client.post("/api/sweep", json={**SWEEP, "points": 101})
    assert client.post("/api/ascan", json={}).status_code == 409
