from __future__ import annotations

import math

import numpy as np
import pytest
import trimesh

from leaflab.fast_sim.drain_target import evaluate_drain
from leaflab.fast_sim.geometry_proxy import compute_geometry_proxy
from leaflab.fast_sim.impact_angle import raycast_first_contact
from leaflab.fast_sim.particle_drop import sample_water_curtain
from leaflab.fast_sim.splash_proxy import (
    curvature_gradient_mean,
    per_face_curvature_gradient,
    splash_score,
)


def _curtain(n: int = 50, seed: int = 9) -> object:
    return sample_water_curtain(
        inner_radius_m=0.5,
        outer_radius_m=2.0,
        release_z_m=20.0,
        fall_height_m=15.0,
        n=n,
        seed=seed,
    )


# ---- splash_proxy ----------------------------------------------------------


def test_per_face_curvature_flat(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    """A flat planar mesh has zero face-adjacency angle → curvature = 0."""
    c = per_face_curvature_gradient(mesh_flat_horizontal)
    assert c.shape == (mesh_flat_horizontal.faces.shape[0],)
    assert np.allclose(c, 0.0, atol=1e-9)


def test_per_face_curvature_cylinder_positive(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    c = per_face_curvature_gradient(mesh_cylinder_tapered)
    assert (c >= 0).all()
    assert c.mean() > 0.0


def test_splash_score_no_hits_returns_zero(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    far = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    far.apply_translation([100.0, 100.0, 0.0])
    field = _curtain(n=20)
    imp = raycast_first_contact(far, field)
    assert splash_score(far, imp) == 0.0
    assert curvature_gradient_mean(far, imp) == 0.0


def test_splash_score_flat_zero(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    field = _curtain()
    imp = raycast_first_contact(mesh_flat_horizontal, field)
    assert splash_score(mesh_flat_horizontal, imp) == 0.0


def test_splash_score_cylinder_positive(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    field = _curtain(n=200)
    imp = raycast_first_contact(mesh_cylinder_tapered, field)
    s = splash_score(mesh_cylinder_tapered, imp)
    assert s > 0.0
    assert math.isfinite(s)


# ---- drain_target ----------------------------------------------------------


def test_drain_target_capture_pattern() -> None:
    pts = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
            [0.0, -2.0, 5.0],
        ]
    )
    res = evaluate_drain(pts, target_xyz=(0.0, 0.0, 0.0), pond_radius_m=2.5)
    assert res.captured.tolist() == [True, True, False, True]
    assert np.allclose(res.distance_to_target_m, [0.0, 1.0, 3.0, 2.0])


def test_drain_target_zero_radius_raises() -> None:
    with pytest.raises(ValueError):
        evaluate_drain(np.zeros((1, 3)), (0.0, 0.0, 0.0), 0.0)


# ---- geometry_proxy --------------------------------------------------------


def test_geom_proxy_cylinder_values(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    g = compute_geometry_proxy(mesh_cylinder_tapered)
    assert math.isclose(g.height_total_m, 14.0, abs_tol=1e-6)
    assert g.surface_area_m2 > 0
    assert g.volume_estimate_m3 > 0
    assert 0.0 <= g.rim_continuity_score <= 1.0
    assert g.channel_continuity_score == 0.5
    assert g.mean_gaussian_curvature >= 0
    assert g.mean_curvature_variation >= 0


def test_geom_proxy_flat_zero_curvature(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    g = compute_geometry_proxy(mesh_flat_horizontal)
    assert g.surface_area_m2 == 100.0
    assert math.isclose(g.mean_gaussian_curvature, 0.0, abs_tol=1e-9)
    assert math.isclose(g.mean_curvature_variation, 0.0, abs_tol=1e-9)


def test_geom_proxy_closed_box_rim_one() -> None:
    box = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
    g = compute_geometry_proxy(box)
    assert math.isclose(g.rim_continuity_score, 1.0, abs_tol=1e-9)
    assert g.volume_estimate_m3 == pytest.approx(8.0, abs=1e-6)
