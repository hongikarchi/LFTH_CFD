from __future__ import annotations

import math

import numpy as np
import pytest

from leaflab.fast_sim.particle_drop import (
    ParticleField,
    particle_field_from_params,
    sample_water_curtain,
)
from leaflab.schema.params_schema import load_params

INNER = 1.0
OUTER = 2.0
RELEASE_Z = 29.5
FALL_H = 15.0
G = 9.81
N = 500


def _sample(**overrides: object) -> ParticleField:
    kwargs: dict[str, object] = {
        "inner_radius_m": INNER,
        "outer_radius_m": OUTER,
        "release_z_m": RELEASE_Z,
        "fall_height_m": FALL_H,
        "n": N,
        "gravity_mps2": G,
        "seed": 42,
    }
    kwargs.update(overrides)
    return sample_water_curtain(**kwargs)  # type: ignore[arg-type]


def test_shapes_and_dtypes() -> None:
    f = _sample()
    assert f.positions.shape == (N, 3)
    assert f.velocities.shape == (N, 3)
    assert f.positions.dtype == np.float64
    assert f.velocities.dtype == np.float64
    assert f.seed == 42


def test_determinism_same_seed() -> None:
    a = _sample(seed=7)
    b = _sample(seed=7)
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.velocities, b.velocities)


def test_determinism_different_seed() -> None:
    a = _sample(seed=1)
    b = _sample(seed=2)
    assert not np.array_equal(a.positions, b.positions)


def test_annulus_bounds() -> None:
    f = _sample()
    r = np.hypot(f.positions[:, 0], f.positions[:, 1])
    tol = 1e-9
    assert (r >= INNER - tol).all(), f"min r = {r.min()} < {INNER}"
    assert (r <= OUTER + tol).all(), f"max r = {r.max()} > {OUTER}"


def test_release_height_constant() -> None:
    f = _sample()
    assert np.all(f.positions[:, 2] == RELEASE_Z)


def test_velocity_vector() -> None:
    f = _sample()
    v_expected = -math.sqrt(2 * G * FALL_H)
    assert np.all(f.velocities[:, 0] == 0.0)
    assert np.all(f.velocities[:, 1] == 0.0)
    assert np.allclose(f.velocities[:, 2], v_expected, atol=1e-12)


def test_area_uniform_distribution() -> None:
    """Inner-half-area vs outer-half-area particle count should match area ratio (~50/50)."""
    f = _sample(n=20000, seed=123)
    r = np.hypot(f.positions[:, 0], f.positions[:, 1])
    r_mid = math.sqrt((INNER**2 + OUTER**2) / 2.0)
    inner_half = float(np.mean(r < r_mid))
    assert 0.45 < inner_half < 0.55, f"area-uniform sampling skewed: {inner_half}"


@pytest.mark.parametrize(
    "kw,exc",
    [
        ({"n": 0}, ValueError),
        ({"n": -1}, ValueError),
        ({"inner_radius_m": -0.1}, ValueError),
        ({"outer_radius_m": 1.0, "inner_radius_m": 1.0}, ValueError),
        ({"outer_radius_m": 0.5, "inner_radius_m": 1.0}, ValueError),
        ({"fall_height_m": 0.0}, ValueError),
        ({"fall_height_m": -1.0}, ValueError),
        ({"gravity_mps2": 0.0}, ValueError),
    ],
)
def test_invalid_inputs(kw: dict[str, object], exc: type[Exception]) -> None:
    with pytest.raises(exc):
        _sample(**kw)


def test_from_params(sample_params_dict: dict[str, object]) -> None:
    params = load_params(sample_params_dict)
    f = particle_field_from_params(params, n=100, seed=1)
    assert f.positions.shape == (100, 3)
    assert f.velocities.shape == (100, 3)
    # release_z = top_leaf_z_m + fall_height_m = 14.2 + 15.0 = 29.2
    assert np.all(f.positions[:, 2] == 14.2 + 15.0)
    v_expected = -math.sqrt(2 * 9.81 * 15.0)
    assert np.allclose(f.velocities[:, 2], v_expected, atol=1e-12)
    r = np.hypot(f.positions[:, 0], f.positions[:, 1])
    assert (r >= 1.0 - 1e-9).all()
    assert (r <= 2.0 + 1e-9).all()


def test_particle_field_from_nozzles_shape() -> None:
    from leaflab.fast_sim.particle_drop import particle_field_from_nozzles
    from leaflab.schema.params_schema import NozzleParams

    nozzles = [
        NozzleParams(
            position=(0.0, 0.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n0"
        ),
        NozzleParams(
            position=(1.0, 0.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n1"
        ),
        NozzleParams(
            position=(0.0, 1.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n2"
        ),
    ]
    field = particle_field_from_nozzles(nozzles, fall_height_m=15.0, n_per_nozzle=20, seed=1)
    assert field.positions.shape == (60, 3)
    assert field.velocities.shape == (60, 3)


def test_particle_field_from_nozzles_clustered_per_nozzle() -> None:
    """Each block of n_per_nozzle particles clusters near its nozzle."""
    from leaflab.fast_sim.particle_drop import particle_field_from_nozzles
    from leaflab.schema.params_schema import NozzleParams

    nozzles = [
        NozzleParams(
            position=(0.0, 0.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n0"
        ),
        NozzleParams(
            position=(5.0, 0.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n1"
        ),
    ]
    field = particle_field_from_nozzles(
        nozzles, fall_height_m=15.0, n_per_nozzle=50, jitter_m=0.05, seed=2
    )
    # within each 50-particle block, positions stay close to that nozzle
    for nz_i, nz in enumerate(nozzles):
        block = field.positions[nz_i * 50 : (nz_i + 1) * 50]
        dxy = block[:, :2] - np.array(nz.position[:2])
        d = np.linalg.norm(dxy, axis=1)
        assert (d <= 0.05 + 1e-9).all(), (
            f"nozzle {nz_i}: particle drift exceeds jitter, max={d.max()}"
        )
        assert np.allclose(block[:, 2], nz.position[2])


def test_particle_field_from_nozzles_determinism() -> None:
    from leaflab.fast_sim.particle_drop import particle_field_from_nozzles
    from leaflab.schema.params_schema import NozzleParams

    nozzles = [
        NozzleParams(
            position=(0.0, 0.0, 15.0), flow_rate_lpm=45.0, velocity_mps=None, nozzle_id="n0"
        ),
    ]
    a = particle_field_from_nozzles(nozzles, fall_height_m=15.0, n_per_nozzle=30, seed=42)
    b = particle_field_from_nozzles(nozzles, fall_height_m=15.0, n_per_nozzle=30, seed=42)
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.velocities, b.velocities)


def test_particle_field_from_params_dispatches_to_nozzles(
    sample_params_dict: dict,
) -> None:
    sample_params_dict["water"]["nozzles"] = [
        {
            "position": [0.0, 0.0, 20.0],
            "flow_rate_lpm": 45.0,
            "velocity_mps": None,
            "nozzle_id": "n0",
        },
        {
            "position": [3.0, 0.0, 20.0],
            "flow_rate_lpm": 45.0,
            "velocity_mps": None,
            "nozzle_id": "n1",
        },
    ]
    params = load_params(sample_params_dict)
    field = particle_field_from_params(params, n=40, seed=7)
    # 40 // 2 nozzles = 20 per nozzle => 40 total
    assert field.positions.shape == (40, 3)
    # all positions stay near the two nozzle XY centres, NOT on the annulus
    dxy_0 = np.linalg.norm(field.positions[:20, :2] - np.array([0.0, 0.0]), axis=1)
    dxy_1 = np.linalg.norm(field.positions[20:, :2] - np.array([3.0, 0.0]), axis=1)
    assert (dxy_0 < 0.5).all()
    assert (dxy_1 < 0.5).all()


def test_particle_field_from_params_falls_back_to_annulus(
    sample_params_dict: dict,
) -> None:
    """When nozzles is None, annulus sampling is used."""
    params = load_params(sample_params_dict)
    assert params.water.nozzles is None
    field = particle_field_from_params(params, n=100, seed=3)
    r = np.hypot(field.positions[:, 0], field.positions[:, 1])
    assert (r >= 1.0 - 1e-9).all()
    assert (r <= 2.0 + 1e-9).all()
