"""Candidate input params (params.json) — Pydantic v2 models.

Schema versioning uses a discriminator pattern, not rigid Literal: raw JSON is
loaded, `schema_version` inspected, and the matching model parses it. This
allows `leaflab migrate` to read old versions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from leaflab.schema.version import SchemaVersion


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)


class GlobalConstraints(StrictModel):
    max_height_m: float = Field(gt=0, le=20.0)
    min_height_m: float = Field(gt=0)
    max_plan_radius_m: float = Field(gt=0)
    target_visual_axis: str


class SpineParams(StrictModel):
    type: str = "bezier_or_nurbs"
    control_points: list[tuple[float, float, float]] = Field(min_length=2)
    twist_total_deg: float = 0.0


class LeafParams(StrictModel):
    """Per-leaf geometry. z_m is the horizontal-centre height (m).

    length_m and width_m are the leaf's horizontal long-axis and
    short-axis diameters in meters; the leaf plate is roughly an
    ellipse of those dimensions, centred at (0, 0, z_m).
    """

    leaf_id: str
    z_m: float
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    camber: float = Field(ge=0, le=1)
    twist_deg: float = 0.0
    pitch_deg: float = 0.0
    landing_angle_deg: float | None = None
    landing_radius_m: float | None = None
    rim_height_m: float = Field(gt=0)
    rim_thickness_m: float = Field(gt=0)
    channel_depth_m: float = Field(gt=0)
    channel_offset_m: float
    overlap_to_next_m: float | None = None


class GeometryParams(StrictModel):
    leaf_count: int = Field(ge=1, le=12)
    single_surface_intent: bool = True
    height_total_m: float = Field(gt=0, le=15.0)
    base_z_m: float = 0.0
    top_leaf_z_m: float
    spine: SpineParams
    leafs: list[LeafParams] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_cross_fields(self) -> GeometryParams:
        if len(self.leafs) != self.leaf_count:
            raise ValueError(
                f"geometry.leaf_count={self.leaf_count} but len(leafs)={len(self.leafs)}"
            )
        if self.top_leaf_z_m > self.height_total_m:
            raise ValueError(
                f"geometry.top_leaf_z_m={self.top_leaf_z_m} > height_total_m={self.height_total_m}"
            )
        if self.top_leaf_z_m < self.base_z_m:
            raise ValueError(
                f"geometry.top_leaf_z_m={self.top_leaf_z_m} < base_z_m={self.base_z_m}"
            )
        return self


class NozzleParams(StrictModel):
    """Per-point water release. Positions in meters, world frame.

    When `WaterParams.nozzles` is set (non-empty list), the fast_sim
    samples particles from these nozzle discs instead of the annulus.
    """

    position: tuple[float, float, float]
    flow_rate_lpm: float = Field(gt=0)
    velocity_mps: tuple[float, float, float] | None = None
    nozzle_id: str


class WaterParams(StrictModel):
    fall_height_m: float = Field(gt=0)
    gravity_mps2: float = 9.81
    estimated_impact_velocity_mps: float = Field(gt=0)
    inlet_type: str
    curtain_radius_inner_m: float = Field(gt=0)
    curtain_radius_outer_m: float = Field(gt=0)
    nozzle_spacing_mm: float = Field(gt=0)
    flow_rate_per_nozzle_lpm: float = Field(gt=0)
    flow_rate_min_lpm: float = Field(gt=0)
    flow_rate_max_lpm: float = Field(gt=0)
    target_drain_position: tuple[float, float, float]
    pond_radius_m: float = Field(gt=0)
    nozzles: list[NozzleParams] | None = None


class MaterialParams(StrictModel):
    base_material: str
    finish: str
    density_kg_m3: float = Field(gt=0)
    shell_thickness_mm: float = Field(gt=0)
    min_shell_thickness_mm: float = Field(gt=0)
    max_shell_thickness_mm: float = Field(gt=0)
    coating_note: str = ""


class StructureParams(StrictModel):
    support_type: str
    visible_internal_frame: bool = False
    base_plate_radius_m: float = Field(gt=0)
    anchor_count: int = Field(ge=1)
    rim_as_structural_edge: bool = True
    channel_as_spine: bool = True


class CameraParams(StrictModel):
    position: tuple[float, float, float]
    target: tuple[float, float, float]


class ViewParams(StrictModel):
    facade_camera: CameraParams
    eye_level_camera: CameraParams
    mezzanine_camera: CameraParams


class ParamsV1(StrictModel):
    schema_version: str = Field(default=SchemaVersion.V1_0.value)
    candidate_id: str
    description: str = ""
    global_constraints: GlobalConstraints
    geometry: GeometryParams
    water: WaterParams
    material: MaterialParams
    structure: StructureParams
    views: ViewParams


PARAMS_MODELS: dict[str, type[StrictModel]] = {
    SchemaVersion.V1_0.value: ParamsV1,
}


def load_params(data: dict[str, Any]) -> ParamsV1:
    """Discriminator-pattern loader for params.json.

    Reads `schema_version`, dispatches to the matching Pydantic model, then
    converts to the current version. For now only V1.0 exists, so no migration.
    """
    version = data.get("schema_version")
    if version is None:
        raise ValueError("params.json missing required 'schema_version' field")
    model_cls = PARAMS_MODELS.get(version)
    if model_cls is None:
        raise ValueError(
            f"unknown params schema_version: {version!r} (known: {list(PARAMS_MODELS)})"
        )
    parsed = model_cls.model_validate(data)
    if not isinstance(parsed, ParamsV1):
        raise NotImplementedError(f"migration from {version!r} to current not yet implemented")
    return parsed
