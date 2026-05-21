"""Particle sampling on the water-curtain annulus + free-fall init velocity.

Kinematic shortcut: particles are placed at the release plane
(`top_leaf_z_m + fall_height_m`) but velocity already equals the impact
magnitude `sqrt(2 g h)`. The downstream raycast (PR-C2) shoots straight
down from each particle to find the contact point, so the intermediate
fall trajectory is intentionally skipped. Air drag ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from leaflab.schema.params_schema import ParamsV1

DEFAULT_PARTICLE_COUNT = 500


@dataclass(frozen=True, eq=False)
class ParticleField:
    positions: NDArray[np.float64]
    velocities: NDArray[np.float64]
    seed: int


def sample_water_curtain(
    inner_radius_m: float,
    outer_radius_m: float,
    release_z_m: float,
    fall_height_m: float,
    *,
    n: int = DEFAULT_PARTICLE_COUNT,
    gravity_mps2: float = 9.81,
    seed: int = 42,
) -> ParticleField:
    """Uniform-area annulus sample + downward free-fall velocity vector."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if inner_radius_m < 0:
        raise ValueError(f"inner_radius_m must be >= 0, got {inner_radius_m}")
    if outer_radius_m <= inner_radius_m:
        raise ValueError(
            f"outer_radius_m ({outer_radius_m}) must be > inner_radius_m ({inner_radius_m})"
        )
    if fall_height_m <= 0:
        raise ValueError(f"fall_height_m must be > 0, got {fall_height_m}")
    if gravity_mps2 <= 0:
        raise ValueError(f"gravity_mps2 must be > 0, got {gravity_mps2}")

    rng = np.random.default_rng(seed)
    u = rng.random(n)
    radii = np.sqrt(inner_radius_m**2 + u * (outer_radius_m**2 - inner_radius_m**2))
    theta = rng.uniform(0.0, 2.0 * math.pi, size=n)

    positions = np.empty((n, 3), dtype=np.float64)
    positions[:, 0] = radii * np.cos(theta)
    positions[:, 1] = radii * np.sin(theta)
    positions[:, 2] = release_z_m

    v_mag = math.sqrt(2.0 * gravity_mps2 * fall_height_m)
    velocities = np.zeros((n, 3), dtype=np.float64)
    velocities[:, 2] = -v_mag

    return ParticleField(positions=positions, velocities=velocities, seed=seed)


def particle_field_from_params(
    params: ParamsV1,
    *,
    n: int = DEFAULT_PARTICLE_COUNT,
    seed: int = 42,
) -> ParticleField:
    """Extract curtain spec from ParamsV1 and sample particles."""
    return sample_water_curtain(
        inner_radius_m=params.water.curtain_radius_inner_m,
        outer_radius_m=params.water.curtain_radius_outer_m,
        release_z_m=params.geometry.top_leaf_z_m + params.water.fall_height_m,
        fall_height_m=params.water.fall_height_m,
        n=n,
        gravity_mps2=params.water.gravity_mps2,
        seed=seed,
    )
