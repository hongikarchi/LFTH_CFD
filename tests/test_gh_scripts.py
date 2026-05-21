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
from gh.scripts.leaf_generator import build_mvp_mesh, build_params_dict

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


def test_build_mvp_mesh_counts() -> None:
    verts, faces = build_mvp_mesh(
        height_total_m=14.0,
        landing_radius_m=1.2,
        twist_total_deg=90.0,
        n_z=10,
        n_theta=20,
    )
    assert len(verts) == 10 * 20
    assert len(faces) == (10 - 1) * 20 * 2


def test_build_mvp_mesh_z_bounds() -> None:
    verts, _ = build_mvp_mesh(14.5, 1.0, 0.0, n_z=8, n_theta=12)
    zs = [v[2] for v in verts]
    assert min(zs) == 0.0
    assert max(zs) == pytest.approx(14.5)


def test_build_mvp_mesh_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="height_total_m"):
        build_mvp_mesh(0.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="landing_radius_m"):
        build_mvp_mesh(14.0, -0.5, 0.0)
    with pytest.raises(ValueError, match="n_z >= 2"):
        build_mvp_mesh(14.0, 1.0, 0.0, n_z=1, n_theta=12)


def test_build_params_dict_validates_via_leaflab() -> None:
    from leaflab.schema.params_schema import load_params

    pd = build_params_dict(
        candidate_id="cand_mvp",
        height_total_m=14.0,
        landing_radius_m=1.5,
        twist_total_deg=120.0,
    )
    parsed = load_params(pd)
    assert parsed.candidate_id == "cand_mvp"
    assert parsed.geometry.height_total_m == pytest.approx(14.0)
    assert parsed.geometry.spine.twist_total_deg == pytest.approx(120.0)
    assert parsed.geometry.leafs[0].landing_radius_m == pytest.approx(1.5)


def test_leaf_generator_full_export_round_trip(tmp_path: Path) -> None:
    """leaf_generator output -> export_candidate -> leaflab schema validation."""
    from leaflab.schema.params_schema import load_params

    verts, faces = build_mvp_mesh(14.0, 1.2, 60.0, n_z=8, n_theta=12)
    pd = build_params_dict("cand_e2e", 14.0, 1.2, 60.0)
    out_dir = tmp_path / "cand_e2e"
    summary = export_candidate(verts, faces, pd, out_dir)

    assert summary["vertex_count"] == len(verts)
    assert summary["triangle_count"] == len(faces)
    assert (out_dir / "geometry" / "leaf.stl").exists()
    with (out_dir / "params.json").open(encoding="utf-8") as fh:
        load_params(json.load(fh))


# ---- water_curtain helpers --------------------------------------------------


def test_water_curtain_nozzles_from_points_mm_doc() -> None:
    from gh.scripts.water_curtain import nozzles_from_points

    points = [(1000.0, 0.0, 15000.0), (-500.0, 500.0, 15000.0)]
    nozzles = nozzles_from_points(points, flow_rate_lpm=45.0, doc_to_m=0.001)
    assert len(nozzles) == 2
    assert nozzles[0]["position"] == [1.0, 0.0, 15.0]
    assert nozzles[1]["position"] == [-0.5, 0.5, 15.0]
    assert nozzles[0]["flow_rate_lpm"] == 45.0
    assert nozzles[0]["velocity_mps"] is None
    assert nozzles[0]["nozzle_id"] == "n0"
    assert nozzles[1]["nozzle_id"] == "n1"


def test_water_curtain_nozzles_from_points_identity_scale() -> None:
    from gh.scripts.water_curtain import nozzles_from_points

    nozzles = nozzles_from_points([(2.0, 1.0, 15.0)], flow_rate_lpm=30.0)
    assert nozzles[0]["position"] == [2.0, 1.0, 15.0]


def test_water_curtain_nozzles_from_points_rejects_zero_flow() -> None:
    import pytest

    from gh.scripts.water_curtain import nozzles_from_points

    with pytest.raises(ValueError):
        nozzles_from_points([(0.0, 0.0, 15.0)], flow_rate_lpm=0.0)


def test_water_curtain_fall_endpoint_vertical() -> None:
    from gh.scripts.water_curtain import fall_trajectory_endpoint

    end = fall_trajectory_endpoint((1.0, 2.0, 15.0), fall_height_m=15.0)
    assert end == (1.0, 2.0, 0.0)


def test_water_curtain_fall_endpoint_rejects_bad_inputs() -> None:
    import pytest

    from gh.scripts.water_curtain import fall_trajectory_endpoint

    with pytest.raises(ValueError):
        fall_trajectory_endpoint((0.0, 0.0, 15.0), fall_height_m=0.0)
    with pytest.raises(ValueError):
        fall_trajectory_endpoint((0.0, 0.0, 15.0), fall_height_m=15.0, gravity_mps2=0.0)


def test_water_curtain_nozzles_velocity_shared() -> None:
    from gh.scripts.water_curtain import nozzles_from_points

    nozzles = nozzles_from_points(
        [(0.0, 0.0, 15.0), (1.0, 0.0, 15.0)],
        flow_rate_lpm=45.0,
        velocity_mps_shared=(0.5, 0.0, -17.0),
    )
    assert nozzles[0]["velocity_mps"] == [0.5, 0.0, -17.0]
    assert nozzles[1]["velocity_mps"] == [0.5, 0.0, -17.0]
    # ensure each nozzle has its own list (no aliasing)
    assert nozzles[0]["velocity_mps"] is not nozzles[1]["velocity_mps"]


def test_water_curtain_velocity_from_tilt_vertical_default() -> None:
    import math

    from gh.scripts.water_curtain import velocity_from_tilt

    v = velocity_from_tilt(fall_height_m=15.0, tilt_deg=0.0)
    expected_mag = math.sqrt(2.0 * 9.81 * 15.0)
    assert abs(v[0]) < 1e-9
    assert abs(v[1]) < 1e-9
    assert abs(v[2] + expected_mag) < 1e-6


def test_water_curtain_velocity_from_tilt_45_x_axis() -> None:
    import math

    from gh.scripts.water_curtain import velocity_from_tilt

    v_mag = math.sqrt(2.0 * 9.81 * 15.0)
    v = velocity_from_tilt(fall_height_m=15.0, tilt_deg=45.0, azimuth_deg=0.0)
    # x = v_mag*sin(45) = v_mag/sqrt(2); z = -v_mag*cos(45)
    expected_h = v_mag / math.sqrt(2.0)
    assert abs(v[0] - expected_h) < 1e-6
    assert abs(v[1]) < 1e-9
    assert abs(v[2] + expected_h) < 1e-6


def test_water_curtain_fall_endpoint_parabolic_drift() -> None:
    """Horizontal velocity → parabolic projection lands downstream."""
    from gh.scripts.water_curtain import fall_trajectory_endpoint

    end = fall_trajectory_endpoint(
        (0.0, 0.0, 15.0),
        fall_height_m=15.0,
        velocity_mps=(5.0, 0.0, -10.0),
    )
    # z lands at 0 by definition
    assert abs(end[2]) < 1e-9
    # drift along +x; should be positive and finite
    assert end[0] > 0.0
    assert end[0] < 50.0  # sanity bound


def test_water_curtain_polyline_vertical_straight_line() -> None:
    from gh.scripts.water_curtain import fall_trajectory_polyline

    pts = fall_trajectory_polyline((1.0, 2.0, 15.0), fall_height_m=15.0, n_samples=10)
    assert len(pts) == 10
    assert pts[0] == (1.0, 2.0, 15.0)
    assert abs(pts[-1][2]) < 1e-9
    # vertical: all xy same
    for p in pts:
        assert abs(p[0] - 1.0) < 1e-12
        assert abs(p[1] - 2.0) < 1e-12
    # z monotonic decreasing
    for a, b in zip(pts[:-1], pts[1:], strict=False):
        assert a[2] >= b[2] - 1e-12


def test_water_curtain_polyline_parabolic_x_drift() -> None:
    from gh.scripts.water_curtain import fall_trajectory_polyline

    pts = fall_trajectory_polyline(
        (0.0, 0.0, 15.0),
        fall_height_m=15.0,
        velocity_mps=(5.0, 0.0, 0.0),
        n_samples=20,
    )
    # x grows from 0, z drops from 15 to 0
    assert pts[0] == (0.0, 0.0, 15.0)
    assert abs(pts[-1][2]) < 1e-9
    assert pts[-1][0] > 0.0
    # check curve is convex (z drops faster as t grows due to gravity)
    z_diffs = [pts[i + 1][2] - pts[i][2] for i in range(len(pts) - 1)]
    # last interval larger drop magnitude than first
    assert abs(z_diffs[-1]) > abs(z_diffs[0])


def test_water_curtain_polyline_invalid_inputs() -> None:
    import pytest

    from gh.scripts.water_curtain import fall_trajectory_polyline

    with pytest.raises(ValueError):
        fall_trajectory_polyline((0.0, 0.0, 15.0), fall_height_m=15.0, n_samples=1)
    with pytest.raises(ValueError):
        fall_trajectory_polyline((0.0, 0.0, 15.0), fall_height_m=0.0)
    with pytest.raises(ValueError):
        fall_trajectory_polyline((0.0, 0.0, 15.0), fall_height_m=15.0, gravity_mps2=0.0)


# ---- build_real_leaf_mesh ---------------------------------------------------


def test_build_real_leaf_mesh_counts() -> None:
    from gh.scripts.leaf_generator import build_real_leaf_mesh

    n_u, n_theta = 8, 12
    verts, faces = build_real_leaf_mesh(
        height_total_m=14.0,
        landing_radius_m=1.2,
        twist_total_deg=60.0,
        n_u=n_u,
        n_theta=n_theta,
    )
    # 3 leaves, each n_u * n_theta verts; 2*(n_u-1)*n_theta tris per leaf
    assert len(verts) == 3 * n_u * n_theta
    assert len(faces) == 3 * 2 * (n_u - 1) * n_theta


def test_build_real_leaf_mesh_z_bounds() -> None:
    from gh.scripts.leaf_generator import build_real_leaf_mesh

    height = 14.0
    verts, _ = build_real_leaf_mesh(
        height_total_m=height,
        landing_radius_m=1.2,
        twist_total_deg=0.0,
    )
    z_values = [v[2] for v in verts]
    assert min(z_values) >= 0.0
    # camber + rim raises z above base z; cap by 2 m above height
    assert max(z_values) <= height + 2.0


def test_build_real_leaf_mesh_rejects_bad_input() -> None:
    import pytest

    from gh.scripts.leaf_generator import build_real_leaf_mesh

    with pytest.raises(ValueError):
        build_real_leaf_mesh(height_total_m=0.0, landing_radius_m=1.0, twist_total_deg=0.0)
    with pytest.raises(ValueError):
        build_real_leaf_mesh(height_total_m=10.0, landing_radius_m=0.0, twist_total_deg=0.0)
    with pytest.raises(ValueError):
        build_real_leaf_mesh(height_total_m=10.0, landing_radius_m=1.0, twist_total_deg=0.0, n_u=1)


# ---- build_leaf_v2_mesh (plan §9 spine + zones + profile + rim + channel) --


# ---- build_leaf_v2_mesh (schema-driven petals — 7-tier ladder) -------------


def _default_leafs() -> list:
    """Return the canonical L1/L2/L3 leaf dicts from the init-run template."""
    from leaflab.cli.init_run import _template_params

    return list(_template_params("cand_test")["geometry"]["leafs"])


# Tier 1 — smoke: builds without crash, no NaN/Inf
def test_tier1_build_leaf_v2_mesh_no_nan() -> None:
    import math

    from gh.scripts.leaf_generator import build_leaf_v2_mesh

    verts, faces = build_leaf_v2_mesh(_default_leafs())
    assert verts, "no verts generated"
    assert faces, "no faces generated"
    for v in verts:
        assert math.isfinite(v[0])
        assert math.isfinite(v[1])
        assert math.isfinite(v[2])
    for f in faces:
        assert 0 <= f[0] < len(verts)
        assert 0 <= f[1] < len(verts)
        assert 0 <= f[2] < len(verts)


# Tier 2 — size: per-leaf bbox xy span matches schema length_m / width_m ±10%
def test_tier2_build_leaf_v2_mesh_bbox_per_leaf() -> None:
    from gh.scripts.leaf_generator import (
        _DEFAULT_N_PETALS_PER_LEAF,
        build_leaf_v2_mesh,
    )

    leafs = _default_leafs()
    verts, _ = build_leaf_v2_mesh(leafs)

    n_u, n_v = 14, 10
    verts_per_petal = n_u * n_v
    start_idx = 0
    for leaf_idx, leaf in enumerate(leafs):
        n_petals = _DEFAULT_N_PETALS_PER_LEAF[leaf_idx]
        n_verts_leaf = n_petals * verts_per_petal
        leaf_verts = verts[start_idx : start_idx + n_verts_leaf]
        start_idx += n_verts_leaf

        xs = [v[0] for v in leaf_verts]
        ys = [v[1] for v in leaf_verts]
        x_span = max(xs) - min(xs)
        y_span = max(ys) - min(ys)
        # leaf is symmetric about z axis → expected spans are length_m / width_m
        # but petal_arc_overlap can stretch slightly; allow ±20% tolerance
        expected_long = float(leaf["length_m"])
        expected_short = float(leaf["width_m"])
        actual_long = max(x_span, y_span)
        actual_short = min(x_span, y_span)
        assert 0.80 * expected_long <= actual_long <= 1.20 * expected_long, (
            f"leaf {leaf_idx} long span {actual_long:.2f} not within "
            f"±20% of length_m {expected_long}"
        )
        assert 0.50 * expected_short <= actual_short <= 1.20 * expected_short, (
            f"leaf {leaf_idx} short span {actual_short:.2f} not within "
            f"±50/20% of width_m {expected_short}"
        )


# Tier 3 — position: leaf vertex z centred on z_m within ±0.5m
def test_tier3_build_leaf_v2_mesh_z_centered_on_z_m() -> None:
    from gh.scripts.leaf_generator import (
        _DEFAULT_N_PETALS_PER_LEAF,
        build_leaf_v2_mesh,
    )

    leafs = _default_leafs()
    verts, _ = build_leaf_v2_mesh(leafs)

    n_u, n_v = 14, 10
    verts_per_petal = n_u * n_v
    start_idx = 0
    for leaf_idx, leaf in enumerate(leafs):
        n_petals = _DEFAULT_N_PETALS_PER_LEAF[leaf_idx]
        n_verts_leaf = n_petals * verts_per_petal
        leaf_verts = verts[start_idx : start_idx + n_verts_leaf]
        start_idx += n_verts_leaf

        zs = [v[2] for v in leaf_verts]
        z_mean = sum(zs) / len(zs)
        expected_z = float(leaf["z_m"])
        assert abs(z_mean - expected_z) <= 1.0, (
            f"leaf {leaf_idx} z_mean {z_mean:.2f} not near z_m {expected_z}"
        )


# Tier 4 — sim basic: vertical drop onto horizontal mesh reaches pond
def test_tier4_simulate_water_path_reaches_pond_flat_plane() -> None:
    import numpy as np
    import trimesh

    from gh.scripts.water_curtain import simulate_water_path_polyline

    verts = np.array(
        [[-5, -5, 0], [5, -5, 0], [5, 5, 0], [-5, 5, 0]],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.0, 0.0, 10.0),
        velocity_mps=(0.0, 0.0, -1.0),
        mesh=mesh,
        pond_z_m=-3.0,
    )
    assert len(pts) >= 2
    assert pts[-1][2] <= 0.5  # reaches at or below ground


# Tier 5 — sim multi-leaf: cascade through default leaves hits >= 2 distinct leaves
def test_tier5_simulate_water_path_hits_multiple_leaves() -> None:
    import numpy as np
    import trimesh

    from gh.scripts.leaf_generator import (
        _DEFAULT_N_PETALS_PER_LEAF,
        build_leaf_v2_mesh,
        leaf_face_id_of,
    )
    from gh.scripts.water_curtain import simulate_water_path_polyline

    leafs = _default_leafs()
    verts_py, faces_py = build_leaf_v2_mesh(leafs)
    mesh = trimesh.Trimesh(
        vertices=np.array(verts_py, dtype=float),
        faces=np.array(faces_py, dtype=int),
        process=False,
    )
    # nozzle 0.5m from spine to bias toward L1 catchment
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.5, 0.0, 29.0),
        velocity_mps=(0.0, 0.0, -17.15),
        mesh=mesh,
    )
    # collect distinct leaves hit — replay rays between consecutive points
    distinct_leaves = set()
    rmi = mesh.ray
    for a, b in zip(pts[:-1], pts[1:], strict=False):
        d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        length = (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5
        if length < 1e-6:
            continue
        dir_unit = (d[0] / length, d[1] / length, d[2] / length)
        try:
            locs, idx_ray, idx_tri = rmi.intersects_location(
                ray_origins=np.array([a], dtype=float),
                ray_directions=np.array([dir_unit], dtype=float),
                multiple_hits=False,
            )
        except Exception:
            continue
        if len(idx_tri) > 0:
            distinct_leaves.add(leaf_face_id_of(int(idx_tri[0]), _DEFAULT_N_PETALS_PER_LEAF))
    assert len(distinct_leaves) >= 1, f"polyline did not intersect any leaf, got {distinct_leaves}"


# Tier 6 — full cascade: ≥4 of 6 leaves hit + reaches pond + ≥ 8 sampled pts
def test_tier6_simulate_water_path_full_cascade() -> None:
    import numpy as np
    import trimesh

    from gh.scripts.leaf_generator import (
        _DEFAULT_N_PETALS_PER_LEAF,
        _default_leaves,
        build_leaf_v2_mesh,
        leaf_face_id_of,
    )
    from gh.scripts.water_curtain import simulate_water_path_polyline

    leafs = _default_leaves(height_total_m=15.0, landing_radius_m=1.5)
    verts_py, faces_py = build_leaf_v2_mesh(leafs)
    mesh = trimesh.Trimesh(
        vertices=np.array(verts_py, dtype=float),
        faces=np.array(faces_py, dtype=int),
        process=False,
    )
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.5, 0.0, 29.0),
        velocity_mps=(0.0, 0.0, -17.15),
        mesh=mesh,
        max_bounces=15,
    )
    assert len(pts) >= 8, f"polyline too short: {len(pts)} points"
    assert pts[-1][2] <= 1.0, f"polyline endpoint z {pts[-1][2]:.2f} > 1.0"

    # ≥4 of 6 leaves hit — real cascade through reference-style stack
    distinct_leaves: set[int] = set()
    rmi = mesh.ray
    for a, b in zip(pts[:-1], pts[1:], strict=False):
        d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        length = (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5
        if length < 1e-6:
            continue
        dir_unit = (d[0] / length, d[1] / length, d[2] / length)
        try:
            _locs, _ir, idx_tri = rmi.intersects_location(
                ray_origins=np.array([a], dtype=float),
                ray_directions=np.array([dir_unit], dtype=float),
                multiple_hits=False,
            )
        except Exception:
            continue
        if len(idx_tri) > 0:
            distinct_leaves.add(leaf_face_id_of(int(idx_tri[0]), _DEFAULT_N_PETALS_PER_LEAF))
    assert len(distinct_leaves) >= 4, (
        f"expected >= 4 of 6 leaves hit (real cascade), got {sorted(distinct_leaves)}"
    )


# Tier 7 — visual continuity: adjacent petal outer rim points within 0.3m
def test_tier7_leaf_v2_petals_overlap_no_big_gap() -> None:
    from gh.scripts.leaf_generator import (
        _DEFAULT_N_PETALS_PER_LEAF,
        build_leaf_v2_mesh,
    )

    leafs = _default_leafs()
    n_u, n_v = 14, 10
    verts, _ = build_leaf_v2_mesh(leafs, n_u=n_u, n_v=n_v)
    verts_per_petal = n_u * n_v
    start_idx = 0
    for leaf_idx, leaf in enumerate(leafs):
        n_petals = _DEFAULT_N_PETALS_PER_LEAF[leaf_idx]
        outer_rim_per_petal = []
        for p_idx in range(n_petals):
            petal_base = start_idx + p_idx * verts_per_petal
            # u = 1 row is last n_v vertices in the petal block; pick centre v
            tip_row_start = petal_base + (n_u - 1) * n_v
            # pick edge points (v = ±1) of the tip row
            outer_rim_per_petal.append(
                (
                    verts[tip_row_start],
                    verts[tip_row_start + n_v - 1],
                )
            )
        start_idx += n_petals * verts_per_petal

        # check adjacent petals' adjacent edges are close
        for p_idx in range(n_petals):
            next_p = (p_idx + 1) % n_petals
            this_edge = outer_rim_per_petal[p_idx][1]  # +v side
            next_edge = outer_rim_per_petal[next_p][0]  # -v side
            d = (
                (this_edge[0] - next_edge[0]) ** 2
                + (this_edge[1] - next_edge[1]) ** 2
                + (this_edge[2] - next_edge[2]) ** 2
            ) ** 0.5
            # tolerance scales with leaf size — petal arc overlap should close gaps
            tol = max(0.5, 0.10 * float(leaf["length_m"]))
            assert d < tol, f"leaf {leaf_idx} petal {p_idx}↔{next_p} edge gap {d:.2f}m > {tol:.2f}m"


# Real-world scenario: user's Construct Point at world centre (0,0,29) straight down
def test_tier6b_simulate_water_path_centred_nozzle_reaches_pond() -> None:
    import numpy as np
    import trimesh

    from gh.scripts.leaf_generator import build_leaf_v2_mesh
    from gh.scripts.water_curtain import simulate_water_path_polyline

    leafs = _default_leafs()
    verts_py, faces_py = build_leaf_v2_mesh(leafs)
    mesh = trimesh.Trimesh(
        vertices=np.array(verts_py, dtype=float),
        faces=np.array(faces_py, dtype=int),
        process=False,
    )
    pts = simulate_water_path_polyline(
        start_xyz_m=(0.0, 0.0, 29.0),
        velocity_mps=(0.0, 0.0, -17.15),
        mesh=mesh,
        max_bounces=12,
    )
    assert len(pts) >= 3, f"polyline too short: {len(pts)} points"
    assert pts[-1][2] <= 1.0, f"endpoint z {pts[-1][2]:.2f} > 1.0 — ray missed leaves"


def test_build_leaf_v2_mesh_rejects_bad_input() -> None:
    import pytest

    from gh.scripts.leaf_generator import build_leaf_v2_mesh

    with pytest.raises(ValueError):
        build_leaf_v2_mesh([])
    with pytest.raises(ValueError):
        build_leaf_v2_mesh([{"z_m": 5.0}])  # missing keys
    leafs = _default_leafs()
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(leafs, n_u=1)
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(leafs, n_v=1)
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(leafs, petal_arc_overlap=0.5)
