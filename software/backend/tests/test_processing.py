import numpy as np

from app import processing
from app.touchstone import read_touchstone, write_s2p
from app.vna import MockVNA, SweepSettings

WIDE = SweepSettings(0.75e9, 3.0e9, 226)


def _ice_sweeps(distance=0.5, thickness=0.25, settings=WIDE):
    vna = MockVNA(seed=1)
    vna.set_scene(kind="sky")
    sky = vna.sweep(settings)
    vna.set_scene(kind="plate", distance_m=distance)
    plate = vna.sweep(settings)
    vna.set_scene(kind="ice", distance_m=distance, ice_thickness_m=thickness)
    ice = vna.sweep(settings)
    return sky, plate, ice


def test_thickness_recovered_with_background():
    sky, _, ice = _ice_sweeps(thickness=0.25)
    out = processing.ascan(ice.freq_hz, ice.s11, background=sky.s11, eps_r=3.2)
    p = out["picks"]
    assert p is not None and p["thickness_m"] is not None
    assert abs(p["thickness_m"] - 0.25) < 0.01
    assert abs(p["surface_ns"] - 2 * 0.5 / processing.C0 * 1e9) < 0.1


def test_eps_from_plate_reference():
    sky, plate, ice = _ice_sweeps(thickness=0.30)
    out = processing.ascan(ice.freq_hz, ice.s11, background=sky.s11, plate=plate.s11)
    p = out["picks"]
    assert p["eps_source"] == "plate"
    assert abs(p["eps_r"] - 3.2) < 0.3
    assert abs(p["thickness_m"] - 0.30) < 0.02


def test_warns_without_background():
    _, _, ice = _ice_sweeps()
    out = processing.ascan(ice.freq_hz, ice.s11)
    assert any("background" in w.lower() for w in out["warnings"])


def test_swr_of_matched_and_mismatched():
    assert np.isclose(processing.swr(np.array([0.0]))[0], 1.0)
    assert np.isclose(processing.swr(np.array([1 / 3]))[0], 2.0)


def test_touchstone_roundtrip(tmp_path):
    _, _, ice = _ice_sweeps()
    p = tmp_path / "x.s2p"
    write_s2p(p, ice.freq_hz, ice.s11, ice.s21, comments=["test"])
    f, s11, s21 = read_touchstone(p)
    assert np.allclose(f, ice.freq_hz)
    assert np.allclose(s11, ice.s11, rtol=1e-6, atol=1e-12)
    assert np.allclose(s21, ice.s21, rtol=1e-6, atol=1e-12)
