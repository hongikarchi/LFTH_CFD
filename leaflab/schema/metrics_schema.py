"""Metrics outputs — fast_metrics, karamba_metrics, cfd_metrics, visual_metrics, score."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from leaflab.schema.version import SchemaVersion


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WaterProxyMetrics(StrictModel):
    impact_angle_mean_deg: float
    impact_angle_p95_deg: float
    normal_impact_score: float = Field(ge=0, le=1)
    attachment_length_m: float = Field(ge=0)
    attachment_ratio: float = Field(ge=0, le=1)
    edge_escape_rate: float = Field(ge=0, le=1)
    edge_escape_risk: float = Field(ge=0, le=1)
    curvature_gradient_mean: float
    drain_target_error_m: float = Field(ge=0)
    splash_proxy: float = Field(ge=0)


class GeometryProxyMetrics(StrictModel):
    height_total_m: float
    surface_area_m2: float
    volume_estimate_m3: float
    mean_gaussian_curvature: float
    mean_curvature_variation: float
    rim_continuity_score: float = Field(ge=0, le=1)
    channel_continuity_score: float = Field(ge=0, le=1)


class FastMetricsV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    water_proxy: WaterProxyMetrics
    geometry_proxy: GeometryProxyMetrics


class StructureMetrics(StrictModel):
    mass_kg: float = Field(ge=0)
    max_displacement_mm: float = Field(ge=0)
    max_stress_mpa: float = Field(ge=0)
    stress_concentration_index: float = Field(ge=0)
    support_reaction_max_kn: float = Field(ge=0)
    overturning_ratio: float = Field(ge=0)
    buckling_proxy: float = Field(ge=0)
    min_thickness_mm: float = Field(gt=0)
    fabrication_thickness_ok: bool


class KarambaMetricsV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    structure: StructureMetrics


class OpenFOAMRunInfo(StrictModel):
    case_type: str
    solver: str
    mesh_cells: int = Field(ge=0)
    simulation_time_s: float = Field(gt=0)
    delta_t_max_s: float = Field(gt=0)


class CFDResults(StrictModel):
    splash_volume_ratio: float = Field(ge=0, le=1)
    attachment_ratio: float = Field(ge=0, le=1)
    overspray_radius_95_m: float = Field(ge=0)
    pond_capture_ratio: float = Field(ge=0, le=1)
    peak_pressure_pa: float = Field(ge=0)
    pressure_impulse_pa_s: float = Field(ge=0)
    water_sheet_continuity_score: float = Field(ge=0, le=1)
    mist_risk_index: float = Field(ge=0, le=1)


class CFDMetricsV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    openfoam: OpenFOAMRunInfo
    cfd_results: CFDResults


class VisualScores(StrictModel):
    big_leaf_similarity: float = Field(ge=0, le=1)
    eye_level_silhouette_score: float = Field(ge=0, le=1)
    top_view_water_path_clarity: float = Field(ge=0, le=1)
    facade_visibility_score: float = Field(ge=0, le=1)
    mezzanine_360_visibility_score: float = Field(ge=0, le=1)
    visual_mass_score: float = Field(ge=0, le=1)
    surface_continuity_score: float = Field(ge=0, le=1)


class VisualMetricsV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    visual: VisualScores


class ScoreV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    score_water: float = Field(ge=0, le=1)
    score_structure: float = Field(ge=0, le=1)
    score_visual: float = Field(ge=0, le=1)
    score_total_weighted: float = Field(ge=0, le=1)
    pareto_rank: int = Field(ge=1)
    notes: list[str] = Field(default_factory=list)


class GeometryCheckV1(StrictModel):
    """Output of `leaflab check-geometry` — STL sanity check (scale, height, manifold, normals)."""

    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    stl_path: str
    height_m: float = Field(ge=0)
    radius_m: float = Field(ge=0)
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    surface_area_m2: float = Field(ge=0)
    volume_estimate_m3: float
    triangle_count: int = Field(ge=0)
    vertex_count: int = Field(ge=0)
    is_watertight: bool
    is_manifold: bool
    normal_consistency: float = Field(ge=0, le=1)
    scale_warning: bool
    warnings: list[str] = Field(default_factory=list)


METRICS_MODELS: dict[str, dict[str, type[StrictModel]]] = {
    "fast": {SchemaVersion.V1_0.value: FastMetricsV1},
    "karamba": {SchemaVersion.V1_0.value: KarambaMetricsV1},
    "cfd": {SchemaVersion.V1_0.value: CFDMetricsV1},
    "visual": {SchemaVersion.V1_0.value: VisualMetricsV1},
    "score": {SchemaVersion.V1_0.value: ScoreV1},
    "geometry_check": {SchemaVersion.V1_0.value: GeometryCheckV1},
}


def load_metrics(kind: str, data: dict[str, Any]) -> StrictModel:
    """Discriminator loader for metrics files. `kind` ∈ {fast, karamba, cfd, visual, score}."""
    if kind not in METRICS_MODELS:
        raise ValueError(f"unknown metrics kind: {kind!r}")
    version = data.get("schema_version")
    if version is None:
        raise ValueError(f"{kind}_metrics.json missing 'schema_version'")
    model_cls = METRICS_MODELS[kind].get(version)
    if model_cls is None:
        raise ValueError(
            f"unknown {kind} schema_version: {version!r} (known: {list(METRICS_MODELS[kind])})"
        )
    return model_cls.model_validate(data)
