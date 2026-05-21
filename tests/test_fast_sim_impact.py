from __future__ import annotations

import math

import numpy as np
import trimesh

from leaflab.fast_sim.impact_angle import raycast_first_contact
from leaflab.fast_sim.particle_drop import sample_water_curtain


def _curtain(n: int = 200, seed: int = 7) -> object:
    return sample_water_curtain(
        inner_radius_m=0.5,
        outer_radius_m=2.0,
        release_z_m=20.0,
        fall_height_m=15.0,
        n=n,
        seed=seed,
    )


def test_horizontal_plane_head_on(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    field = _curtain()
    res = raycast_first_contact(mesh_flat_horizontal, field)
    assert res.hit_mask.all(), f"misses on horizontal plane: {(~res.hit_mask).sum()}"
    assert np.allclose(res.hit_points[:, 2], 0.0, atol=1e-9)
    valid = res.normal_impact[res.hit_mask]
    assert np.allclose(valid, 1.0, atol=1e-9), f"expected 1.0, got {valid.min()}..{valid.max()}"


def test_tilted_plane_normal_impact(mesh_tilted_30: trimesh.Trimesh) -> None:
    field = _curtain()
    res = raycast_first_contact(mesh_tilted_30, field)
    assert res.hit_mask.all(), f"misses on tilted plane: {(~res.hit_mask).sum()}"
    expected = math.cos(math.radians(30.0))
    valid = res.normal_impact[res.hit_mask]
    assert np.allclose(valid, expected, atol=1e-6), (
        f"expected {expected}, got min={valid.min()} max={valid.max()}"
    )


def test_total_miss_marks_all_false() -> None:
    """Place mesh far away from particle column → all rays miss."""
    far = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    far.apply_translation([100.0, 100.0, 0.0])
    field = _curtain(n=50)
    res = raycast_first_contact(far, field)
    assert not res.hit_mask.any()
    assert np.all(res.face_ids == -1)
    assert np.isnan(res.hit_points).all()
    assert np.isnan(res.normal_impact).all()


def test_normal_impact_bounded_unit(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    field = _curtain(n=300)
    res = raycast_first_contact(mesh_cylinder_tapered, field)
    valid = res.normal_impact[res.hit_mask]
    assert (valid >= 0.0).all()
    assert (valid <= 1.0 + 1e-9).all()


def test_shapes(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    field = _curtain(n=128)
    res = raycast_first_contact(mesh_flat_horizontal, field)
    assert res.hit_mask.shape == (128,)
    assert res.hit_points.shape == (128, 3)
    assert res.hit_normals.shape == (128, 3)
    assert res.face_ids.shape == (128,)
    assert res.normal_impact.shape == (128,)
    assert res.hit_mask.dtype == np.bool_
    assert res.face_ids.dtype == np.int64


def test_zero_velocity_raises(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    from dataclasses import replace as _r  # noqa: F401  (just to keep import sane)

    from leaflab.fast_sim.particle_drop import ParticleField

    pos = np.array([[0.0, 0.0, 5.0]], dtype=np.float64)
    vel = np.zeros((1, 3), dtype=np.float64)
    bad = ParticleField(positions=pos, velocities=vel, seed=0)
    import pytest

    with pytest.raises(ValueError, match="zero-magnitude"):
        raycast_first_contact(mesh_flat_horizontal, bad)
