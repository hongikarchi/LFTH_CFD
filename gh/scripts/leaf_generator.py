"""Minimal params_dict builder for ``runs/<id>/params.json``.

After PR-G the procedural mesh generators (build_*_mesh) and the
6-module flower-stack helpers were removed. The mesh is now an input
(reference geometry from the Rhino doc), not something this module
synthesises. This file is now strictly the schema-1.0 params dict
factory used by the export pipeline.

Strict Python 3.9 compat — no ``leaflab`` import.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_params_dict(
    candidate_id: str,
    height_total_m: float,
    landing_radius_m: float,
    twist_total_deg: float,
    nozzles: Optional[List[Dict[str, Any]]] = None,
    source_mesh_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a schema-1.0 params dict with slider-driven overrides.

    The mesh itself is an input (reference geometry); ``leafs`` is left
    empty so the schema validator's leaf_count==len(leafs) check passes
    when both are 0/empty. ``source_mesh_path`` (optional) records where
    the mesh came from for reproducibility.
    """
    top_leaf_z = max(0.1, height_total_m - 0.3)
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "description": "PR-G - reference mesh input (procedural mesh removed)",
        "global_constraints": {
            "max_height_m": 15.0,
            "min_height_m": 10.0,
            "max_plan_radius_m": max(landing_radius_m * 2.0, 4.5),
            "target_visual_axis": "facade_to_void_center",
        },
        "geometry": {
            "leaf_count": 0,
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
            "leafs": [],
            "source_mesh_path": source_mesh_path,
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
