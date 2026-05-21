"""Raycast each particle straight down to find the first surface contact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import trimesh
from numpy.typing import NDArray

from leaflab.fast_sim.particle_drop import ParticleField


@dataclass(frozen=True, eq=False)
class ImpactResult:
    hit_mask: NDArray[np.bool_]
    hit_points: NDArray[np.float64]
    hit_normals: NDArray[np.float64]
    face_ids: NDArray[np.int64]
    normal_impact: NDArray[np.float64]


def raycast_first_contact(mesh: trimesh.Trimesh, field: ParticleField) -> ImpactResult:
    """Shoot each particle along its velocity direction; record first hit.

    Misses are encoded as `hit_mask=False`, with NaN positions/normals/impact
    and face_id = -1. Hit normals are taken from `mesh.face_normals` (mesh's
    own outward orientation); `normal_impact = |v_dir . n|` so closer to 1 =
    head-on, 0 = grazing.
    """
    n = field.positions.shape[0]
    speeds = np.linalg.norm(field.velocities, axis=1, keepdims=True)
    if (speeds == 0).any():
        raise ValueError("zero-magnitude velocity in particle field")
    directions = field.velocities / speeds

    rmi: Any = trimesh.ray.ray_triangle.RayMeshIntersector(mesh)
    locations, index_ray, index_tri = rmi.intersects_location(
        ray_origins=field.positions,
        ray_directions=directions,
        multiple_hits=False,
    )

    hit_mask = np.zeros(n, dtype=bool)
    hit_points = np.full((n, 3), np.nan, dtype=np.float64)
    hit_normals = np.full((n, 3), np.nan, dtype=np.float64)
    face_ids = np.full(n, -1, dtype=np.int64)
    normal_impact = np.full(n, np.nan, dtype=np.float64)

    if len(index_ray) > 0:
        idx_ray = np.asarray(index_ray, dtype=np.int64)
        idx_tri = np.asarray(index_tri, dtype=np.int64)
        locs = np.asarray(locations, dtype=np.float64)
        hit_mask[idx_ray] = True
        hit_points[idx_ray] = locs
        face_ids[idx_ray] = idx_tri
        normals = np.asarray(mesh.face_normals[idx_tri], dtype=np.float64)
        hit_normals[idx_ray] = normals
        dot = np.einsum("ij,ij->i", directions[idx_ray], normals)
        normal_impact[idx_ray] = np.abs(dot)

    return ImpactResult(
        hit_mask=hit_mask,
        hit_points=hit_points,
        hit_normals=hit_normals,
        face_ids=face_ids,
        normal_impact=normal_impact,
    )
