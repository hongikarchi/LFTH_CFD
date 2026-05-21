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


def test_build_leaf_v2_mesh_counts() -> None:
    from gh.scripts.leaf_generator import _LEAF_V2_TOTAL_PETALS, build_leaf_v2_mesh

    n_u, n_v = 10, 8
    verts, faces = build_leaf_v2_mesh(
        height_total_m=14.0,
        landing_radius_m=1.2,
        twist_total_deg=60.0,
        n_u=n_u,
        n_v=n_v,
    )
    assert len(verts) == _LEAF_V2_TOTAL_PETALS * n_u * n_v
    assert len(faces) == _LEAF_V2_TOTAL_PETALS * 2 * (n_u - 1) * (n_v - 1)


def test_build_leaf_v2_mesh_no_nan_and_z_bounded() -> None:
    import math

    from gh.scripts.leaf_generator import build_leaf_v2_mesh

    height = 14.0
    verts, _ = build_leaf_v2_mesh(
        height_total_m=height,
        landing_radius_m=1.2,
        twist_total_deg=0.0,
    )
    for v in verts:
        for c in v:
            assert math.isfinite(c)
    z_values = [v[2] for v in verts]
    assert min(z_values) >= -2.0
    assert max(z_values) <= height + 3.0


def test_build_leaf_v2_mesh_twist_rotates_xy() -> None:
    """Non-zero twist should change xy positions vs twist=0."""
    from gh.scripts.leaf_generator import build_leaf_v2_mesh

    verts_a, _ = build_leaf_v2_mesh(
        height_total_m=14.0,
        landing_radius_m=1.2,
        twist_total_deg=0.0,
        n_u=6,
        n_v=4,
    )
    verts_b, _ = build_leaf_v2_mesh(
        height_total_m=14.0,
        landing_radius_m=1.2,
        twist_total_deg=180.0,
        n_u=6,
        n_v=4,
    )
    differ = any(
        abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6
        for a, b in zip(verts_a, verts_b, strict=False)
    )
    assert differ, "twist=180 should change xy from twist=0"


def test_build_leaf_v2_mesh_rejects_bad_input() -> None:
    import pytest

    from gh.scripts.leaf_generator import build_leaf_v2_mesh

    with pytest.raises(ValueError):
        build_leaf_v2_mesh(height_total_m=0.0, landing_radius_m=1.0, twist_total_deg=0.0)
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(height_total_m=10.0, landing_radius_m=0.0, twist_total_deg=0.0)
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(height_total_m=10.0, landing_radius_m=1.0, twist_total_deg=0.0, n_u=1)
    with pytest.raises(ValueError):
        build_leaf_v2_mesh(height_total_m=10.0, landing_radius_m=1.0, twist_total_deg=0.0, n_v=1)
