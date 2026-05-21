"""`leaflab init-run <candidate_id>` — create a new candidate run directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from leaflab.schema.version import CURRENT_PARAMS_VERSION

DEFAULT_RUNS_DIR = Path("runs")


def _template_params(candidate_id: str) -> dict[str, Any]:
    """Minimal valid params.json template — fill in real values via GH export."""
    return {
        "schema_version": CURRENT_PARAMS_VERSION.value,
        "candidate_id": candidate_id,
        "description": "TBD",
        "global_constraints": {
            "max_height_m": 15.0,
            "min_height_m": 10.0,
            "max_plan_radius_m": 4.5,
            "target_visual_axis": "facade_to_void_center",
        },
        "geometry": {
            "leaf_count": 3,
            "single_surface_intent": True,
            "height_total_m": 14.5,
            "base_z_m": 0.0,
            "top_leaf_z_m": 14.2,
            "spine": {
                "type": "bezier_or_nurbs",
                "control_points": [
                    [0.0, 0.0, 0.0],
                    [0.5, -0.3, 4.5],
                    [-0.4, 0.6, 9.5],
                    [0.2, 0.1, 14.5],
                ],
                "twist_total_deg": 135.0,
            },
            "leafs": [
                {
                    "leaf_id": "L1_landing",
                    "z_m": 14.2,
                    "length_m": 5.2,
                    "width_m": 3.4,
                    "camber": 0.38,
                    "twist_deg": 42.0,
                    "pitch_deg": 18.0,
                    "landing_angle_deg": 14.0,
                    "landing_radius_m": 1.2,
                    "rim_height_m": 0.12,
                    "rim_thickness_m": 0.045,
                    "channel_depth_m": 0.08,
                    "channel_offset_m": 0.35,
                    "overlap_to_next_m": 0.6,
                },
                {
                    "leaf_id": "L2_flow",
                    "z_m": 8.4,
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
                    "z_m": 3.8,
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
            "nozzles": None,
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
            "facade_camera": {
                "position": [12.0, -18.0, 2.0],
                "target": [0.0, 0.0, 7.0],
            },
            "eye_level_camera": {
                "position": [6.0, -7.0, 1.6],
                "target": [0.0, 0.0, 5.0],
            },
            "mezzanine_camera": {
                "position": [4.0, -3.0, 12.0],
                "target": [0.0, 0.0, 8.0],
            },
        },
    }


def run(
    candidate_id: str = typer.Argument(..., help="candidate identifier (e.g. cand_0001)"),
    runs_dir: Path = typer.Option(DEFAULT_RUNS_DIR, "--runs-dir", help="root runs directory"),
    force: bool = typer.Option(False, "--force", help="overwrite existing run directory"),
) -> None:
    """Create a new candidate run directory with a template params.json."""
    run_dir = runs_dir / candidate_id
    if run_dir.exists() and not force:
        typer.echo(f"error: {run_dir} already exists (use --force to overwrite)", err=True)
        raise typer.Exit(code=1)

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "geometry").mkdir(exist_ok=True)

    params_path = run_dir / "params.json"
    with params_path.open("w", encoding="utf-8") as fh:
        json.dump(_template_params(candidate_id), fh, indent=2)
        fh.write("\n")

    typer.echo(f"created {run_dir}")
    typer.echo(f"  - {params_path}")
    typer.echo(f"  - {run_dir / 'geometry'}/  (place leaf.stl here)")
