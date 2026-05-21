"""Phase B MVP geometry generator for `gh/LeafGenerator.gh`.

Pure Python (3.9-compatible) + numpy. Produces a triangle mesh as
``(vertices, faces)`` and a params dict suitable for
:func:`gh.scripts.export_candidate.export_candidate`.

This is an MVP for end-to-end pipeline verification — geometry is a stacked,
tapered, twisted cylinder, NOT a true leaf form. Real leaf geometry is Phase
C/D work (see ``big_leaf_water_generator_plan.md`` §9).

This module must remain importable inside Rhino 8's embedded CPython 3.9
(GH ``Python 3 Script`` component). It MUST NOT import ``leaflab`` and MUST
NOT use 3.10+ syntax.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

Vertex = Tuple[float, float, float]
TriFace = Tuple[int, int, int]


def build_mvp_mesh(
    height_total_m: float,
    landing_radius_m: float,
    twist_total_deg: float,
    n_z: int = 12,
    n_theta: int = 24,
) -> Tuple[List[Vertex], List[TriFace]]:
    """Build a tapered + twisted cylinder mesh as (vertices, triangle faces).

    Tapers from ``landing_radius_m`` at z=0 down to 40 % at the top, and
    twists linearly over the height. Caller converts to RhinoCommon Mesh or
    feeds straight into ``export_candidate``.
    """
    if height_total_m <= 0:
        raise ValueError("height_total_m must be > 0")
    if landing_radius_m <= 0:
        raise ValueError("landing_radius_m must be > 0")
    if n_z < 2 or n_theta < 3:
        raise ValueError("n_z >= 2 and n_theta >= 3 required")

    verts: List[Vertex] = []
    for i in range(n_z):
        z_frac = i / (n_z - 1)
        z = z_frac * height_total_m
        r = landing_radius_m * (1.0 - 0.6 * z_frac)
        twist = math.radians(twist_total_deg) * z_frac
        for j in range(n_theta):
            a = (2.0 * math.pi * j / n_theta) + twist
            verts.append((r * math.cos(a), r * math.sin(a), z))

    faces: List[TriFace] = []
    for i in range(n_z - 1):
        for j in range(n_theta):
            a = i * n_theta + j
            b = i * n_theta + ((j + 1) % n_theta)
            c = (i + 1) * n_theta + ((j + 1) % n_theta)
            d = (i + 1) * n_theta + j
            faces.append((a, b, c))
            faces.append((a, c, d))
    return verts, faces


# Layout per leaf: (z_frac, length_factor, camber_factor, rim_h_factor,
#                   pitch_deg, twist_offset_frac)
_LEAF_SPECS: List[Tuple[float, float, float, float, float, float]] = [
    (0.95, 1.6, 0.20, 0.08, 14.0, 0.0),  # L1 landing — top, large
    (0.55, 1.1, 0.16, 0.06, 24.0, 0.4),  # L2 flow — mid
    (0.20, 0.75, 0.12, 0.04, 35.0, 0.75),  # L3 discharge — bottom
]


def build_real_leaf_mesh(
    height_total_m: float,
    landing_radius_m: float,
    twist_total_deg: float,
    n_u: int = 12,
    n_theta: int = 24,
) -> Tuple[List[Vertex], List[TriFace]]:
    """3-leaf dome stack: each leaf is an ellipsoidal cap with rim curl.

    Same three slider inputs as ``build_mvp_mesh`` so the existing GH
    wrappers stay compatible. Mesh is the union of three independent
    leaf surfaces (L1 landing, L2 flow, L3 discharge), each tilted by
    its own pitch and offset by a fraction of the global twist.
    """
    if height_total_m <= 0:
        raise ValueError("height_total_m must be > 0")
    if landing_radius_m <= 0:
        raise ValueError("landing_radius_m must be > 0")
    if n_u < 2 or n_theta < 3:
        raise ValueError("n_u >= 2 and n_theta >= 3 required")

    all_verts: List[Vertex] = []
    all_faces: List[TriFace] = []

    for (
        z_frac,
        length_factor,
        camber_factor,
        rim_h_factor,
        pitch_deg,
        twist_offset_frac,
    ) in _LEAF_SPECS:
        a = landing_radius_m * length_factor  # ellipse semi-major (m)
        b = a * 0.7  # semi-minor (aspect)
        camber_m = camber_factor * a
        rim_m = rim_h_factor * a
        z_offset = z_frac * height_total_m
        twist_rad = math.radians(twist_total_deg * (z_frac + twist_offset_frac))
        pitch_rad = math.radians(pitch_deg)
        cp = math.cos(pitch_rad)
        sp = math.sin(pitch_rad)
        ct = math.cos(twist_rad)
        st = math.sin(twist_rad)

        base_idx = len(all_verts)
        for i in range(n_u):
            u = i / float(n_u - 1)  # 0 = centre, 1 = edge
            for j in range(n_theta):
                theta = 2.0 * math.pi * j / n_theta
                x_e = a * u * math.cos(theta)
                y_e = b * u * math.sin(theta)
                z_dome = camber_m * (1.0 - u * u)
                rim_frac = max(0.0, (u - 0.85) / 0.15)
                z_rim = rim_m * rim_frac * rim_frac
                z_local = z_dome + z_rim
                # pitch about world Y-axis (rotates x and z)
                x_p = x_e * cp + z_local * sp
                z_p = -x_e * sp + z_local * cp
                # global twist about world Z-axis (rotates x and y)
                x_g = x_p * ct - y_e * st
                y_g = x_p * st + y_e * ct
                all_verts.append((x_g, y_g, z_offset + z_p))

        for i in range(n_u - 1):
            for j in range(n_theta):
                a_i = base_idx + i * n_theta + j
                b_i = base_idx + i * n_theta + ((j + 1) % n_theta)
                c_i = base_idx + (i + 1) * n_theta + ((j + 1) % n_theta)
                d_i = base_idx + (i + 1) * n_theta + j
                all_faces.append((a_i, b_i, c_i))
                all_faces.append((a_i, c_i, d_i))

    return all_verts, all_faces


# ---------------------------------------------------------------------------
# build_leaf_v2_mesh — plan §9 pipeline (spine + zones + profile + rim + channel)
# ---------------------------------------------------------------------------

# (t_center, t_half_width, length_factor, width_aspect, camber_factor,
#  rim_h_factor, channel_depth_factor, channel_width_sigma)
_LEAF_V2_ZONES: List[Tuple[float, float, float, float, float, float, float, float]] = [
    (0.92, 0.08, 1.6, 0.70, 0.20, 0.08, 0.06, 0.30),  # L1 landing — large bowl
    (0.55, 0.13, 1.1, 0.65, 0.16, 0.06, 0.05, 0.28),  # L2 flow — mid
    (0.18, 0.10, 0.75, 0.60, 0.12, 0.04, 0.04, 0.26),  # L3 discharge
]


def _bezier_point(t: float, cps: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Cubic Bezier position at parameter t given 4 control points."""
    u = 1.0 - t
    u2 = u * u
    t2 = t * t
    b0 = u2 * u
    b1 = 3.0 * u2 * t
    b2 = 3.0 * u * t2
    b3 = t2 * t
    return (
        b0 * cps[0][0] + b1 * cps[1][0] + b2 * cps[2][0] + b3 * cps[3][0],
        b0 * cps[0][1] + b1 * cps[1][1] + b2 * cps[2][1] + b3 * cps[3][1],
        b0 * cps[0][2] + b1 * cps[1][2] + b2 * cps[2][2] + b3 * cps[3][2],
    )


def _bezier_tangent(t: float, cps: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Cubic Bezier derivative at t (not normalised)."""
    u = 1.0 - t
    a0 = 3.0 * u * u
    a1 = 6.0 * u * t
    a2 = 3.0 * t * t
    return (
        a0 * (cps[1][0] - cps[0][0]) + a1 * (cps[2][0] - cps[1][0]) + a2 * (cps[3][0] - cps[2][0]),
        a0 * (cps[1][1] - cps[0][1]) + a1 * (cps[2][1] - cps[1][1]) + a2 * (cps[3][1] - cps[2][1]),
        a0 * (cps[1][2] - cps[0][2]) + a1 * (cps[2][2] - cps[1][2]) + a2 * (cps[3][2] - cps[2][2]),
    )


def _normalize(
    v: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    mag = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if mag < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _local_frame(
    tangent: Tuple[float, float, float],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Build (N, B) perpendicular to tangent. N kept roughly aligned with world +X."""
    world_x = (1.0, 0.0, 0.0)
    n_raw = _cross(world_x, tangent)
    if abs(n_raw[0]) + abs(n_raw[1]) + abs(n_raw[2]) < 1e-9:
        # tangent ‖ world_x → fall back to world_y
        n_raw = _cross((0.0, 1.0, 0.0), tangent)
    n_vec = _normalize(_cross(tangent, n_raw))
    b_vec = _normalize(_cross(tangent, n_vec))
    return n_vec, b_vec


def _default_spine(
    height_total_m: float, landing_radius_m: float
) -> List[Tuple[float, float, float]]:
    """4-point cubic Bezier — base to apex, with mild S-curve in xy."""
    r = landing_radius_m
    h = height_total_m
    return [
        (0.0, 0.0, 0.0),
        (0.40 * r, -0.30 * r, 0.33 * h),
        (-0.35 * r, 0.45 * r, 0.66 * h),
        (0.15 * r, 0.10 * r, h),
    ]


def build_leaf_v2_mesh(
    height_total_m: float,
    landing_radius_m: float,
    twist_total_deg: float,
    n_v: int = 14,
    n_theta: int = 28,
) -> Tuple[List[Vertex], List[TriFace]]:
    """Plan §9 leaf: bezier spine + per-zone profile (ellipse + camber + rim + channel).

    Three leaf zones (landing / flow / discharge) are placed along a
    cubic Bezier spine. Per-zone profile is an ellipse cross-section
    swept along the local spine tangent, with:
    - paraboloid camber (concave-up bowl, peaks at zone centre)
    - smooth rim curl at the outer edge (u > 0.85)
    - longitudinal channel groove at theta ≈ 0 / π
    - global twist (radians per fraction of spine height) accumulated
      along v

    Returns one big mesh that is the union of three independent leaf
    surfaces (no inter-leaf blend yet — that's a Phase D follow-up).
    """
    if height_total_m <= 0:
        raise ValueError("height_total_m must be > 0")
    if landing_radius_m <= 0:
        raise ValueError("landing_radius_m must be > 0")
    if n_v < 3 or n_theta < 3:
        raise ValueError("n_v >= 3 and n_theta >= 3 required")

    cps = _default_spine(height_total_m, landing_radius_m)
    twist_total_rad = math.radians(twist_total_deg)

    all_verts: List[Vertex] = []
    all_faces: List[TriFace] = []

    for (
        t_center,
        t_half,
        length_factor,
        width_aspect,
        camber_factor,
        rim_h_factor,
        channel_depth_factor,
        channel_sigma,
    ) in _LEAF_V2_ZONES:
        a_max = landing_radius_m * length_factor
        b_max = a_max * width_aspect
        camber_max = camber_factor * a_max
        rim_max = rim_h_factor * a_max
        channel_depth = channel_depth_factor * a_max

        base_idx = len(all_verts)
        for i in range(n_v):
            v_frac = i / float(n_v - 1)  # 0 → 1 within zone
            t = (t_center - t_half) + 2.0 * t_half * v_frac
            t = min(max(t, 0.0), 1.0)
            spine_pt = _bezier_point(t, cps)
            tangent = _normalize(_bezier_tangent(t, cps))
            n_vec, b_vec = _local_frame(tangent)

            # zone-local v in [-1, 1] for taper
            v_local = 2.0 * v_frac - 1.0
            scale = max(0.0, 1.0 - v_local * v_local)

            a_v = a_max * scale
            b_v = b_max * scale
            camber_v = camber_max * scale
            rim_v = rim_max * scale
            ch_depth_v = channel_depth * scale

            twist_rad = twist_total_rad * t

            for j in range(n_theta):
                theta = 2.0 * math.pi * j / n_theta
                cos_th = math.cos(theta)
                sin_th = math.sin(theta)
                # u — radial param within the profile (always full radius for now)
                u = 1.0
                x_local = a_v * u * cos_th
                y_local = b_v * u * sin_th
                z_dome = camber_v * (1.0 - u * u)
                rim_frac = max(0.0, (u - 0.85) / 0.15)
                z_rim = rim_v * rim_frac * rim_frac
                # longitudinal channel: deepest at sin(theta) ≈ 0
                if channel_sigma > 0:
                    ch_factor = math.exp(-(sin_th * sin_th) / (channel_sigma * channel_sigma))
                else:
                    ch_factor = 0.0
                z_channel = -ch_depth_v * ch_factor * (1.0 - u * u)
                z_local = z_dome + z_rim + z_channel

                # twist about spine tangent (rotate x_local/y_local in local frame)
                ct = math.cos(twist_rad)
                st = math.sin(twist_rad)
                x_t = x_local * ct - y_local * st
                y_t = x_local * st + y_local * ct

                # place in world: spine + N*x_t + B*y_t + T*z_local
                px = spine_pt[0] + n_vec[0] * x_t + b_vec[0] * y_t + tangent[0] * z_local
                py = spine_pt[1] + n_vec[1] * x_t + b_vec[1] * y_t + tangent[1] * z_local
                pz = spine_pt[2] + n_vec[2] * x_t + b_vec[2] * y_t + tangent[2] * z_local
                all_verts.append((px, py, pz))

        for i in range(n_v - 1):
            for j in range(n_theta):
                a_i = base_idx + i * n_theta + j
                b_i = base_idx + i * n_theta + ((j + 1) % n_theta)
                c_i = base_idx + (i + 1) * n_theta + ((j + 1) % n_theta)
                d_i = base_idx + (i + 1) * n_theta + j
                all_faces.append((a_i, b_i, c_i))
                all_faces.append((a_i, c_i, d_i))

    return all_verts, all_faces


def build_params_dict(
    candidate_id: str,
    height_total_m: float,
    landing_radius_m: float,
    twist_total_deg: float,
    nozzles: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a schema-1.0 params dict with slider-driven overrides.

    Mirrors the default template in ``leaflab/cli/init_run.py``. TODO: when
    ``configs/base_params.json`` is fleshed out (Phase C task), both this and
    ``init_run`` should load from it instead of duplicating.
    """
    top_leaf_z = max(0.1, height_total_m - 0.3)
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "description": "Phase D pre - 3-leaf dome stack",
        "global_constraints": {
            "max_height_m": 15.0,
            "min_height_m": 10.0,
            "max_plan_radius_m": max(landing_radius_m * 2.0, 4.5),
            "target_visual_axis": "facade_to_void_center",
        },
        "geometry": {
            "leaf_count": 3,
            "single_surface_intent": True,
            "height_total_m": height_total_m,
            "base_z_m": 0.0,
            "top_leaf_z_m": top_leaf_z,
            "spine": {
                "type": "bezier_or_nurbs",
                "control_points": [
                    [0.0, 0.0, 0.0],
                    [0.5, -0.3, height_total_m * 0.33],
                    [-0.4, 0.6, height_total_m * 0.66],
                    [0.2, 0.1, height_total_m],
                ],
                "twist_total_deg": twist_total_deg,
            },
            "leafs": [
                {
                    "leaf_id": "L1_landing",
                    "z_m": top_leaf_z,
                    "length_m": 5.2,
                    "width_m": 3.4,
                    "camber": 0.38,
                    "twist_deg": 42.0,
                    "pitch_deg": 18.0,
                    "landing_angle_deg": 14.0,
                    "landing_radius_m": landing_radius_m,
                    "rim_height_m": 0.12,
                    "rim_thickness_m": 0.045,
                    "channel_depth_m": 0.08,
                    "channel_offset_m": 0.35,
                    "overlap_to_next_m": 0.6,
                },
                {
                    "leaf_id": "L2_flow",
                    "z_m": height_total_m * 0.5,
                    "length_m": 4.6,
                    "width_m": 2.8,
                    "camber": 0.34,
                    "twist_deg": -31.0,
                    "pitch_deg": 24.0,
                    "rim_height_m": 0.08,
                    "rim_thickness_m": 0.04,
                    "channel_depth_m": 0.06,
                    "channel_offset_m": -0.25,
                    "overlap_to_next_m": 0.4,
                },
                {
                    "leaf_id": "L3_discharge",
                    "z_m": height_total_m * 0.25,
                    "length_m": 3.2,
                    "width_m": 2.1,
                    "camber": 0.28,
                    "twist_deg": 26.0,
                    "pitch_deg": 35.0,
                    "rim_height_m": 0.05,
                    "rim_thickness_m": 0.035,
                    "channel_depth_m": 0.045,
                    "channel_offset_m": 0.15,
                },
            ],
        },
        "water": {
            "fall_height_m": 15.0,
            "gravity_mps2": 9.81,
            "estimated_impact_velocity_mps": 17.2,
            "inlet_type": "double_ring_curtain",
            "curtain_radius_inner_m": 1.0,
            "curtain_radius_outer_m": 2.0,
            "nozzle_spacing_mm": 40.0,
            "flow_rate_per_nozzle_lpm": 45.0,
            "flow_rate_min_lpm": 30.0,
            "flow_rate_max_lpm": 60.0,
            "target_drain_position": [0.0, 0.0, 0.0],
            "pond_radius_m": 4.5,
            "nozzles": nozzles,
        },
        "material": {
            "base_material": "brass_casting",
            "finish": "automotive_paint",
            "density_kg_m3": 8500.0,
            "shell_thickness_mm": 18.0,
            "min_shell_thickness_mm": 12.0,
            "max_shell_thickness_mm": 45.0,
            "coating_note": "TBD",
        },
        "structure": {
            "support_type": "hidden_base_plate_and_anchor",
            "visible_internal_frame": False,
            "base_plate_radius_m": 1.2,
            "anchor_count": 12,
            "rim_as_structural_edge": True,
            "channel_as_spine": True,
        },
        "views": {
            "facade_camera": {"position": [12.0, -18.0, 2.0], "target": [0.0, 0.0, 7.0]},
            "eye_level_camera": {"position": [6.0, -7.0, 1.6], "target": [0.0, 0.0, 5.0]},
            "mezzanine_camera": {"position": [4.0, -3.0, 12.0], "target": [0.0, 0.0, 8.0]},
        },
    }
