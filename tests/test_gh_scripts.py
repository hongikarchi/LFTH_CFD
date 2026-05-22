"""Structural tests for gh/scripts/ — boundary rules + functional sanity.

PR-G architecture: procedural mesh generation is removed; the leaf mesh
is loaded from a Rhino reference geometry. This file tests the four
GH-side modules separately:

- ``mesh_io``    — Rhino mesh dump → (verts, faces) merge
- ``water_sim``  — particle/polyline cascade through a trimesh
- ``evaluator``  — rough CFD metrics aggregate
- ``leaf_generator`` — minimal params_dict builder (no mesh)

Tests run in the leaflab venv (Python 3.12) but the gh/scripts modules
must remain importable inside Rhino 8's embedded CPython 3.9.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest
import trimesh

REPO_ROOT = Path(__file__).resolve().parents[1]
GH_SCRIPTS_DIR = REPO_ROOT / "gh" / "scripts"


def _iter_gh_script_files() -> list[Path]:
    return sorted(p for p in GH_SCRIPTS_DIR.rglob("*.py") if p.name != "__init__.py")


# ---------------------------------------------------------------------------
# Boundary rules (apply to every gh/scripts/*.py)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script_path", _iter_gh_script_files(), ids=lambda p: p.name)
def test_no_leaflab_import(script_path: Path) -> None:
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
    src = script_path.read_text(encoding="utf-8")
    ast.parse(src, filename=str(script_path), feature_version=(3, 9))


# ---------------------------------------------------------------------------
# mesh_io
# ---------------------------------------------------------------------------


def test_mesh_io_single_mesh_identity_scale() -> None:
    from gh.scripts.mesh_io import mesh_summary, rhino_mesh_to_tri_data

    dump = [
        {
            "verts": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
            "faces": [(0, 1, 2)],
        }
    ]
    verts, faces = rhino_mesh_to_tri_data(dump, doc_to_m=1.0)
    assert verts == [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    assert faces == [(0, 1, 2)]
    s = mesh_summary(verts, faces)
    assert s["vert_count"] == 3
    assert s["face_count"] == 1
    assert s["bbox_m"] == [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]]


def test_mesh_io_mm_doc_scale() -> None:
    from gh.scripts.mesh_io import rhino_mesh_to_tri_data

    dump = [
        {
            "verts": [(1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0), (0.0, 0.0, 1000.0)],
            "faces": [(0, 1, 2)],
        }
    ]
    verts, _ = rhino_mesh_to_tri_data(dump, doc_to_m=0.001)
    assert verts == [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]


def test_mesh_io_multi_mesh_reindex() -> None:
    from gh.scripts.mesh_io import rhino_mesh_to_tri_data

    dump = [
        {
            "verts": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
            "faces": [(0, 1, 2)],
        },
        {
            "verts": [(5.0, 5.0, 5.0), (6.0, 5.0, 5.0), (5.0, 6.0, 5.0)],
            "faces": [(0, 1, 2)],
        },
    ]
    verts, faces = rhino_mesh_to_tri_data(dump)
    assert len(verts) == 6
    # second mesh's face indices must be re-based: (3, 4, 5)
    assert faces == [(0, 1, 2), (3, 4, 5)]


def test_mesh_io_rejects_bad_input() -> None:
    from gh.scripts.mesh_io import rhino_mesh_to_tri_data

    with pytest.raises(ValueError):
        rhino_mesh_to_tri_data([], doc_to_m=0)
    with pytest.raises(ValueError):
        rhino_mesh_to_tri_data([{"verts": []}])  # missing 'faces'
    with pytest.raises(ValueError):
        rhino_mesh_to_tri_data([{"faces": []}])  # missing 'verts'


def test_mesh_io_empty_summary() -> None:
    from gh.scripts.mesh_io import mesh_summary

    s = mesh_summary([], [])
    assert s["vert_count"] == 0
    assert s["face_count"] == 0


# ---------------------------------------------------------------------------
# water_sim — fixtures & helpers
# ---------------------------------------------------------------------------


def _flat_quad_mesh(size: float = 10.0, z: float = 0.0) -> trimesh.Trimesh:
    verts = np.array(
        [
            [-size / 2, -size / 2, z],
            [size / 2, -size / 2, z],
            [size / 2, size / 2, z],
            [-size / 2, size / 2, z],
        ],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def _stacked_disc_mesh(
    n_layers: int = 6,
    top_z: float = 14.0,
    bottom_z: float = 1.0,
    top_radius: float = 1.5,
    bottom_radius: float = 3.0,
    n_petals: int = 5,
    n_u: int = 8,
    n_v: int = 6,
) -> trimesh.Trimesh:
    """Synthetic reference-like mesh: n_layers tilted petal-discs stacked."""
    all_verts: list[tuple[float, float, float]] = []
    all_faces: list[tuple[int, int, int]] = []
    for i in range(n_layers):
        frac = i / max(1, n_layers - 1)
        z_m = top_z + (bottom_z - top_z) * frac
        radius = top_radius + (bottom_radius - top_radius) * frac
        camber = 0.45 * radius
        for p in range(n_petals):
            base_idx = len(all_verts)
            theta_centre = 2.0 * math.pi * p / n_petals + 0.4 * i  # spiral
            for ui in range(n_u):
                u = ui / float(n_u - 1)
                for vi in range(n_v):
                    v_local = (vi / float(n_v - 1)) * 2.0 - 1.0
                    eff_theta = theta_centre + v_local * (math.pi / n_petals * 1.1)
                    r = u * radius
                    z_bowl = camber * (u * u) * (1.0 - 0.4 * v_local * v_local)
                    all_verts.append(
                        (r * math.cos(eff_theta), r * math.sin(eff_theta), z_m + z_bowl)
                    )
            for ui in range(n_u - 1):
                for vi in range(n_v - 1):
                    a = base_idx + ui * n_v + vi
                    b = base_idx + ui * n_v + (vi + 1)
                    c = base_idx + (ui + 1) * n_v + (vi + 1)
                    d = base_idx + (ui + 1) * n_v + vi
                    all_faces.append((a, b, c))
                    all_faces.append((a, c, d))
    return trimesh.Trimesh(
        vertices=np.array(all_verts, dtype=float),
        faces=np.array(all_faces, dtype=int),
        process=False,
    )


# ---------------------------------------------------------------------------
# water_sim tests — preserved API from former water_curtain.py
# ---------------------------------------------------------------------------


def test_water_sim_nozzles_from_points_mm_doc() -> None:
    from gh.scripts.water_sim import nozzles_from_points

    points = [(1000.0, 0.0, 15000.0), (-500.0, 500.0, 15000.0)]
    nozzles = nozzles_from_points(points, flow_rate_lpm=45.0, doc_to_m=0.001)
    assert nozzles[0]["position"] == [1.0, 0.0, 15.0]
    assert nozzles[1]["position"] == [-0.5, 0.5, 15.0]


def test_water_sim_velocity_from_tilt_vertical() -> None:
    from gh.scripts.water_sim import velocity_from_tilt

    v = velocity_from_tilt(fall_height_m=15.0, tilt_deg=0.0)
    assert abs(v[0]) < 1e-9
    assert abs(v[1]) < 1e-9
    expected_mag = math.sqrt(2.0 * 9.81 * 15.0)
    assert abs(v[2] + expected_mag) < 1e-6


def test_water_sim_fall_endpoint_vertical() -> None:
    from gh.scripts.water_sim import fall_trajectory_endpoint

    end = fall_trajectory_endpoint((1.0, 2.0, 15.0), fall_height_m=15.0)
    assert end == (1.0, 2.0, 0.0)


# Tier 1 — smoke: simulate on flat plane reaches pond
def test_tier1_simulate_reaches_pond_flat_plane() -> None:
    from gh.scripts.water_sim import simulate_water_path_polyline

    mesh = _flat_quad_mesh(size=10.0, z=0.0)
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.0, 0.0, 10.0),
        velocity_mps=(0.0, 0.0, -1.0),
        mesh=mesh,
        pond_z_m=-3.0,
    )
    assert len(pts) >= 2
    assert pts[-1][2] <= 0.5


# Tier 2 — cascade through reference-like synthetic mesh hits ≥ 3 layers
def test_tier2_simulate_cascade_synthetic_reference() -> None:
    from gh.scripts.water_sim import simulate_water_path_polyline

    mesh = _stacked_disc_mesh(n_layers=6)
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.3, 0.0, 29.0),
        velocity_mps=(0.0, 0.0, -17.15),
        mesh=mesh,
        max_bounces=20,
    )
    assert len(pts) >= 5, f"polyline too short: {len(pts)}"
    assert pts[-1][2] <= 1.0


# Tier 3 — polyline has visible xy spread (not stuck on z-axis)
def test_tier3_simulate_xy_spread() -> None:
    from gh.scripts.water_sim import simulate_water_path_polyline

    mesh = _stacked_disc_mesh(n_layers=6)
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.0, 0.0, 29.0),
        velocity_mps=(0.0, 0.0, -17.15),
        mesh=mesh,
        max_bounces=20,
    )
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xy_span = max(max(xs) - min(xs), max(ys) - min(ys))
    assert xy_span >= 0.3, (
        f"polyline has no horizontal spread (xy_span={xy_span:.3f}m) — water "
        "didn't bounce/slide laterally; visible reflection missing"
    )


# Tier 4 — evaluator returns valid metrics dict on synthetic case
def test_tier4_evaluator_metrics_shape() -> None:
    from gh.scripts.evaluator import evaluate
    from gh.scripts.water_sim import (
        nozzles_from_points,
        simulate_water_path_polyline,
        velocity_from_tilt,
    )

    mesh = _stacked_disc_mesh(n_layers=6)
    verts = mesh.vertices.tolist()
    faces = mesh.faces.tolist()
    nozzles = nozzles_from_points(
        [(0.3, 0.0, 29.0)],
        flow_rate_lpm=45.0,
        velocity_mps_shared=velocity_from_tilt(15.0, 0.0),
    )
    polylines = []
    for nz in nozzles:
        sp = tuple(nz["position"])
        vel = tuple(nz["velocity_mps"]) if nz["velocity_mps"] else (0.0, 0.0, -17.15)
        polylines.append(simulate_water_path_polyline(sp, vel, mesh, max_bounces=20))
    m = evaluate(verts, faces, polylines, nozzles)
    for key in (
        "polyline_count",
        "points_total",
        "cascade_drop_m_avg",
        "pond_capture_ratio",
        "xy_spread_m_avg",
        "normal_impact_avg",
        "nozzle_count",
        "bbox_m",
    ):
        assert key in m, f"evaluator missing key {key}"
    assert m["polyline_count"] == 1
    assert m["cascade_drop_m_avg"] > 10.0  # 29m → ~0m drop
    assert 0.0 <= m["pond_capture_ratio"] <= 1.0


# Tier 5 — e2e pipeline (mesh_io → water_sim → evaluator → summary)
def test_tier5_e2e_pipeline() -> None:
    from gh.scripts.evaluator import evaluate
    from gh.scripts.mesh_io import mesh_summary, rhino_mesh_to_tri_data
    from gh.scripts.water_sim import (
        nozzles_from_points,
        simulate_water_path_polyline,
        velocity_from_tilt,
    )

    mesh = _stacked_disc_mesh(n_layers=4)
    dumps = [
        {"verts": mesh.vertices.tolist(), "faces": mesh.faces.tolist()},
    ]
    verts, faces = rhino_mesh_to_tri_data(dumps, doc_to_m=1.0)
    summary = mesh_summary(verts, faces)
    tm = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces), process=False)
    nozzles = nozzles_from_points(
        [(0.4, 0.0, 29.0)],
        flow_rate_lpm=45.0,
        velocity_mps_shared=velocity_from_tilt(15.0, 0.0),
    )
    polylines = []
    for nz in nozzles:
        sp = tuple(nz["position"])
        vel = tuple(nz["velocity_mps"]) if nz["velocity_mps"] else (0.0, 0.0, -17.15)
        polylines.append(simulate_water_path_polyline(sp, vel, tm, max_bounces=20))
    metrics = evaluate(verts, faces, polylines, nozzles)
    assert summary["vert_count"] > 0
    assert metrics["polyline_count"] == 1
    assert metrics["cascade_drop_m_avg"] > 10.0
    # endpoint reaches near pond
    assert polylines[0][-1][2] <= 1.5


# ---------------------------------------------------------------------------
# leaf_generator — minimal build_params_dict
# ---------------------------------------------------------------------------


def test_build_params_dict_schema_compat() -> None:
    from gh.scripts.leaf_generator import build_params_dict
    from leaflab.schema.params_schema import load_params

    pd = build_params_dict(
        candidate_id="cand_prg",
        height_total_m=14.0,
        landing_radius_m=1.5,
        twist_total_deg=60.0,
    )
    parsed = load_params(pd)
    assert parsed.candidate_id == "cand_prg"
    assert parsed.geometry.leaf_count == 0
    assert parsed.geometry.leafs == []
    assert parsed.geometry.source_mesh_path is None


def test_build_params_dict_records_source_mesh_path() -> None:
    from gh.scripts.leaf_generator import build_params_dict
    from leaflab.schema.params_schema import load_params

    pd = build_params_dict(
        candidate_id="cand_ref",
        height_total_m=14.0,
        landing_radius_m=1.5,
        twist_total_deg=60.0,
        source_mesh_path="rhino:layer:꽃_1",
    )
    parsed = load_params(pd)
    assert parsed.geometry.source_mesh_path == "rhino:layer:꽃_1"


# ---------------------------------------------------------------------------
# export round-trip (existing — keep)
# ---------------------------------------------------------------------------


def test_export_candidate_round_trip(tmp_path: Path, sample_params_dict: dict) -> None:
    from gh.scripts.export_candidate import export_candidate
    from gh.scripts.import_results import import_results

    mesh = trimesh.creation.box(extents=(3.0, 2.0, 14.0))
    out_dir = tmp_path / "cand_x"
    summary = export_candidate(
        mesh.vertices.tolist(), mesh.faces.tolist(), sample_params_dict, out_dir
    )
    assert (out_dir / "params.json").exists()
    assert summary["triangle_count"] == 12
    results = import_results(out_dir)
    assert results["params"]["candidate_id"] == sample_params_dict["candidate_id"]


def test_export_candidate_writes_valid_params_for_leaflab_validate(
    tmp_path: Path, sample_params_dict: dict
) -> None:
    from gh.scripts.export_candidate import export_candidate
    from leaflab.schema.params_schema import load_params

    mesh = trimesh.creation.box(extents=(3.0, 2.0, 14.0))
    out_dir = tmp_path / "cand_v"
    export_candidate(mesh.vertices.tolist(), mesh.faces.tolist(), sample_params_dict, out_dir)
    with (out_dir / "params.json").open(encoding="utf-8") as fh:
        loaded = load_params(json.load(fh))
    assert loaded.candidate_id == sample_params_dict["candidate_id"]


# ---------------------------------------------------------------------------
# PR-H — particle CFD physics
# ---------------------------------------------------------------------------


def test_initial_velocity_vertical() -> None:
    from gh.scripts.water_sim import initial_velocity_from_tilt

    v = initial_velocity_from_tilt(fall_height_m=15.0, tilt_deg=0.0)
    expected_mag = math.sqrt(2.0 * 9.81 * 15.0)
    assert abs(v[0]) < 1e-9
    assert abs(v[1]) < 1e-9
    assert abs(v[2] + expected_mag) < 1e-6


def test_initial_velocity_horizontal_x() -> None:
    from gh.scripts.water_sim import initial_velocity_from_tilt

    v = initial_velocity_from_tilt(fall_height_m=15.0, tilt_deg=90.0, azimuth_deg=0.0)
    expected_mag = math.sqrt(2.0 * 9.81 * 15.0)
    assert abs(v[0] - expected_mag) < 1e-6
    assert abs(v[1]) < 1e-6
    assert abs(v[2]) < 1e-6


def test_n_particles_from_flow_rate_values() -> None:
    from gh.scripts.water_sim import n_particles_from_flow_rate

    assert n_particles_from_flow_rate(45.0) == 180
    assert n_particles_from_flow_rate(0.5) == 2
    assert n_particles_from_flow_rate(0.01) == 1
    assert n_particles_from_flow_rate(10000.0) == 200


def test_simulate_particle_specular_lift_on_flat() -> None:
    from gh.scripts.water_sim import simulate_particle

    mesh = _flat_quad_mesh(size=20.0, z=0.0)
    traj = simulate_particle(
        mesh,
        start_xyz_m=(0.0, 0.0, 20.0),
        velocity_mps=(0.0, 0.0, -15.0),
        elastic_speed_threshold_mps=5.0,
        max_bounces=3,
    )
    assert traj.n_collisions >= 1
    rising = max(p[2] for p in traj.points[1:])
    assert rising > 0.5, f"specular bounce didn't lift water: max z = {rising:.2f}"


def test_simulate_particle_slide_on_tilted() -> None:
    import numpy as np
    import trimesh

    from gh.scripts.water_sim import simulate_particle

    verts = np.array(
        [[-5, -5, 0], [5, -5, 0], [5, 5, 5], [-5, 5, 5]],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    traj = simulate_particle(
        mesh,
        start_xyz_m=(0.0, 0.0, 3.0),
        velocity_mps=(0.0, 0.0, -1.0),
        elastic_speed_threshold_mps=10.0,
        slide_speed_threshold_mps=3.0,
        max_bounces=5,
    )
    assert traj.n_collisions >= 1
    assert traj.points[-1][2] <= 1.0


def test_simulate_water_curtain_particle_count() -> None:
    from gh.scripts.water_sim import simulate_water_curtain

    mesh = _flat_quad_mesh(size=20.0, z=0.0)
    trajectories = simulate_water_curtain(
        mesh,
        nozzle_points_m=[(0.0, 0.0, 15.0)],
        flow_rate_lpm=10.0,
        tilt_deg=0.0,
        azimuth_deg=0.0,
        fall_height_m=15.0,
    )
    assert len(trajectories) == 40  # 10 lpm × 4 base = 40 particles


def test_simulate_water_curtain_determinism() -> None:
    from gh.scripts.water_sim import simulate_water_curtain

    mesh = _flat_quad_mesh(size=20.0, z=0.0)
    a = simulate_water_curtain(mesh, [(0.0, 0.0, 15.0)], 5.0, 0.0, 0.0, rng_seed=42)
    b = simulate_water_curtain(mesh, [(0.0, 0.0, 15.0)], 5.0, 0.0, 0.0, rng_seed=42)
    assert len(a) == len(b)
    for ta, tb in zip(a, b, strict=False):
        for pa, pb in zip(ta.points, tb.points, strict=False):
            assert abs(pa[0] - pb[0]) < 1e-9
            assert abs(pa[1] - pb[1]) < 1e-9
            assert abs(pa[2] - pb[2]) < 1e-9


def test_simulate_water_curtain_reaches_pond() -> None:
    from gh.scripts.water_sim import simulate_water_curtain

    mesh = _flat_quad_mesh(size=20.0, z=0.0)
    trajectories = simulate_water_curtain(mesh, [(0.0, 0.0, 15.0)], 5.0, 0.0, 0.0, pond_z_m=-2.0)
    for t in trajectories:
        assert t.points[-1][2] <= 0.5


def test_simulate_water_curtain_cascade_xy_spread() -> None:
    from gh.scripts.water_sim import simulate_water_curtain

    mesh = _stacked_disc_mesh(n_layers=6)
    trajectories = simulate_water_curtain(
        mesh,
        [(0.0, 0.0, 29.0)],
        flow_rate_lpm=5.0,
        tilt_deg=0.0,
        azimuth_deg=0.0,
        rng_seed=1,
    )
    all_xs: list[float] = []
    all_ys: list[float] = []
    for t in trajectories:
        all_xs.extend(p[0] for p in t.points)
        all_ys.extend(p[1] for p in t.points)
    xy_span = max(max(all_xs) - min(all_xs), max(all_ys) - min(all_ys))
    assert xy_span >= 0.5, f"cascade xy_span = {xy_span:.2f}m too small"
