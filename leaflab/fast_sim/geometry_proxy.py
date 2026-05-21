"""Geometry-side proxy metrics computed directly from the mesh."""

from __future__ import annotations

import numpy as np
import trimesh

from leaflab.schema.metrics_schema import GeometryProxyMetrics


def _boundary_edge_count(mesh: trimesh.Trimesh) -> int:
    edges = np.sort(mesh.edges, axis=1)
    _u, inverse, counts = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    return int((counts[inverse] == 1).sum())


def _rim_continuity(mesh: trimesh.Trimesh) -> float:
    """1.0 = fully closed; ratio of non-boundary edges to total."""
    total = mesh.edges.shape[0]
    if total == 0:
        return 0.0
    open_count = _boundary_edge_count(mesh)
    return float(1.0 - open_count / total)


def compute_geometry_proxy(mesh: trimesh.Trimesh) -> GeometryProxyMetrics:
    """Cheap geometric metrics — area, volume, curvature stats, continuity heuristics."""
    bbox = np.asarray(mesh.bounds, dtype=np.float64)
    height_total_m = float(bbox[1, 2] - bbox[0, 2])
    surface_area_m2 = float(mesh.area)

    if mesh.is_watertight:
        volume_estimate_m3 = float(abs(mesh.volume))
    else:
        try:
            volume_estimate_m3 = float(abs(mesh.convex_hull.volume))
        except Exception:
            volume_estimate_m3 = 0.0

    adj_angles = np.asarray(mesh.face_adjacency_angles, dtype=np.float64)
    if adj_angles.size == 0:
        mean_gauss = 0.0
        mean_curv_var = 0.0
    else:
        mean_gauss = float(adj_angles.mean())
        mean_curv_var = float(adj_angles.std())

    rim = _rim_continuity(mesh)
    channel = 0.5  # placeholder, calibrate Phase D

    return GeometryProxyMetrics(
        height_total_m=height_total_m,
        surface_area_m2=surface_area_m2,
        volume_estimate_m3=volume_estimate_m3,
        mean_gaussian_curvature=mean_gauss,
        mean_curvature_variation=mean_curv_var,
        rim_continuity_score=rim,
        channel_continuity_score=channel,
    )
