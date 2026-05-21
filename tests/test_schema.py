from __future__ import annotations

import pytest
from pydantic import ValidationError

from leaflab.schema.params_schema import ParamsV1, load_params
from leaflab.schema.version import CURRENT_PARAMS_VERSION, SchemaVersion


def test_template_params_validates(sample_params_dict: dict) -> None:
    params = load_params(sample_params_dict)
    assert isinstance(params, ParamsV1)
    assert params.candidate_id == "cand_test"
    assert params.schema_version == CURRENT_PARAMS_VERSION.value


def test_missing_schema_version_rejected(sample_params_dict: dict) -> None:
    del sample_params_dict["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        load_params(sample_params_dict)


def test_unknown_schema_version_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["schema_version"] = "99.0"
    with pytest.raises(ValueError, match="unknown params schema_version"):
        load_params(sample_params_dict)


def test_negative_height_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["height_total_m"] = -1.0
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_height_exceeds_15m_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["height_total_m"] = 20.0
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_extra_field_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["nonsense_field"] = 123
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_schema_version_enum_has_v1() -> None:
    assert SchemaVersion.V1_0.value == "1.0"


def test_leaf_count_mismatch_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["leaf_count"] = 4
    with pytest.raises(ValidationError, match="leaf_count"):
        load_params(sample_params_dict)


def test_top_leaf_z_above_height_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["top_leaf_z_m"] = 14.8
    sample_params_dict["geometry"]["height_total_m"] = 14.5
    with pytest.raises(ValidationError, match="top_leaf_z_m"):
        load_params(sample_params_dict)


def test_top_leaf_z_below_base_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["base_z_m"] = 1.0
    sample_params_dict["geometry"]["top_leaf_z_m"] = 0.5
    with pytest.raises(ValidationError, match="base_z_m"):
        load_params(sample_params_dict)


def test_algorithm_version_default_on_metrics() -> None:
    from leaflab.schema.metrics_schema import (
        FastMetricsV1,
        GeometryProxyMetrics,
        WaterProxyMetrics,
    )

    water = WaterProxyMetrics(
        impact_angle_mean_deg=10.0,
        impact_angle_p95_deg=20.0,
        normal_impact_score=0.15,
        attachment_length_m=8.0,
        attachment_ratio=0.7,
        edge_escape_rate=0.05,
        edge_escape_risk=0.1,
        curvature_gradient_mean=0.1,
        drain_target_error_m=0.3,
        splash_proxy=0.2,
    )
    geo = GeometryProxyMetrics(
        height_total_m=14.0,
        surface_area_m2=42.0,
        volume_estimate_m3=0.8,
        mean_gaussian_curvature=0.02,
        mean_curvature_variation=0.1,
        rim_continuity_score=0.8,
        channel_continuity_score=0.75,
    )
    m = FastMetricsV1(candidate_id="cand_x", water_proxy=water, geometry_proxy=geo)
    assert m.algorithm_version == "1.0.0"


def test_algorithm_version_override_on_metrics() -> None:
    from leaflab.schema.metrics_schema import GeometryCheckV1

    g = GeometryCheckV1(
        candidate_id="c",
        stl_path="/tmp/x.stl",
        height_m=14.0,
        radius_m=2.0,
        bbox_min=(0.0, 0.0, 0.0),
        bbox_max=(3.0, 2.0, 14.0),
        surface_area_m2=42.0,
        volume_estimate_m3=0.8,
        triangle_count=12,
        vertex_count=8,
        is_watertight=True,
        is_manifold=True,
        normal_consistency=0.99,
        scale_warning=False,
        algorithm_version="trimesh-2.1.0",
    )
    assert g.algorithm_version == "trimesh-2.1.0"
