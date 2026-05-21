from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh

from leaflab.cli.init_run import _template_params

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_params_dict() -> dict:
    return _template_params("cand_test")


@pytest.fixture
def sample_params_file(tmp_path: Path, sample_params_dict: dict) -> Path:
    p = tmp_path / "params.json"
    with p.open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)
    return p


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def small_leaf_stl(tmp_path: Path) -> Path:
    """A small watertight box mesh (3 x 2 x 14 m) used as a leaf-like STL stand-in."""
    mesh = trimesh.creation.box(extents=(3.0, 2.0, 14.0))
    out = tmp_path / "leaf.stl"
    mesh.export(out)
    return out


@pytest.fixture
def oversize_leaf_stl(tmp_path: Path) -> Path:
    """A box that exceeds the 15m height constraint - used for failure path tests."""
    mesh = trimesh.creation.box(extents=(3.0, 2.0, 18.0))
    out = tmp_path / "oversize_leaf.stl"
    mesh.export(out)
    return out


@pytest.fixture
def mm_scale_leaf_stl(tmp_path: Path) -> Path:
    """A box sized as if in millimeters (extents up to ~200m) - triggers scale warning."""
    mesh = trimesh.creation.box(extents=(3000.0, 2000.0, 14000.0))
    out = tmp_path / "mm_leaf.stl"
    mesh.export(out)
    return out


@pytest.fixture
def populated_run_dir(tmp_path: Path, sample_params_dict: dict, small_leaf_stl: Path) -> Path:
    """Create a runs/cand_test/ directory with params.json + geometry/leaf.stl."""
    run_dir = tmp_path / "run"
    (run_dir / "geometry").mkdir(parents=True)
    with (run_dir / "params.json").open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)
    target_stl = run_dir / "geometry" / "leaf.stl"
    target_stl.write_bytes(small_leaf_stl.read_bytes())
    return run_dir
