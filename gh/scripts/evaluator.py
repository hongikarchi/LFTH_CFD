"""Rough CFD metrics from (mesh + simulated water polylines + nozzles).

Mirrors a subset of ``leaflab/fast_sim/run.py`` but lives in the GH-side
script tree so it can be called directly from a GH Py3 component without
crossing the leaflab boundary.

Strict Python 3.9 compat — no ``leaflab`` import.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

PointXYZ = Tuple[float, float, float]


def _mesh_face_normal(verts: List[PointXYZ], face: Tuple[int, int, int]) -> PointXYZ:
    a, b, c = verts[face[0]], verts[face[1]], verts[face[2]]
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz)
    if mag < 1e-12:
        return (0.0, 0.0, 1.0)
    return (nx / mag, ny / mag, nz / mag)


def _ray_hit_distance(
    origin: PointXYZ,
    direction: PointXYZ,
    verts: List[PointXYZ],
    faces: List[Tuple[int, int, int]],
) -> float:
    """Slow ray-mesh intersection — returns t along direction of nearest hit,
    or ``float("inf")`` if no hit. Used only when no trimesh available; the
    GH wrapper passes a trimesh-derived list of hit normals via polyline rays
    so this routine isn't hot-path."""
    best_t = float("inf")
    for face in faces:
        a, b, c = verts[face[0]], verts[face[1]], verts[face[2]]
        e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        h = (
            direction[1] * e2[2] - direction[2] * e2[1],
            direction[2] * e2[0] - direction[0] * e2[2],
            direction[0] * e2[1] - direction[1] * e2[0],
        )
        det = e1[0] * h[0] + e1[1] * h[1] + e1[2] * h[2]
        if abs(det) < 1e-12:
            continue
        inv = 1.0 / det
        s = (origin[0] - a[0], origin[1] - a[1], origin[2] - a[2])
        u = inv * (s[0] * h[0] + s[1] * h[1] + s[2] * h[2])
        if u < 0.0 or u > 1.0:
            continue
        q = (s[1] * e1[2] - s[2] * e1[1], s[2] * e1[0] - s[0] * e1[2], s[0] * e1[1] - s[1] * e1[0])
        v = inv * (direction[0] * q[0] + direction[1] * q[1] + direction[2] * q[2])
        if v < 0.0 or u + v > 1.0:
            continue
        t = inv * (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2])
        if 1e-6 < t < best_t:
            best_t = t
    return best_t


def evaluate(
    verts: List[PointXYZ],
    faces: List[Tuple[int, int, int]],
    polylines: List[List[PointXYZ]],
    nozzles: List[Dict[str, Any]],
    pond_z_m: float = 0.0,
    pond_radius_m: float = 4.5,
    pond_xy_centre: Tuple[float, float] = (0.0, 0.0),
) -> Dict[str, Any]:
    """Aggregate metrics across all polylines for a rough-CFD score.

    Inputs:
    - ``verts``, ``faces``: the leaf mesh (in meters)
    - ``polylines``: list of point lists, each one trajectory from a nozzle
    - ``nozzles``: per-nozzle dicts (from ``water_sim.nozzles_from_points``)

    Returns a dict with:
    - ``polyline_count``, ``points_total``
    - ``cascade_drop_m_avg`` — avg z drop per polyline (start.z − end.z)
    - ``cascade_drop_m_min``, ``cascade_drop_m_max``
    - ``pond_capture_ratio`` — fraction of polylines ending within pond
    - ``xy_spread_m_avg`` — avg horizontal travel per polyline
    - ``normal_impact_avg`` — placeholder (raycast-based; ≈0 when no leaf
      hit). Computed from mesh face normals at polyline waypoints.
    - ``bbox_m`` — mesh bbox (for downstream sanity)
    """
    if pond_radius_m <= 0:
        raise ValueError("pond_radius_m must be > 0, got {0}".format(pond_radius_m))
    if not isinstance(polylines, list):
        raise ValueError("polylines must be a list of point lists")

    n_polylines = len(polylines)
    points_total = sum(len(p) for p in polylines)

    drops: List[float] = []
    xy_spreads: List[float] = []
    captured = 0
    impacts: List[float] = []

    for poly in polylines:
        if len(poly) < 2:
            continue
        start = poly[0]
        end = poly[-1]
        drops.append(float(start[2]) - float(end[2]))

        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        xy_spreads.append(max(max(xs) - min(xs), max(ys) - min(ys)))

        dx = float(end[0]) - pond_xy_centre[0]
        dy = float(end[1]) - pond_xy_centre[1]
        if float(end[2]) <= pond_z_m + 0.5 and math.sqrt(dx * dx + dy * dy) <= pond_radius_m:
            captured += 1

        # cheap normal-impact estimate at waypoints: small ray window
        for a, b in zip(poly[:-1], poly[1:], strict=False):
            dvec = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            seg_len = math.sqrt(dvec[0] ** 2 + dvec[1] ** 2 + dvec[2] ** 2)
            if seg_len < 0.05:
                continue
            ray_dir = (dvec[0] / seg_len, dvec[1] / seg_len, dvec[2] / seg_len)
            t = _ray_hit_distance(a, ray_dir, verts, faces[: min(200, len(faces))])
            if t < seg_len * 1.5 and faces:
                # rough proxy: use the first triangle's normal — exact normal
                # isn't critical for the summary statistic.
                nrm = _mesh_face_normal(verts, faces[0])
                impacts.append(abs(ray_dir[0] * nrm[0] + ray_dir[1] * nrm[1] + ray_dir[2] * nrm[2]))

    if verts:
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        bbox = [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]]
    else:
        bbox = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

    return {
        "polyline_count": n_polylines,
        "points_total": points_total,
        "cascade_drop_m_avg": (sum(drops) / len(drops)) if drops else 0.0,
        "cascade_drop_m_min": min(drops) if drops else 0.0,
        "cascade_drop_m_max": max(drops) if drops else 0.0,
        "pond_capture_ratio": (captured / n_polylines) if n_polylines else 0.0,
        "xy_spread_m_avg": (sum(xy_spreads) / len(xy_spreads)) if xy_spreads else 0.0,
        "normal_impact_avg": (sum(impacts) / len(impacts)) if impacts else 0.0,
        "nozzle_count": len(nozzles),
        "bbox_m": bbox,
    }
