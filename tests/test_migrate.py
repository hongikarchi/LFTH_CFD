from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from leaflab.cli import migrate
from leaflab.cli.main import app
from leaflab.schema.version import CURRENT_PARAMS_VERSION

runner = CliRunner()


def _write_params(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def test_migrate_path_not_found(tmp_path: Path) -> None:
    result = runner.invoke(app, ["migrate", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "path not found" in result.output


def test_migrate_no_params_in_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["migrate", str(tmp_path)])
    assert result.exit_code == 1
    assert "no params.json found" in result.output


def test_migrate_skips_current_version(
    tmp_path: Path, sample_params_dict: dict
) -> None:
    fp = _write_params(tmp_path / "run" / "params.json", sample_params_dict)
    result = runner.invoke(app, ["migrate", str(fp)])
    assert result.exit_code == 0, result.output
    assert "skip:" in result.output
    assert "already" in result.output


def test_migrate_missing_schema_version_errors(
    tmp_path: Path, sample_params_dict: dict
) -> None:
    del sample_params_dict["schema_version"]
    fp = _write_params(tmp_path / "params.json", sample_params_dict)
    result = runner.invoke(app, ["migrate", str(fp)])
    assert result.exit_code == 1
    assert "missing required 'schema_version'" in result.output


def test_migrate_unknown_version_errors(
    tmp_path: Path, sample_params_dict: dict
) -> None:
    sample_params_dict["schema_version"] = "0.5"
    fp = _write_params(tmp_path / "params.json", sample_params_dict)
    result = runner.invoke(app, ["migrate", str(fp)])
    assert result.exit_code == 1
    assert "no migration path" in result.output


def test_migrate_dry_run_does_not_write(
    tmp_path: Path,
    sample_params_dict: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Register a fake 0.9 -> current migration that wipes a sentinel
    def _fake_migration(data: dict) -> dict:
        data["description"] = "MIGRATED"
        return data

    monkeypatch.setitem(
        migrate.PARAMS_MIGRATIONS,
        ("0.9", CURRENT_PARAMS_VERSION.value),
        _fake_migration,
    )
    sample_params_dict["schema_version"] = "0.9"
    sample_params_dict["description"] = "original"
    fp = _write_params(tmp_path / "params.json", sample_params_dict)

    result = runner.invoke(app, ["migrate", str(fp), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "would migrate" in result.output

    on_disk = json.loads(fp.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == "0.9"
    assert on_disk["description"] == "original"


def test_migrate_applies_registered_step(
    tmp_path: Path,
    sample_params_dict: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_migration(data: dict) -> dict:
        data["description"] = "MIGRATED"
        return data

    monkeypatch.setitem(
        migrate.PARAMS_MIGRATIONS,
        ("0.9", CURRENT_PARAMS_VERSION.value),
        _fake_migration,
    )
    sample_params_dict["schema_version"] = "0.9"
    fp = _write_params(tmp_path / "params.json", sample_params_dict)

    result = runner.invoke(app, ["migrate", str(fp)])
    assert result.exit_code == 0, result.output
    assert "migrated:" in result.output

    on_disk = json.loads(fp.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == CURRENT_PARAMS_VERSION.value
    assert on_disk["description"] == "MIGRATED"


def test_migrate_directory_walk(
    tmp_path: Path,
    sample_params_dict: dict,
) -> None:
    """Recursive scan finds nested params.json files."""
    _write_params(tmp_path / "cand_a" / "params.json", sample_params_dict)
    _write_params(tmp_path / "cand_b" / "params.json", sample_params_dict)
    result = runner.invoke(app, ["migrate", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert result.output.count("skip:") == 2
    assert "total: 2" in result.output
