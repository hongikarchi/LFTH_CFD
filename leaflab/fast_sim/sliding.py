"""Tangent-gravity flow integration + boundary edge escape detection.

Each particle that hit the mesh continues along the surface: at every step
the tangent component of gravity accelerates the particle while the normal
component is absorbed (idealised stick-slip — no rebound). When the position
drifts off the surface it is snapped back via `trimesh.proximity.closest_point`,
and we re-read the local face normal.

Termination per particle: (a) crossed a boundary edge → `off_edge=True`;
(b) speed below `velocity_floor_mps`; (c) `n_steps` exhausted.

Arc length is the integrated surface-projected travel — used as the
`attachment_length_m` proxy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import trimesh
from numpy.typing import NDArray

from leaflab.fast_sim.impact_angle import ImpactResult


@dataclass(frozen=True, eq=False)
class SlidingResult:
    endpoints: NDArray[np.float64]
    arc_length_m: NDArray[np.float64]
    off_edge: NDArray[np.bool_]
    steps_taken: NDArray[np.int64]
    active_at_end: NDArray[np.bool_]


def _boundary_segments(mesh: trimesh.Trimesh) -> NDArray[np.float64]:
    """Return (M, 2, 3) vertex coordinates of mesh boundary edges (count == 1)."""
    edges = np.sort(mesh.edges, axis=1)
    _unique, inverse, counts = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    bnd_mask = counts[inverse] == 1
    bnd_edges = edges[bnd_mask]
    if bnd_edges.size == 0:
        return np.empty((0, 2, 3), dtype=np.float64)
    bnd_edges_unique = np.unique(bnd_edges, axis=0)
    return np.asarray(mesh.vertices[bnd_edges_unique], dtype=np.float64)


def _min_dist_to_segments(
    points: NDArray[np.float64], segments: NDArray[np.float64]
) -> NDArray[np.float64]:
    """For each point, min distance to any line segment. Vectorised."""
    n = points.shape[0]
    if segments.shape[0] == 0:
        return np.full(n, np.inf, dtype=np.float64)
    a = segments[:, 0, :]
    b = segments[:, 1, :]
    ab = b - a
    ab_len_sq = np.einsum("mk,mk->m", ab, ab)
    ab_len_sq = np.where(ab_len_sq == 0, 1e-12, ab_len_sq)

    p = points[:, None, :]
    ap = p - a[None, :, :]
    t = np.einsum("nmk,mk->nm", ap, ab) / ab_len_sq[None, :]
    t = np.clip(t, 0.0, 1.0)
    closest = a[None, :, :] + t[..., None] * ab[None, :, :]
    diff = p - closest
    dists = np.linalg.norm(diff, axis=2)
    return np.asarray(dists.min(axis=1), dtype=np.float64)


def slide_along_surface(
    mesh: trimesh.Trimesh,
    impact: ImpactResult,
    *,
    n_steps: int = 200,
    dt_s: float = 0.01,
    gravity_mps2: float = 9.81,
    velocity_floor_mps: float = 0.05,
    boundary_tol_m: float = 0.02,
    initial_velocity_z: float | None = None,
) -> SlidingResult:
    """Integrate tangent flow for every particle that hit the surface."""
    n = impact.hit_mask.shape[0]
    pos = np.where(impact.hit_mask[:, None], impact.hit_points, 0.0).astype(np.float64)
    face_ids = np.where(impact.hit_mask, impact.face_ids, 0).astype(np.int64)

    v_init_z = -1.0 if initial_velocity_z is None else float(initial_velocity_z)
    v_in = np.zeros((n, 3), dtype=np.float64)
    v_in[:, 2] = v_init_z
    n_hit_for_proj = np.where(
        impact.hit_mask[:, None], impact.hit_normals, np.array([0.0, 0.0, 1.0])
    )
    normal_component = np.einsum("ij,ij->i", v_in, n_hit_for_proj)[:, None] * n_hit_for_proj
    velocity = v_in - normal_component

    arc = np.zeros(n, dtype=np.float64)
    off_edge = np.zeros(n, dtype=bool)
    steps_taken = np.zeros(n, dtype=np.int64)
    active = impact.hit_mask.copy()

    bnd = _boundary_segments(mesh)
    g_vec = np.array([0.0, 0.0, -gravity_mps2], dtype=np.float64)
    face_normals: NDArray[np.float64] = np.asarray(mesh.face_normals, dtype=np.float64)

    for step in range(n_steps):
        if not active.any():
            break
        idx = np.where(active)[0]
        n_curr = face_normals[face_ids[idx]]

        g_dot_n = np.einsum("ij,j->i", n_curr, g_vec)[:, None]
        g_tan = g_vec[None, :] - g_dot_n * n_curr
        velocity[idx] += g_tan * dt_s

        v_dot_n = np.einsum("ij,ij->i", velocity[idx], n_curr)[:, None]
        velocity[idx] -= v_dot_n * n_curr

        step_vec = velocity[idx] * dt_s
        proposed = pos[idx] + step_vec

        snapped_any: Any = trimesh.proximity.closest_point(mesh, proposed)
        snapped, _dist_to_mesh, snapped_face = snapped_any
        snapped = np.asarray(snapped, dtype=np.float64)
        snapped_face = np.asarray(snapped_face, dtype=np.int64)

        travelled = np.linalg.norm(snapped - pos[idx], axis=1)
        arc[idx] += travelled
        pos[idx] = snapped
        face_ids[idx] = snapped_face
        steps_taken[idx] = step + 1

        if bnd.shape[0] > 0:
            d_bnd = _min_dist_to_segments(pos[idx], bnd)
            off_now = d_bnd < boundary_tol_m
        else:
            off_now = np.zeros(idx.shape[0], dtype=bool)
        speed = np.linalg.norm(velocity[idx], axis=1)
        slow_now = speed < velocity_floor_mps

        terminate = off_now | slow_now
        if terminate.any():
            stop_indices = idx[terminate]
            off_edge[stop_indices] = off_now[terminate]
            active[stop_indices] = False

    return SlidingResult(
        endpoints=pos,
        arc_length_m=arc,
        off_edge=off_edge,
        steps_taken=steps_taken,
        active_at_end=active,
    )
