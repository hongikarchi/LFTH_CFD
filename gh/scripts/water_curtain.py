"""Doc-unit point list -> nozzle dicts + free-fall endpoint helper.

Used by gh/LeafGenerator.gh build component. Runs inside Rhino 8's
embedded CPython 3.9 - MUST NOT import leaflab and MUST avoid 3.10+
syntax (use Optional/List/Tuple/Dict from typing, no PEP 604 unions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

PointXYZ = Tuple[float, float, float]


def nozzles_from_points(
    points_xyz_doc: List[PointXYZ],
    flow_rate_lpm: float,
    doc_to_m: float = 1.0,
) -> List[Dict[str, Any]]:
    """Convert Rhino doc-unit points to nozzle dicts with positions in meters.

    ``doc_to_m`` is the scale to convert one doc unit to one meter
    (e.g. 0.001 for mm-doc, 1.0 for m-doc). Each nozzle gets
    ``flow_rate_lpm`` as its flow rate; velocity is None (downstream
    sim defaults to vertical free-fall).
    """
    if flow_rate_lpm <= 0:
        raise ValueError("flow_rate_lpm must be > 0, got {0}".format(flow_rate_lpm))
    out: List[Dict[str, Any]] = []
    for i, (x, y, z) in enumerate(points_xyz_doc):
        out.append({
            "position": [x * doc_to_m, y * doc_to_m, z * doc_to_m],
            "flow_rate_lpm": float(flow_rate_lpm),
            "velocity_mps": None,
            "nozzle_id": "n{0}".format(i),
        })
    return out


def fall_trajectory_endpoint(
    start_xyz_m: PointXYZ,
    fall_height_m: float,
    velocity_mps: Optional[PointXYZ] = None,
    gravity_mps2: float = 9.81,
) -> PointXYZ:
    """End-of-fall point in meters.

    Vertical free-fall by default. If ``velocity_mps`` has horizontal
    components, parabolic projection is OUT OF SCOPE today - falls back
    to vertical drop endpoint.
    """
    if fall_height_m <= 0:
        raise ValueError("fall_height_m must be > 0, got {0}".format(fall_height_m))
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0, got {0}".format(gravity_mps2))
    sx, sy, sz = start_xyz_m
    # vertical drop default; oblique trajectories deferred (FIXME: parabolic)
    if velocity_mps is None or (velocity_mps[0] == 0.0 and velocity_mps[1] == 0.0):
        return (sx, sy, sz - fall_height_m)
    return (sx, sy, sz - fall_height_m)
