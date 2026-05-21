from __future__ import annotations

import math

import numpy as np
import trimesh

from leaflab.fast_sim.impact_angle import raycast_first_contact
from leaflab.fast_sim.particle_drop import sample_water_curtain
from leaflab.fast_sim.sliding import (
    _boundary_segments,
    _min_dist_to_segments,
    slide_along_surface,
)


def _curtain(n: int = 100, seed: int = 7) -> object:
    return sample_water_curtain(
        inner_radius_m=0.5,
        outer_radius_m=2.0,
        release_z_m=20.0,
        fall_height_m=15.0,
        n=n,
        seed=seed,
    )


def test_boundary_segments_flat(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    bnd = _boundary_segments(mesh_flat_horizontal)
    assert bnd.shape == (4, 2, 3), f"expected 4 boundary edges, got {bnd.shape}"


def test_boundary_segments_closed_cylinder(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    """Tapered cylinder open at top + bottom (no caps) → 2*n_theta boundary edges."""
    bnd = _boundary_segments(mesh_cylinder_tapered)
    assert bnd.shape[0] == 2 * 24
    assert bnd.shape[1:] == (2, 3)


def test_min_dist_to_segments_simple() -> None:
    seg = np.array([[[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]])
    pts = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [2.0, 0.0, 0.0],
            [-2.0, 0.0, 0.0],
        ]
    )
    d = _min_dist_to_segments(pts, seg)
    assert np.allclose(d, [0.0, 1.0, 1.0, 1.0])


def test_horizontal_plane_no_motion(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    """On a horizontal plane, tangent gravity = 0 + tangent v_init = 0 → no slide."""
    field = _curtain(n=50)
    imp = raycast_first_contact(mesh_flat_horizontal, field)
    res = slide_along_surface(
        mesh_flat_horizontal,
        imp,
        n_steps=50,
        velocity_floor_mps=0.01,
    )
    valid = imp.hit_mask
    assert np.allclose(res.arc_length_m[valid], 0.0, atol=1e-6)
    assert not res.off_edge[valid].any()


def test_tilted_plane_slides_downhill_and_escapes(
    mesh_tilted_30: trimesh.Trimesh,
) -> None:
    """On a 30° plane, particles accelerate downhill and exit via boundary."""
    field = _curtain(n=20, seed=3)
    v_init_z = -math.sqrt(2 * 9.81 * 15.0)
    imp = raycast_first_contact(mesh_tilted_30, field)
    res = slide_along_surface(
        mesh_tilted_30,
        imp,
        n_steps=400,
        dt_s=0.01,
        boundary_tol_m=0.1,
        initial_velocity_z=v_init_z,
    )
    valid = imp.hit_mask
    assert valid.any(), "no impacts on tilted plane"
    arcs = res.arc_length_m[valid]
    assert (arcs > 0.5).all(), f"expected sliding, arcs={arcs}"
    # at 17m/s tangent + tilted, particles should reach boundary
    assert res.off_edge[valid].mean() > 0.5


def test_cylinder_smoke(mesh_cylinder_tapered: trimesh.Trimesh) -> None:
    field = _curtain(n=100, seed=11)
    v_init_z = -math.sqrt(2 * 9.81 * 15.0)
    imp = raycast_first_contact(mesh_cylinder_tapered, field)
    res = slide_along_surface(
        mesh_cylinder_tapered,
        imp,
        n_steps=100,
        initial_velocity_z=v_init_z,
    )
    assert res.endpoints.shape == (100, 3)
    assert res.arc_length_m.shape == (100,)
    assert not np.isnan(res.arc_length_m).any()
    assert (res.steps_taken >= 0).all()


def test_shapes_and_dtypes(mesh_flat_horizontal: trimesh.Trimesh) -> None:
    field = _curtain(n=32)
    imp = raycast_first_contact(mesh_flat_horizontal, field)
    res = slide_along_surface(mesh_flat_horizontal, imp, n_steps=10)
    assert res.endpoints.shape == (32, 3)
    assert res.arc_length_m.shape == (32,)
    assert res.off_edge.shape == (32,)
    assert res.steps_taken.shape == (32,)
    assert res.active_at_end.shape == (32,)
    assert res.off_edge.dtype == np.bool_
    assert res.steps_taken.dtype == np.int64
