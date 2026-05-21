from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh
from typer.testing import CliRunner

from leaflab.cli.main import app
from leaflab.fast_sim import run_fast_sim
from leaflab.schema.metrics_schema import load_metrics
from leaflab.schema.params_schema import load_params


def test_run_fast_sim_returns_valid_metrics(
    sample_params_dict: dict, mesh_cylinder_tapered: trimesh.Trimesh
) -> None:
    params = load_params(sample_params_dict)
    metrics = run_fast_sim(mesh_cylinder_tapered, params, n_particles=50, seed=1)
    assert metrics.candidate_id == "cand_test"
    assert metrics.algorithm_version == "0.1.0"
    assert 0.0 <= metrics.water_proxy.normal_impact_score <= 1.0
    assert metrics.water_proxy.attachment_length_m >= 0
    assert 0.0 <= metrics.water_proxy.edge_escape_rate <= 1.0
    assert 0.0 <= metrics.water_proxy.attachment_ratio <= 1.0
    assert metrics.water_proxy.drain_target_error_m >= 0
    assert metrics.water_proxy.splash_proxy >= 0
    assert metrics.geometry_proxy.height_total_m > 0
    assert metrics.geometry_proxy.surface_area_m2 > 0


def test_run_fast_sim_no_hits_returns_zero_water_metrics(
    sample_params_dict: dict,
) -> None:
    """A mesh placed far away from the water curtain → all misses → zeroed water proxy."""
    far_mesh = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    far_mesh.apply_translation([1000.0, 1000.0, 0.0])
    params = load_params(sample_params_dict)
    metrics = run_fast_sim(far_mesh, params, n_particles=20, seed=0)
    assert metrics.water_proxy.normal_impact_score == 0.0
    assert metrics.water_proxy.attachment_length_m == 0.0
    assert metrics.water_proxy.edge_escape_rate == 0.0
    assert metrics.water_proxy.splash_proxy == 0.0


def test_cli_fast_sim_e2e(tmp_path: Path, sample_params_dict: dict) -> None:
    run_dir = tmp_path / "cand_e2e"
    (run_dir / "geometry").mkdir(parents=True)
    sample_params_dict["candidate_id"] = "cand_e2e"
    with (run_dir / "params.json").open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)

    box = trimesh.creation.box(extents=(4.0, 4.0, 14.0))
    box.apply_translation([0.0, 0.0, 7.0])
    box.export(run_dir / "geometry" / "leaf.stl")

    runner = CliRunner()
    result = runner.invoke(app, ["fast-sim", str(run_dir), "-n", "30", "--slide-steps", "30"])
    assert result.exit_code == 0, result.output

    out_path = run_dir / "fast_metrics.json"
    assert out_path.exists()
    with out_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    loaded = load_metrics("fast", data)
    assert loaded.candidate_id == "cand_e2e"  # type: ignore[attr-defined]


def test_cli_fast_sim_missing_params(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["fast-sim", str(tmp_path)])
    assert result.exit_code != 0
    assert "missing params.json" in result.output


def test_cli_fast_sim_missing_stl(tmp_path: Path, sample_params_dict: dict) -> None:
    run_dir = tmp_path / "no_stl"
    (run_dir / "geometry").mkdir(parents=True)
    with (run_dir / "params.json").open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)

    runner = CliRunner()
    result = runner.invoke(app, ["fast-sim", str(run_dir)])
    assert result.exit_code != 0
    assert "missing STL" in result.output


@pytest.mark.parametrize("seed", [0, 1, 99])
def test_run_fast_sim_deterministic(
    sample_params_dict: dict, mesh_cylinder_tapered: trimesh.Trimesh, seed: int
) -> None:
    params = load_params(sample_params_dict)
    m1 = run_fast_sim(mesh_cylinder_tapered, params, n_particles=40, seed=seed)
    m2 = run_fast_sim(mesh_cylinder_tapered, params, n_particles=40, seed=seed)
    assert m1.model_dump() == m2.model_dump()
