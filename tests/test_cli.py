from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from leaflab.cli.main import app

runner = CliRunner()


def test_init_run_creates_params(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init-run", "cand_0001", "--runs-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    params_path = tmp_path / "cand_0001" / "params.json"
    assert params_path.exists()
    assert (tmp_path / "cand_0001" / "geometry").is_dir()
    data = json.loads(params_path.read_text(encoding="utf-8"))
    assert data["candidate_id"] == "cand_0001"


def test_init_run_refuses_existing(tmp_path: Path) -> None:
    runner.invoke(app, ["init-run", "cand_x", "--runs-dir", str(tmp_path)])
    result = runner.invoke(app, ["init-run", "cand_x", "--runs-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_init_run_force_overwrites(tmp_path: Path) -> None:
    runner.invoke(app, ["init-run", "cand_y", "--runs-dir", str(tmp_path)])
    result = runner.invoke(app, ["init-run", "cand_y", "--runs-dir", str(tmp_path), "--force"])
    assert result.exit_code == 0


def test_validate_ok(tmp_path: Path) -> None:
    runner.invoke(app, ["init-run", "cand_v", "--runs-dir", str(tmp_path)])
    params_path = tmp_path / "cand_v" / "params.json"
    result = runner.invoke(app, ["validate", str(params_path)])
    assert result.exit_code == 0
    assert "ok:" in result.output


def test_validate_missing_file() -> None:
    result = runner.invoke(app, ["validate", "nonexistent.json"])
    assert result.exit_code == 1
    assert "file not found" in result.output


def test_help_works() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init-run" in result.output
    assert "validate" in result.output
