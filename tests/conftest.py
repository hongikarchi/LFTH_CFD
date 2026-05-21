from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
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


# ---------------------------------------------------------------------------
# fast_sim mesh fixtures — programmatic, deterministic
# ---------------------------------------------------------------------------


def _thin_quad_mesh(size_xy: float, z: float = 0.0) -> trimesh.Trimesh:
    """Single-sided quad (2 triangles) at given z; normals point +z."""
    half = size_xy / 2.0
    vertices = np.array(
        [
            [-half, -half, z],
            [half, -half, z],
            [half, half, z],
            [-half, half, z],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


@pytest.fixture
def mesh_flat_horizontal() -> trimesh.Trimesh:
    """Horizontal 10x10m quad at z=0. Outward normal = +z."""
    return _thin_quad_mesh(size_xy=10.0, z=0.0)


@pytest.fixture
def mesh_tilted_30() -> trimesh.Trimesh:
    """Quad tilted 30 deg about y-axis. Normal = (sin30, 0, cos30)."""
    mesh = _thin_quad_mesh(size_xy=10.0, z=0.0)
    R = trimesh.transformations.rotation_matrix(math.radians(30.0), [0.0, 1.0, 0.0])
    mesh.apply_transform(R)
    return mesh


@pytest.fixture
def mesh_cylinder_tapered() -> trimesh.Trimesh:
    """Tapered+twisted cylinder approximating build_mvp_mesh; closed strip, no caps."""
    n_z, n_theta = 12, 24
    h, r0, twist = 14.0, 1.5, math.radians(60.0)
    vertices: list[list[float]] = []
    for i in range(n_z):
        z = i / (n_z - 1) * h
        r = r0 * (0.4 + 0.6 * (1.0 - z / h))
        t = twist * (z / h)
        for j in range(n_theta):
            a = (2.0 * math.pi * j / n_theta) + t
            vertices.append([r * math.cos(a), r * math.sin(a), z])
    faces: list[list[int]] = []
    for i in range(n_z - 1):
        for j in range(n_theta):
            a = i * n_theta + j
            b = i * n_theta + ((j + 1) % n_theta)
            c = (i + 1) * n_theta + ((j + 1) % n_theta)
            d = (i + 1) * n_theta + j
            faces.append([a, b, c])
            faces.append([a, c, d])
    return trimesh.Trimesh(
        vertices=np.array(vertices, dtype=np.float64),
        faces=np.array(faces, dtype=np.int64),
        process=False,
    )


@pytest.fixture
def mesh_open_bowl() -> trimesh.Trimesh:
    """Upper hemisphere of an icosphere (z >= 0 only) — open at z=0 ring."""
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=2.0)
    keep = sphere.vertices[:, 2] >= -1e-6
    face_keep = keep[sphere.faces].all(axis=1)
    new_faces = sphere.faces[face_keep]
    return trimesh.Trimesh(vertices=sphere.vertices, faces=new_faces, process=True)
