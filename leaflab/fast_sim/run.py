"""Orchestrator: mesh + params → FastMetricsV1 (water proxy + geometry proxy)."""

from __future__ import annotations

import math

import numpy as np
import trimesh

from leaflab.fast_sim.drain_target import evaluate_drain
from leaflab.fast_sim.geometry_proxy import compute_geometry_proxy
from leaflab.fast_sim.impact_angle import raycast_first_contact
from leaflab.fast_sim.particle_drop import (
    DEFAULT_PARTICLE_COUNT,
    particle_field_from_params,
)
from leaflab.fast_sim.sliding import slide_along_surface
from leaflab.fast_sim.splash_proxy import curvature_gradient_mean, splash_score
from leaflab.schema.metrics_schema import FastMetricsV1, WaterProxyMetrics
from leaflab.schema.params_schema import ParamsV1

ALGORITHM_VERSION = "0.1.0"


def run_fast_sim(
    mesh: trimesh.Trimesh,
    params: ParamsV1,
    *,
    n_particles: int = DEFAULT_PARTICLE_COUNT,
    seed: int = 42,
    n_slide_steps: int = 200,
    dt_s: float = 0.01,
) -> FastMetricsV1:
    """Full water proxy pipeline for one candidate."""
    field = particle_field_from_params(params, n=n_particles, seed=seed)
    impact = raycast_first_contact(mesh, field)
    hit = impact.hit_mask

    v_init_z = -math.sqrt(2.0 * params.water.gravity_mps2 * params.water.fall_height_m)
    sliding = slide_along_surface(
        mesh,
        impact,
        n_steps=n_slide_steps,
        dt_s=dt_s,
        gravity_mps2=params.water.gravity_mps2,
        initial_velocity_z=v_init_z,
    )

    if hit.any():
        ni = impact.normal_impact[hit]
        angles_deg = np.degrees(np.arcsin(np.clip(ni, 0.0, 1.0)))
        impact_angle_mean_deg = float(angles_deg.mean())
        impact_angle_p95_deg = float(np.quantile(angles_deg, 0.95))
        normal_impact_score = float(np.clip(ni.mean(), 0.0, 1.0))
        attachment_length_m = float(sliding.arc_length_m[hit].mean())
        off = sliding.off_edge[hit]
        edge_escape_rate = float(off.mean())
        attachment_ratio = float(1.0 - edge_escape_rate)
    else:
        impact_angle_mean_deg = 0.0
        impact_angle_p95_deg = 0.0
        normal_impact_score = 0.0
        attachment_length_m = 0.0
        edge_escape_rate = 0.0
        attachment_ratio = 0.0

    drain = evaluate_drain(
        sliding.endpoints[hit] if hit.any() else np.zeros((0, 3)),
        params.water.target_drain_position,
        params.water.pond_radius_m,
    )
    if drain.distance_to_target_m.size > 0:
        drain_target_error_m = float(np.median(drain.distance_to_target_m))
    else:
        drain_target_error_m = 0.0

    splash = splash_score(mesh, impact)
    curv_grad = curvature_gradient_mean(mesh, impact)

    water_proxy = WaterProxyMetrics(
        impact_angle_mean_deg=impact_angle_mean_deg,
        impact_angle_p95_deg=impact_angle_p95_deg,
        normal_impact_score=normal_impact_score,
        attachment_length_m=attachment_length_m,
        attachment_ratio=attachment_ratio,
        edge_escape_rate=edge_escape_rate,
        edge_escape_risk=edge_escape_rate,
        curvature_gradient_mean=curv_grad,
        drain_target_error_m=drain_target_error_m,
        splash_proxy=splash,
    )
    geom_proxy = compute_geometry_proxy(mesh)

    return FastMetricsV1(
        algorithm_version=ALGORITHM_VERSION,
        candidate_id=params.candidate_id,
        water_proxy=water_proxy,
        geometry_proxy=geom_proxy,
    )
