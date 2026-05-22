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
    max_bounces: int = 12,
    n_samples_per_segment: int = 6,
    slide_initial_speed_factor: float = 0.20,
    slide_horizontal_splash_speed: float = 0.8,
    slide_substeps: int = 5,
    slide_substep_dt_s: float = 0.05,
    bounce_threshold: float = 0.75,
    bounce_loss: float = 0.18,
    pond_z_m: float = 0.0,
    pos_offset_m: float = 1.0e-3,
) -> List[PointXYZ]:
    """Trace water cascading through a trimesh — rough CFD-style.

    At each hit, compute `normal_impact = |v_hat · n|`:

    - **normal_impact ≥ bounce_threshold** (~head-on): specular bounce
      `v -= 2(v·n) n`, scaled by `bounce_loss`. Water visibly reflects
      off the surface (rare, only on highly perpendicular hits).
    - **else** (grazing): surface-trace slide — `slide_substeps` micro
      iterations along the local gravity-tangent direction, each
      advancing position by `vel · slide_substep_dt_s`. Velocity
      accumulates tangent gravity. After substeps, water is presumed
      to leave the leaf edge and free-falls to next raycast.

    Polyline samples capture the trajectory shape (parabolic between
    hits, multi-point along each slide).

    Termination: pond reached, max_bounces hit, or zero velocity.
    """
    if max_bounces < 1:
        raise ValueError("max_bounces must be >= 1, got {0}".format(max_bounces))
    if n_samples_per_segment < 1:
        raise ValueError("n_samples_per_segment must be >= 1")
    if slide_substeps < 1:
        raise ValueError("slide_substeps must be >= 1")
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0")
    if not 0.0 <= slide_initial_speed_factor <= 1.0:
        raise ValueError("slide_initial_speed_factor must be in [0, 1]")
    if not 0.0 <= bounce_threshold <= 1.0:
        raise ValueError("bounce_threshold must be in [0, 1]")
    if not 0.0 <= bounce_loss <= 1.0:
        raise ValueError("bounce_loss must be in [0, 1]")

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
    _after_bounce = False

    for bounce_idx in range(max_bounces):
        if pos[2] <= pond_z_m + 0.05:
            break
        speed = _vec_norm(vel)
        if speed < 1e-6:
            break
        # First ray: input velocity direction (water from nozzle).
        # After slide: shoot straight down (waterfall — gravity dominates
        # between leaves). After specular bounce: follow reflected velocity
        # direction (which is set by `_after_bounce` flag below).
        ray_dir = _vec_unit(vel) if (bounce_idx == 0 or _after_bounce) else (0.0, 0.0, -1.0)
        _after_bounce = False

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
            # Fallback for ray-through-apex hollow: if first ray from
            # near-axis nozzle misses entirely, retry with tiny xy offset
            # so the ray bypasses the central apex degeneracy.
            if bounce_idx == 0 and len(locs) == 0 and abs(pos[0]) < 0.2 and abs(pos[1]) < 0.2:
                offset_origins = _np.asarray([[pos[0] + 0.2, pos[1] + 0.0, pos[2]]], dtype=float)
                locs, idx_ray, idx_tri = rmi.intersects_location(
                    ray_origins=offset_origins,
                    ray_directions=dirs,
                    multiple_hits=False,
                )
                if len(locs) > 0:
                    pos = (pos[0] + 0.2, pos[1], pos[2])
                    points[-1] = pos
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

        # decide: head-on bounce vs grazing slide
        v_dir = _vec_unit(vel)
        normal_impact = abs(_vec_dot(v_dir, normal_unit))

        if normal_impact >= bounce_threshold:
            # specular reflection (rare, head-on hits on tilted surfaces)
            v_dot_n = _vec_dot(vel, normal_unit)
            reflected = (
                vel[0] - 2.0 * v_dot_n * normal_unit[0],
                vel[1] - 2.0 * v_dot_n * normal_unit[1],
                vel[2] - 2.0 * v_dot_n * normal_unit[2],
            )
            new_vel = _vec_scale(reflected, bounce_loss)
            # offset along REFLECTED direction so next ray escapes this face
            refl_unit = _vec_unit(new_vel)
            new_pos = (
                hit_point[0] + refl_unit[0] * 0.5,
                hit_point[1] + refl_unit[1] * 0.5,
                hit_point[2] + refl_unit[2] * 0.5,
            )
            points.append(new_pos)
            pos = new_pos
            vel = new_vel
            _after_bounce = True  # next ray follows reflected velocity
        else:
            # surface-trace slide: tangent gravity over slide_substeps micro steps
            g_vec: PointXYZ = (0.0, 0.0, -gravity_mps2)
            g_dot_n = _vec_dot(g_vec, normal_unit)
            g_tan = (
                g_vec[0] - g_dot_n * normal_unit[0],
                g_vec[1] - g_dot_n * normal_unit[1],
                g_vec[2] - g_dot_n * normal_unit[2],
            )
            g_tan_mag = _vec_norm(g_tan)

            # initial tangent velocity from incoming v
            v_normal_comp = _vec_dot(vel, normal_unit)
            v_tan = (
                vel[0] - v_normal_comp * normal_unit[0],
                vel[1] - v_normal_comp * normal_unit[1],
                vel[2] - v_normal_comp * normal_unit[2],
            )
            v_tan_mag = _vec_norm(v_tan)

            # scale slide speed from incoming kinetic energy + add downhill kick
            base_slide_speed = max(speed * slide_initial_speed_factor, v_tan_mag * 0.5)
            if g_tan_mag > 0.3:
                slide_dir = (
                    g_tan[0] / g_tan_mag,
                    g_tan[1] / g_tan_mag,
                    g_tan[2] / g_tan_mag,
                )
            else:
                # near-horizontal — splash radially outward from world z-axis
                xy_r = math.sqrt(hit_point[0] * hit_point[0] + hit_point[1] * hit_point[1])
                if xy_r > 1e-3:
                    slide_dir = _vec_unit((hit_point[0] / xy_r, hit_point[1] / xy_r, -0.2))
                else:
                    slide_dir = (1.0, 0.0, -0.2)
                base_slide_speed = max(base_slide_speed, slide_horizontal_splash_speed)

            cur_vel = _vec_scale(slide_dir, base_slide_speed)
            cur_pos = (
                hit_point[0] + normal_unit[0] * pos_offset_m,
                hit_point[1] + normal_unit[1] * pos_offset_m,
                hit_point[2] + normal_unit[2] * pos_offset_m,
            )

            # micro slide steps — sample positions along surface tangent
            for _slide in range(slide_substeps):
                # tangent gravity acceleration
                cur_vel = (
                    cur_vel[0] + g_tan[0] * slide_substep_dt_s,
                    cur_vel[1] + g_tan[1] * slide_substep_dt_s,
                    cur_vel[2] + g_tan[2] * slide_substep_dt_s,
                )
                cur_pos = (
                    cur_pos[0] + cur_vel[0] * slide_substep_dt_s,
                    cur_pos[1] + cur_vel[1] * slide_substep_dt_s,
                    cur_pos[2] + cur_vel[2] * slide_substep_dt_s,
                )
                points.append(cur_pos)

            pos = cur_pos
            # carry tangent velocity forward — water leaves leaf edge with this v
            vel = cur_vel

        if pos[2] <= pond_z_m:
            break

    # ensure polyline ends at or below pond_z to look like it reaches water
    if points[-1][2] > pond_z_m + 0.05 and _vec_norm(vel) > 1e-6:
        t_end = _solve_fall_time(vel[2], points[-1][2] - pond_z_m, gravity_mps2)
        points.extend(
            _free_fall_sample(points[-1], vel, gravity_mps2, t_end, n_samples_per_segment)
        )

    return points


# ---------------------------------------------------------------------------
# PR-H — particle CFD: per-particle physics with elastic/diffuse/slide modes
# ---------------------------------------------------------------------------


class ParticleTrajectory(object):  # noqa: UP004  (3.9 compat — no dataclass kwonly)
    """A water droplet's trajectory through the mesh.

    Attributes:
    - points: polyline samples in METERS (world frame)
    - nozzle_id: source nozzle id
    - particle_idx: this particle's index within its nozzle
    - n_collisions: number of mesh hits
    - terminated_by: one of {"pond", "max_bounces", "stuck", "out_of_bounds"}
    """

    __slots__ = ("points", "nozzle_id", "particle_idx", "n_collisions", "terminated_by")

    def __init__(
        self,
        points,
        nozzle_id="",
        particle_idx=0,
        n_collisions=0,
        terminated_by="pond",
    ):
        self.points = points
        self.nozzle_id = nozzle_id
        self.particle_idx = particle_idx
        self.n_collisions = n_collisions
        self.terminated_by = terminated_by


def n_particles_from_flow_rate(
    flow_rate_lpm,
    base_particles_per_lpm=4.0,
    cap=200,
):
    """Map flow_rate_lpm → bounded particle count for visualisation.

    Real 45 L/min ≈ 1.5e4 droplets/s. For viz we sample a handful per
    nozzle: ``round(flow_rate * base)`` clamped to [1, cap].
    """
    if base_particles_per_lpm <= 0:
        raise ValueError("base_particles_per_lpm must be > 0")
    if cap < 1:
        raise ValueError("cap must be >= 1")
    n = int(max(1, round(flow_rate_lpm * base_particles_per_lpm)))
    return min(cap, n)


def initial_velocity_from_tilt(
    fall_height_m,
    tilt_deg,
    azimuth_deg=0.0,
    gravity_mps2=9.81,
):
    """v = sqrt(2gh) in direction (sin t cos a, sin t sin a, -cos t).

    tilt_deg=0 → straight down. tilt_deg>0 → off-vertical, azimuth picks
    the horizontal direction (0=+X, 90=+Y).
    """
    if fall_height_m <= 0:
        raise ValueError("fall_height_m must be > 0")
    if gravity_mps2 <= 0:
        raise ValueError("gravity_mps2 must be > 0")
    v_mag = math.sqrt(2.0 * gravity_mps2 * fall_height_m)
    t = math.radians(tilt_deg)
    a = math.radians(azimuth_deg)
    return (
        v_mag * math.sin(t) * math.cos(a),
        v_mag * math.sin(t) * math.sin(a),
        -v_mag * math.cos(t),
    )


def _solve_parabola_t_to_hit(pos, vel, hit, gravity_mps2):
    """Time from pos with velocity vel under -z gravity to reach hit_point.

    z(t) = pos.z + vel.z·t - ½g·t²; solve for t at z = hit.z.
    Use the larger positive root (post-bounce trajectories also valid).
    Fallback to straight-line t when discriminant < 0 (numerical).
    """
    dz = hit[2] - pos[2]
    a = -0.5 * gravity_mps2
    b = vel[2]
    c = -dz
    disc = b * b - 4.0 * a * c
    if disc < 0 or abs(a) < 1e-12:
        seg = math.sqrt((hit[0] - pos[0]) ** 2 + (hit[1] - pos[1]) ** 2 + dz * dz)
        speed = math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2)
        return seg / max(speed, 1e-6)
    sqrt_d = math.sqrt(disc)
    t1 = (-b + sqrt_d) / (2.0 * a)
    t2 = (-b - sqrt_d) / (2.0 * a)
    candidates = [t for t in (t1, t2) if t > 1e-9]
    return min(candidates) if candidates else 1e-6


def _random_unit_in_cone(rng, axis_unit, cone_half_angle_rad):
    """Sample a unit vector within `cone_half_angle_rad` of `axis_unit`.

    Uniform over the solid-angle cap. Used for diffuse-bounce scatter.
    """
    cos_max = math.cos(cone_half_angle_rad)
    u1 = rng.random()
    u2 = rng.random()
    cos_theta = 1.0 - u1 * (1.0 - cos_max)
    sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta))
    phi = 2.0 * math.pi * u2
    # local frame around axis
    az = axis_unit
    ref = (0.0, 0.0, 1.0) if abs(az[2]) < 0.99 else (1.0, 0.0, 0.0)
    bx = _vec_unit(_vec_sub(ref, _vec_scale(az, _vec_dot(az, ref))))
    by = (
        az[1] * bx[2] - az[2] * bx[1],
        az[2] * bx[0] - az[0] * bx[2],
        az[0] * bx[1] - az[1] * bx[0],
    )
    return (
        bx[0] * sin_theta * math.cos(phi) + by[0] * sin_theta * math.sin(phi) + az[0] * cos_theta,
        bx[1] * sin_theta * math.cos(phi) + by[1] * sin_theta * math.sin(phi) + az[1] * cos_theta,
        bx[2] * sin_theta * math.cos(phi) + by[2] * sin_theta * math.sin(phi) + az[2] * cos_theta,
    )


def simulate_particle(
    mesh,
    start_xyz_m,
    velocity_mps,
    gravity_mps2=9.81,
    max_bounces=20,
    pond_z_m=0.0,
    n_samples_per_segment=8,
    elastic_speed_threshold_mps=8.0,
    slide_speed_threshold_mps=1.5,
    restitution_elastic=0.65,
    restitution_diffuse=0.45,
    diffuse_cone_deg=30.0,
    slide_step_s=0.10,
    slide_max_steps=8,
    pos_offset_m=1.0e-3,
    rng_seed=0,
    nozzle_id="",
    particle_idx=0,
):
    """One water droplet, particle-CFD physics.

    Per segment: raycast → sample parabolic travel → collide. Collision
    mode chosen from impact speed:
    - speed > elastic_threshold → specular reflection (with restitution)
    - elastic ≥ speed > slide_threshold → diffuse cone scatter
    - speed ≤ slide_threshold → surface slide under tangent gravity

    Termination: pond reached, no-hit free-fall to pond, bounce limit, or
    zero velocity (terminated_by="stuck"/"pond"/...).
    """
    import random as _random

    rng = _random.Random(rng_seed)
    pos = (float(start_xyz_m[0]), float(start_xyz_m[1]), float(start_xyz_m[2]))
    vel = (float(velocity_mps[0]), float(velocity_mps[1]), float(velocity_mps[2]))
    points = [pos]
    n_collisions = 0
    terminated_by = "max_bounces"

    g_vec = (0.0, 0.0, -gravity_mps2)
    rmi = mesh.ray

    for _ in range(max_bounces):
        if pos[2] <= pond_z_m + 0.05:
            terminated_by = "pond"
            break
        speed = _vec_norm(vel)
        if speed < 1e-6:
            terminated_by = "stuck"
            break
        ray_dir = _vec_unit(vel)

        # raycast
        try:
            import numpy as _np

            locs, idx_ray, idx_tri = rmi.intersects_location(
                ray_origins=_np.asarray([pos], dtype=float),
                ray_directions=_np.asarray([ray_dir], dtype=float),
                multiple_hits=False,
            )
        except Exception:
            locs = []
            idx_tri = []

        if len(locs) == 0:
            # free-fall to pond, sample parabola
            if pos[2] <= pond_z_m:
                terminated_by = "pond"
                break
            t_end = _solve_fall_time(vel[2], pos[2] - pond_z_m, gravity_mps2)
            points.extend(_free_fall_sample(pos, vel, gravity_mps2, t_end, n_samples_per_segment))
            terminated_by = "pond"
            break

        hit_point = (float(locs[0][0]), float(locs[0][1]), float(locs[0][2]))
        face_idx = int(idx_tri[0])
        normal_raw = mesh.face_normals[face_idx]
        normal_unit = _vec_unit((float(normal_raw[0]), float(normal_raw[1]), float(normal_raw[2])))
        if _vec_dot(normal_unit, ray_dir) > 0.0:
            normal_unit = (-normal_unit[0], -normal_unit[1], -normal_unit[2])

        # time to hit under gravity → sample parabolic travel
        t_hit = _solve_parabola_t_to_hit(pos, vel, hit_point, gravity_mps2)
        points.extend(_free_fall_sample(pos, vel, gravity_mps2, t_hit, n_samples_per_segment))

        # velocity at impact (post-gravity)
        v_at_hit = (
            vel[0] + g_vec[0] * t_hit,
            vel[1] + g_vec[1] * t_hit,
            vel[2] + g_vec[2] * t_hit,
        )
        speed_at_hit = _vec_norm(v_at_hit)
        n_dot_v = _vec_dot(v_at_hit, normal_unit)
        n_collisions += 1

        if speed_at_hit > elastic_speed_threshold_mps:
            # SPECULAR
            v_refl = (
                v_at_hit[0] - 2.0 * n_dot_v * normal_unit[0],
                v_at_hit[1] - 2.0 * n_dot_v * normal_unit[1],
                v_at_hit[2] - 2.0 * n_dot_v * normal_unit[2],
            )
            new_vel = _vec_scale(v_refl, restitution_elastic)
            new_pos = (
                hit_point[0] + normal_unit[0] * pos_offset_m,
                hit_point[1] + normal_unit[1] * pos_offset_m,
                hit_point[2] + normal_unit[2] * pos_offset_m,
            )
            points.append(new_pos)
            pos = new_pos
            vel = new_vel
        elif speed_at_hit > slide_speed_threshold_mps:
            # DIFFUSE scatter in cone around normal
            scatter_unit = _random_unit_in_cone(rng, normal_unit, math.radians(diffuse_cone_deg))
            new_vel = _vec_scale(scatter_unit, speed_at_hit * restitution_diffuse)
            new_pos = (
                hit_point[0] + normal_unit[0] * pos_offset_m,
                hit_point[1] + normal_unit[1] * pos_offset_m,
                hit_point[2] + normal_unit[2] * pos_offset_m,
            )
            points.append(new_pos)
            pos = new_pos
            vel = new_vel
        else:
            # SURFACE FLOW — slide along gravity tangent
            g_dot_n = _vec_dot(g_vec, normal_unit)
            g_tan = (
                g_vec[0] - g_dot_n * normal_unit[0],
                g_vec[1] - g_dot_n * normal_unit[1],
                g_vec[2] - g_dot_n * normal_unit[2],
            )
            v_normal_comp = _vec_dot(v_at_hit, normal_unit)
            v_tan = (
                v_at_hit[0] - v_normal_comp * normal_unit[0],
                v_at_hit[1] - v_normal_comp * normal_unit[1],
                v_at_hit[2] - v_normal_comp * normal_unit[2],
            )
            cur_vel = v_tan
            cur_pos = (
                hit_point[0] + normal_unit[0] * pos_offset_m,
                hit_point[1] + normal_unit[1] * pos_offset_m,
                hit_point[2] + normal_unit[2] * pos_offset_m,
            )
            for _step in range(slide_max_steps):
                cur_vel = (
                    cur_vel[0] + g_tan[0] * slide_step_s,
                    cur_vel[1] + g_tan[1] * slide_step_s,
                    cur_vel[2] + g_tan[2] * slide_step_s,
                )
                cur_pos = (
                    cur_pos[0] + cur_vel[0] * slide_step_s,
                    cur_pos[1] + cur_vel[1] * slide_step_s,
                    cur_pos[2] + cur_vel[2] * slide_step_s,
                )
                points.append(cur_pos)
                if cur_pos[2] <= pond_z_m + 0.05:
                    break
            pos = cur_pos
            vel = cur_vel
            if _vec_norm(vel) < 1e-3:
                terminated_by = "stuck"
                break

        if pos[2] <= pond_z_m:
            terminated_by = "pond"
            break

    # ensure polyline ends near pond
    if points[-1][2] > pond_z_m + 0.05 and _vec_norm(vel) > 1e-6:
        t_end = _solve_fall_time(vel[2], points[-1][2] - pond_z_m, gravity_mps2)
        points.extend(
            _free_fall_sample(points[-1], vel, gravity_mps2, t_end, n_samples_per_segment)
        )

    return ParticleTrajectory(
        points=points,
        nozzle_id=nozzle_id,
        particle_idx=particle_idx,
        n_collisions=n_collisions,
        terminated_by=terminated_by,
    )


def simulate_water_curtain(
    mesh,
    nozzle_points_m,
    flow_rate_lpm,
    tilt_deg,
    azimuth_deg,
    fall_height_m=15.0,
    gravity_mps2=9.81,
    nozzle_jitter_m=0.05,
    rng_seed=42,
    base_particles_per_lpm=4.0,
    particle_cap=200,
    **sim_kwargs,
):
    """Per-nozzle batch: n_particles_from_flow_rate(flow) particles per nozzle.

    Each particle starts at nozzle.position with small disc jitter
    (`nozzle_jitter_m`), velocity from `initial_velocity_from_tilt`.
    Returns list of ParticleTrajectory.
    """
    import random as _random

    rng = _random.Random(rng_seed)
    n_per = n_particles_from_flow_rate(
        flow_rate_lpm,
        base_particles_per_lpm=base_particles_per_lpm,
        cap=particle_cap,
    )
    v0 = initial_velocity_from_tilt(
        fall_height_m=fall_height_m,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        gravity_mps2=gravity_mps2,
    )
    trajectories = []
    for nz_idx, nz_pos in enumerate(nozzle_points_m):
        nz_id = "n{0}".format(nz_idx)
        for p_idx in range(n_per):
            # disc jitter (area-uniform)
            u = rng.random()
            theta = rng.uniform(0.0, 2.0 * math.pi)
            r = nozzle_jitter_m * math.sqrt(u)
            jp = (
                float(nz_pos[0]) + r * math.cos(theta),
                float(nz_pos[1]) + r * math.sin(theta),
                float(nz_pos[2]),
            )
            traj = simulate_particle(
                mesh,
                jp,
                v0,
                gravity_mps2=gravity_mps2,
                nozzle_id=nz_id,
                particle_idx=p_idx,
                rng_seed=rng_seed + nz_idx * 1000 + p_idx,
                **sim_kwargs,
            )
            trajectories.append(traj)
    return trajectories
