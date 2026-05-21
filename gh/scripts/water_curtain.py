"""Doc-unit point list -> nozzle dicts + free-fall endpoint helper.

Used by gh/LeafGenerator.gh build component. Runs inside Rhino 8's
embedded CPython 3.9 - MUST NOT import ``leaflab`` and MUST avoid 3.10+
syntax (use Optional/List/Tuple/Dict from typing, no PEP 604 unions).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

PointXYZ = Tuple[float, float, float]


def nozzles_from_points(
    points_xyz_doc: List[PointXYZ],
    flow_rate_lpm: float,
    doc_to_m: float = 1.0,
    velocity_mps_shared: Optional[PointXYZ] = None,
) -> List[Dict[str, Any]]:
    """Convert Rhino doc-unit points to nozzle dicts with positions in meters.

    ``doc_to_m`` is the scale to convert one doc unit to one meter
    (e.g. 0.001 for mm-doc, 1.0 for m-doc). Each nozzle gets
    ``flow_rate_lpm`` as its flow rate.

    ``velocity_mps_shared`` (optional) is one velocity vector applied
    to every nozzle. ``None`` keeps per-nozzle velocity_mps = None so
    the downstream sim defaults to pure vertical free-fall.
    """
    if flow_rate_lpm <= 0:
        raise ValueError("flow_rate_lpm must be > 0, got {0}".format(flow_rate_lpm))
    if velocity_mps_shared is not None:
        vel: Optional[List[float]] = [
            float(velocity_mps_shared[0]),
            float(velocity_mps_shared[1]),
            float(velocity_mps_shared[2]),
        ]
    else:
        vel = None
    out: List[Dict[str, Any]] = []
    for i, (x, y, z) in enumerate(points_xyz_doc):
        out.append(
            {
                "position": [x * doc_to_m, y * doc_to_m, z * doc_to_m],
                "flow_rate_lpm": float(flow_rate_lpm),
                "velocity_mps": list(vel) if vel is not None else None,
                "nozzle_id": "n{0}".format(i),
            }
        )
    return out


def velocity_from_tilt(
    fall_height_m: float,
    tilt_deg: float,
    azimuth_deg: float = 0.0,
    gravity_mps2: float = 9.81,
) -> PointXYZ:
    """Initial velocity vector for a nozzle tilted ``tilt_deg`` from vertical.

    Magnitude = ``sqrt(2 g h)`` (post-fall equivalent). ``tilt_deg=0``
    returns straight down; positive ``tilt_deg`` lifts the vector
    toward the horizon in the ``azimuth_deg`` direction (0 = +X, 90 = +Y).
    """
    if fall_height_m <= 0:
        raise ValueError("fall_height_m must be > 0, got {0}".format(fall_height_m))
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0, got {0}".format(gravity_mps2))
    v_mag = math.sqrt(2.0 * gravity_mps2 * fall_height_m)
    tilt_rad = math.radians(tilt_deg)
    az_rad = math.radians(azimuth_deg)
    horiz = v_mag * math.sin(tilt_rad)
    vx = horiz * math.cos(az_rad)
    vy = horiz * math.sin(az_rad)
    vz = -v_mag * math.cos(tilt_rad)
    return (vx, vy, vz)


def fall_trajectory_endpoint(
    start_xyz_m: PointXYZ,
    fall_height_m: float,
    velocity_mps: Optional[PointXYZ] = None,
    gravity_mps2: float = 9.81,
) -> PointXYZ:
    """End-of-fall point in meters.

    Vertical free-fall by default. With horizontal velocity components,
    computes proper parabolic endpoint at z = start.z - fall_height_m
    (drop time solved from quadratic, then x/y advanced).
    """
    if fall_height_m <= 0:
        raise ValueError("fall_height_m must be > 0, got {0}".format(fall_height_m))
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0, got {0}".format(gravity_mps2))
    sx, sy, sz = start_xyz_m
    if velocity_mps is None or (velocity_mps[0] == 0.0 and velocity_mps[1] == 0.0):
        return (sx, sy, sz - fall_height_m)
    vx, vy, vz = velocity_mps
    # z(t) = sz + vz*t - 0.5*g*t^2 ; solve for t at z = sz - fall_height
    # 0.5*g*t^2 - vz*t - fall_height = 0  =>  t = (vz + sqrt(vz^2 + 2g*h)) / g
    disc = vz * vz + 2.0 * gravity_mps2 * fall_height_m
    if disc < 0:
        return (sx, sy, sz - fall_height_m)
    t = (vz + math.sqrt(disc)) / gravity_mps2
    return (sx + vx * t, sy + vy * t, sz - fall_height_m)
