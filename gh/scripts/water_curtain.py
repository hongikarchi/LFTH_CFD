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


def _solve_fall_time(vz: float, fall_height_m: float, gravity_mps2: float) -> float:
    """Time for a particle with vertical velocity vz to drop by fall_height_m.

    Solves ``0.5 g t^2 - vz t - fall_height = 0`` for the positive root.
    """
    disc = vz * vz + 2.0 * gravity_mps2 * fall_height_m
    if disc < 0:
        # gravity > 0 ensures disc > 0; defensive only
        return math.sqrt(2.0 * fall_height_m / gravity_mps2)
    return (vz + math.sqrt(disc)) / gravity_mps2


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
    t = _solve_fall_time(vz, fall_height_m, gravity_mps2)
    return (sx + vx * t, sy + vy * t, sz - fall_height_m)


def fall_trajectory_polyline(
    start_xyz_m: PointXYZ,
    fall_height_m: float,
    velocity_mps: Optional[PointXYZ] = None,
    gravity_mps2: float = 9.81,
    n_samples: int = 16,
) -> List[PointXYZ]:
    """Sample N positions along the free-fall trajectory in meters.

    Index 0 = start_xyz_m. Last index ≈ landing point at
    z = start.z - fall_height_m. Parabolic curve when velocity_mps has
    horizontal components; straight vertical line otherwise.
    """
    if n_samples < 2:
        raise ValueError("n_samples must be >= 2, got {0}".format(n_samples))
    if fall_height_m <= 0:
        raise ValueError("fall_height_m must be > 0, got {0}".format(fall_height_m))
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0, got {0}".format(gravity_mps2))
    sx, sy, sz = start_xyz_m
    if velocity_mps is None:
        vx, vy, vz = 0.0, 0.0, 0.0
    else:
        vx, vy, vz = velocity_mps[0], velocity_mps[1], velocity_mps[2]
    t_end = _solve_fall_time(vz, fall_height_m, gravity_mps2)
    out: List[PointXYZ] = []
    for i in range(n_samples):
        frac = i / float(n_samples - 1)
        t = t_end * frac
        x = sx + vx * t
        y = sy + vy * t
        z = sz + vz * t - 0.5 * gravity_mps2 * t * t
        out.append((x, y, z))
    return out


# ---------------------------------------------------------------------------
# simulate_water_path_polyline — multi-bounce raycast through a trimesh
# ---------------------------------------------------------------------------


def _vec_add(a: PointXYZ, b: PointXYZ) -> PointXYZ:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(a: PointXYZ, b: PointXYZ) -> PointXYZ:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(a: PointXYZ, s: float) -> PointXYZ:
    return (a[0] * s, a[1] * s, a[2] * s)


def _vec_dot(a: PointXYZ, b: PointXYZ) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_norm(a: PointXYZ) -> float:
    return math.sqrt(_vec_dot(a, a))


def _vec_unit(a: PointXYZ) -> PointXYZ:
    mag = _vec_norm(a)
    if mag < 1e-12:
        return (0.0, 0.0, -1.0)
    return (a[0] / mag, a[1] / mag, a[2] / mag)


def _free_fall_sample(
    start: PointXYZ,
    velocity: PointXYZ,
    gravity_mps2: float,
    duration_s: float,
    n_samples: int,
) -> List[PointXYZ]:
    """Sample positions along projectile motion from start with initial velocity."""
    out: List[PointXYZ] = []
    for i in range(1, n_samples + 1):
        t = duration_s * i / n_samples
        out.append(
            (
                start[0] + velocity[0] * t,
                start[1] + velocity[1] * t,
                start[2] + velocity[2] * t - 0.5 * gravity_mps2 * t * t,
            )
        )
    return out


def simulate_water_path_polyline(
    start_xyz_m: PointXYZ,
    velocity_mps: PointXYZ,
    mesh: Any,
    gravity_mps2: float = 9.81,
    max_bounces: int = 8,
    n_samples_per_segment: int = 6,
    slide_initial_speed_factor: float = 0.10,
    slide_horizontal_splash_speed: float = 0.5,
    pond_z_m: float = 0.0,
    pos_offset_m: float = 1.0e-3,
) -> List[PointXYZ]:
    """Trace water cascading through a trimesh — always slides downhill.

    Specular bounces are physically inappropriate for water on leaves
    (water splashes / sheets, never rebounds upward). At each hit we
    compute the surface's gravity-tangent direction (which way "downhill"
    points on this triangle) and redirect water along it, with speed
    scaled by the incoming kinetic energy.

    For a near-horizontal surface where gravity is mostly absorbed by
    the normal, we add a small horizontal splash outward from the world
    z-axis so the water doesn't stall.

    No hit → free-fall to ``z = pond_z_m``, sample the parabola, stop.
    """
    if max_bounces < 1:
        raise ValueError("max_bounces must be >= 1, got {0}".format(max_bounces))
    if n_samples_per_segment < 1:
        raise ValueError("n_samples_per_segment must be >= 1")
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0")
    if not 0.0 <= slide_initial_speed_factor <= 1.0:
        raise ValueError("slide_initial_speed_factor must be in [0, 1]")

    pos = (
        float(start_xyz_m[0]),
        float(start_xyz_m[1]),
        float(start_xyz_m[2]),
    )
    vel = (
        float(velocity_mps[0]),
        float(velocity_mps[1]),
        float(velocity_mps[2]),
    )
    points: List[PointXYZ] = [pos]
    rmi = mesh.ray

    for bounce_idx in range(max_bounces):
        if pos[2] <= pond_z_m + 0.05:
            break
        speed = _vec_norm(vel)
        if speed < 1e-6:
            break
        # First ray: use input velocity direction (water enters from nozzle).
        # Subsequent rays after slide: shoot DOWNWARD (waterfall — gravity
        # dominates descent between leaves; slide is the local kick only).
        ray_dir = _vec_unit(vel) if bounce_idx == 0 else (0.0, 0.0, -1.0)

        # ray-mesh intersection — find nearest hit along ray
        try:
            import numpy as _np  # numpy available alongside trimesh

            origins = _np.asarray([pos], dtype=float)
            dirs = _np.asarray([ray_dir], dtype=float)
            locs, idx_ray, idx_tri = rmi.intersects_location(
                ray_origins=origins,
                ray_directions=dirs,
                multiple_hits=False,
            )
        except Exception:
            locs = []
            idx_tri = []

        if len(locs) == 0:
            # no hit — free-fall down to pond
            if pos[2] <= pond_z_m:
                break
            t_end = _solve_fall_time(vel[2], pos[2] - pond_z_m, gravity_mps2)
            points.extend(_free_fall_sample(pos, vel, gravity_mps2, t_end, n_samples_per_segment))
            break

        hit_point = (float(locs[0][0]), float(locs[0][1]), float(locs[0][2]))
        face_idx = int(idx_tri[0])
        normal_raw = mesh.face_normals[face_idx]
        normal = (float(normal_raw[0]), float(normal_raw[1]), float(normal_raw[2]))
        normal_unit = _vec_unit(normal)
        # orient normal against incoming ray (so n · -v_hat > 0)
        if _vec_dot(normal_unit, ray_dir) > 0.0:
            normal_unit = (-normal_unit[0], -normal_unit[1], -normal_unit[2])

        # sample trajectory from pos to hit_point under gravity (parabola)
        delta = _vec_sub(hit_point, pos)
        seg_len = _vec_norm(delta)
        if seg_len > 1e-9:
            # approximate time-to-hit by projecting onto current speed direction
            t_hit = seg_len / max(speed, 1e-6)
            points.extend(_free_fall_sample(pos, vel, gravity_mps2, t_hit, n_samples_per_segment))

        # always slide downhill — tangent of gravity on this triangle's plane
        g_vec: PointXYZ = (0.0, 0.0, -gravity_mps2)
        g_dot_n = _vec_dot(g_vec, normal_unit)
        g_tan = (
            g_vec[0] - g_dot_n * normal_unit[0],
            g_vec[1] - g_dot_n * normal_unit[1],
            g_vec[2] - g_dot_n * normal_unit[2],
        )
        g_tan_mag = _vec_norm(g_tan)

        slide_speed = speed * slide_initial_speed_factor
        if g_tan_mag > 0.5:
            slide_dir = (
                g_tan[0] / g_tan_mag,
                g_tan[1] / g_tan_mag,
                g_tan[2] / g_tan_mag,
            )
            new_vel = _vec_scale(slide_dir, slide_speed)
        else:
            xy_r = math.sqrt(hit_point[0] * hit_point[0] + hit_point[1] * hit_point[1])
            if xy_r > 1e-3:
                slide_dir = (hit_point[0] / xy_r, hit_point[1] / xy_r, -0.1)
            else:
                slide_dir = (1.0, 0.0, -0.1)
            slide_dir = _vec_unit(slide_dir)
            new_vel = _vec_scale(slide_dir, slide_horizontal_splash_speed)

        # advance position along slide direction by `slide_step_m` so the next
        # ray-cast escapes the current leaf's coverage (otherwise water hits
        # the same face infinitely). slide_step ≈ leaf radius so one slide takes
        # water roughly from center to edge.
        slide_step_m = 1.5
        slide_end = (
            hit_point[0] + slide_dir[0] * slide_step_m,
            hit_point[1] + slide_dir[1] * slide_step_m,
            hit_point[2] + slide_dir[2] * slide_step_m,
        )
        # offset above surface so next ray doesn't snag the leaf we just left
        new_pos = (
            slide_end[0] + normal_unit[0] * pos_offset_m,
            slide_end[1] + normal_unit[1] * pos_offset_m,
            slide_end[2] + normal_unit[2] * pos_offset_m,
        )
        points.append(new_pos)
        pos = new_pos
        vel = new_vel

        if pos[2] <= pond_z_m:
            break

    # ensure polyline ends at or below pond_z to look like it reaches water
    if points[-1][2] > pond_z_m + 0.05 and _vec_norm(vel) > 1e-6:
        t_end = _solve_fall_time(vel[2], points[-1][2] - pond_z_m, gravity_mps2)
        points.extend(
            _free_fall_sample(points[-1], vel, gravity_mps2, t_end, n_samples_per_segment)
        )

    return points
