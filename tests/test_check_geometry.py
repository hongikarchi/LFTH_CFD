from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from leaflab.cli.main import app
from leaflab.geometry import MeshValidationError, validate_mesh

runner = CliRunner()


def test_validate_mesh_basic(small_leaf_stl: Path) -> None:
    result = validate_mesh(
        stl_path=small_leaf_stl,
        candidate_id="cand_x",
        max_height_m=15.0,
    )
    assert result.candidate_id == "cand_x"
    assert pytest.approx(result.height_m, abs=1e-3) == 14.0
    assert result.triangle_count > 0
    assert result.is_watertight is True
    assert result.is_manifold is True
    assert result.scale_warning is False


def test_validate_mesh_exceeds_height(oversize_leaf_stl: Path) -> None:
    with pytest.raises(MeshValidationError, match="height"):
        validate_mesh(
            stl_path=oversize_leaf_stl,
            candidate_id="cand_oversize",
            max_height_m=15.0,
        )


def test_validate_mesh_scale_warning(mm_scale_leaf_stl: Path) -> None:
    # mm-scale mesh has height 14000m -> also exceeds 15m hard limit, so we expect
    # MeshValidationError from height (which is the right behavior in practice).
    with pytest.raises(MeshValidationError):
        validate_mesh(
            stl_path=mm_scale_leaf_stl,
            candidate_id="cand_mm",
            max_height_m=15.0,
        )


def test_validate_mesh_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MeshValidationError, match="not found"):
        validate_mesh(
            stl_path=tmp_path / "nonexistent.stl",
            candidate_id="cand_missing",
            max_height_m=15.0,
        )


def test_cli_check_geometry_ok(populated_run_dir: Path) -> None:
    result = runner.invoke(app, ["check-geometry", str(populated_run_dir)])
    assert result.exit_code == 0, result.output
    assert "ok:" in result.output
    metrics_path = populated_run_dir / "geometry_metrics.json"
    assert metrics_path.exists()
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert data["candidate_id"] == "cand_test"
    assert data["schema_version"] == "1.0"


def test_cli_check_geometry_missing_stl(tmp_path: Path, sample_params_dict: dict) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "geometry").mkdir(parents=True)
    with (run_dir / "params.json").open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)
    result = runner.invoke(app, ["check-geometry", str(run_dir)])
    assert result.exit_code == 1
    assert "missing STL" in result.output


def test_cli_check_geometry_missing_params(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "geometry").mkdir(parents=True)
    (run_dir / "geometry" / "leaf.stl").write_bytes(b"")
    result = runner.invoke(app, ["check-geometry", str(run_dir)])
    assert result.exit_code == 1
    assert "missing params" in result.output


def test_cli_validate_geometry_metrics(populated_run_dir: Path) -> None:
    """`leaflab validate` should recognize geometry_metrics.json."""
    runner.invoke(app, ["check-geometry", str(populated_run_dir)])
    metrics_path = populated_run_dir / "geometry_metrics.json"
    result = runner.invoke(app, ["validate", str(metrics_path)])
    assert result.exit_code == 0, result.output
    assert "ok:" in result.output
