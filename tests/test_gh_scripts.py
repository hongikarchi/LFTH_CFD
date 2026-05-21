"""Structural tests for gh/scripts/ — boundary rules + functional sanity.

These tests run in the leaflab venv (Python 3.12), but the gh/scripts/ modules
must remain compatible with Rhino 8's embedded CPython 3.9. We verify:
- no `leaflab` imports anywhere in gh/scripts/
- 3.9 syntax compatibility (parseable with feature_version=(3, 9))
- functional round-trip: export -> on-disk -> import_results reads it back
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import trimesh

from gh.scripts.export_candidate import export_candidate
from gh.scripts.import_results import get_score_or_none, import_results

REPO_ROOT = Path(__file__).resolve().parents[1]
GH_SCRIPTS_DIR = REPO_ROOT / "gh" / "scripts"


def _iter_gh_script_files() -> list[Path]:
    return sorted(p for p in GH_SCRIPTS_DIR.rglob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("script_path", _iter_gh_script_files(), ids=lambda p: p.name)
def test_no_leaflab_import(script_path: Path) -> None:
    """gh/scripts/ files must not import leaflab (boundary rule)."""
    src = script_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(script_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("leaflab"), (
                    f"{script_path.name} imports leaflab.{alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith("leaflab"), f"{script_path.name} does `from {mod} import ...`"


@pytest.mark.parametrize("script_path", _iter_gh_script_files(), ids=lambda p: p.name)
def test_python_39_parseable(script_path: Path) -> None:
    """gh/scripts/ files must parse under Python 3.9 syntax rules."""
    src = script_path.read_text(encoding="utf-8")
    ast.parse(src, filename=str(script_path), feature_version=(3, 9))


def test_export_candidate_round_trip(tmp_path: Path, sample_params_dict: dict) -> None:
    """Smoke test: write a box mesh via export_candidate, read back via import_results."""
    mesh = trimesh.creation.box(extents=(3.0, 2.0, 14.0))
    verts = mesh.vertices.tolist()
    faces = mesh.faces.tolist()

    out_dir = tmp_path / "cand_x"
    summary = export_candidate(verts, faces, sample_params_dict, out_dir)

    assert (out_dir / "params.json").exists()
    assert (out_dir / "geometry" / "leaf.stl").exists()
    assert summary["triangle_count"] == 12  # box has 12 tris
    assert summary["vertex_count"] == 8

    results = import_results(out_dir)
    assert results["params"] is not None
    assert results["params"]["candidate_id"] == sample_params_dict["candidate_id"]
    assert results["score"] is None
    assert results["geometry_check"] is None  # not yet generated
    assert results["fast_metrics"] is None


def test_import_results_missing_dir(tmp_path: Path) -> None:
    """import_results on an empty/nonexistent dir returns all-None dict."""
    results = import_results(tmp_path / "nope")
    assert all(v is None for v in results.values())


def test_get_score_or_none(tmp_path: Path) -> None:
    assert get_score_or_none(tmp_path) is None
    (tmp_path / "score.json").write_text('{"a": 1}', encoding="utf-8")
    assert get_score_or_none(tmp_path) == {"a": 1}


def test_export_candidate_writes_valid_params_for_leaflab_validate(
    tmp_path: Path, sample_params_dict: dict
) -> None:
    """The params.json written by export_candidate must validate via leaflab schema."""
    mesh = trimesh.creation.box(extents=(3.0, 2.0, 14.0))
    out_dir = tmp_path / "cand_v"
    export_candidate(
        mesh.vertices.tolist(),
        mesh.faces.tolist(),
        sample_params_dict,
        out_dir,
    )

    # leaflab is imported here (in the test, not the gh script) to verify
    # round-trip schema compliance.
    from leaflab.schema.params_schema import load_params

    with (out_dir / "params.json").open(encoding="utf-8") as fh:
        loaded = load_params(json.load(fh))
    assert loaded.candidate_id == sample_params_dict["candidate_id"]
