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
    (0.95, 1.6, 0.20, 0.08, 14.0, 0.0),    # L1 landing — top, large
    (0.55, 1.1, 0.16, 0.06, 24.0, 0.4),    # L2 flow — mid
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

    for (z_frac, length_factor, camber_factor, rim_h_factor,
         pitch_deg, twist_offset_frac) in _LEAF_SPECS:
        a = landing_radius_m * length_factor        # ellipse semi-major (m)
        b = a * 0.7                                  # semi-minor (aspect)
        camber_m = camber_factor * a
        rim_m = rim_h_factor * a
        z_offset = z_frac * height_total_m
        twist_rad = math.radians(
            twist_total_deg * (z_frac + twist_offset_frac)
        )
        pitch_rad = math.radians(pitch_deg)
        cp = math.cos(pitch_rad)
        sp = math.sin(pitch_rad)
        ct = math.cos(twist_rad)
        st = math.sin(twist_rad)

        base_idx = len(all_verts)
        for i in range(n_u):
            u = i / float(n_u - 1)             # 0 = centre, 1 = edge
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
