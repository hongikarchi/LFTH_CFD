"""Curvature-gradient-weighted splash proxy.

A face whose normal differs sharply from its neighbours is treated as a
detachment / splash risk site. The proxy combines this geometric quantity
with the local impact severity (`normal_impact**2`), giving a single scalar
per mesh that scales with both surface roughness and incident pressure.
"""

from __future__ import annotations

import numpy as np
import trimesh
from numpy.typing import NDArray

from leaflab.fast_sim.impact_angle import ImpactResult


def per_face_curvature_gradient(mesh: trimesh.Trimesh) -> NDArray[np.float64]:
    """Average angle (radians) between each face normal and its edge-neighbours."""
    n_faces = len(mesh.faces)
    if n_faces == 0:
        return np.zeros(0, dtype=np.float64)
    adj: NDArray[np.int64] = np.asarray(mesh.face_adjacency, dtype=np.int64)
    angles: NDArray[np.float64] = np.asarray(mesh.face_adjacency_angles, dtype=np.float64)
    if adj.shape[0] == 0:
        return np.zeros(n_faces, dtype=np.float64)

    sums = np.zeros(n_faces, dtype=np.float64)
    counts = np.zeros(n_faces, dtype=np.int64)
    np.add.at(sums, adj[:, 0], angles)
    np.add.at(sums, adj[:, 1], angles)
    np.add.at(counts, adj[:, 0], 1)
    np.add.at(counts, adj[:, 1], 1)
    denom = np.maximum(counts, 1)
    return sums / denom


def curvature_gradient_mean(mesh: trimesh.Trimesh, impact: ImpactResult) -> float:
    """Mean per-face curvature gradient at the particle impact points."""
    if not impact.hit_mask.any():
        return 0.0
    face_curv = per_face_curvature_gradient(mesh)
    valid_face_ids = impact.face_ids[impact.hit_mask]
    return float(face_curv[valid_face_ids].mean())


def splash_score(mesh: trimesh.Trimesh, impact: ImpactResult) -> float:
    """Curvature gradient at impact site × normal-impact² (∈ [0, ∞))."""
    if not impact.hit_mask.any():
        return 0.0
    face_curv = per_face_curvature_gradient(mesh)
    valid_mask = impact.hit_mask
    face_curv_at_hit = face_curv[impact.face_ids[valid_mask]]
    normal_imp = impact.normal_impact[valid_mask]
    return float((face_curv_at_hit * normal_imp**2).mean())
