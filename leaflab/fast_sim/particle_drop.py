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

from leaflab.schema.params_schema import NozzleParams, ParamsV1

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


def particle_field_from_nozzles(
    nozzles: list[NozzleParams],
    fall_height_m: float,
    *,
    n_per_nozzle: int = 50,
    gravity_mps2: float = 9.81,
    seed: int = 42,
    jitter_m: float = 0.01,
) -> ParticleField:
    """Sample particles from a small disc around each nozzle position.

    Each nozzle gets `n_per_nozzle` particles uniformly distributed on
    a disc of radius `jitter_m` centred at `nozzle.position`. Velocity
    is taken from `nozzle.velocity_mps` if set, else downward free-fall
    `(0, 0, -sqrt(2 g h))`.
    """
    if len(nozzles) < 1:
        raise ValueError(f"len(nozzles) must be >= 1, got {len(nozzles)}")
    if n_per_nozzle < 1:
        raise ValueError(f"n_per_nozzle must be >= 1, got {n_per_nozzle}")
    if jitter_m < 0:
        raise ValueError(f"jitter_m must be >= 0, got {jitter_m}")
    if fall_height_m <= 0:
        raise ValueError(f"fall_height_m must be > 0, got {fall_height_m}")
    if gravity_mps2 <= 0:
        raise ValueError(f"gravity_mps2 must be > 0, got {gravity_mps2}")

    rng = np.random.default_rng(seed)
    total = len(nozzles) * n_per_nozzle
    positions: NDArray[np.float64] = np.empty((total, 3), dtype=np.float64)
    velocities: NDArray[np.float64] = np.empty((total, 3), dtype=np.float64)

    v_default = -math.sqrt(2.0 * gravity_mps2 * fall_height_m)

    for i, nozzle in enumerate(nozzles):
        u = rng.random(n_per_nozzle)
        radii = jitter_m * np.sqrt(u)
        theta = rng.uniform(0.0, 2.0 * math.pi, size=n_per_nozzle)

        start = i * n_per_nozzle
        stop = start + n_per_nozzle
        positions[start:stop, 0] = nozzle.position[0] + radii * np.cos(theta)
        positions[start:stop, 1] = nozzle.position[1] + radii * np.sin(theta)
        positions[start:stop, 2] = nozzle.position[2]

        if nozzle.velocity_mps is None:
            velocities[start:stop, 0] = 0.0
            velocities[start:stop, 1] = 0.0
            velocities[start:stop, 2] = v_default
        else:
            velocities[start:stop, 0] = nozzle.velocity_mps[0]
            velocities[start:stop, 1] = nozzle.velocity_mps[1]
            velocities[start:stop, 2] = nozzle.velocity_mps[2]

    return ParticleField(positions=positions, velocities=velocities, seed=seed)


def particle_field_from_params(
    params: ParamsV1,
    *,
    n: int = DEFAULT_PARTICLE_COUNT,
    seed: int = 42,
) -> ParticleField:
    """Extract curtain spec from ParamsV1 and sample particles.

    Dispatches: if `params.water.nozzles` is a non-empty list, samples
    per-nozzle (n distributed across nozzles); otherwise falls back to
    the annulus sampling of `sample_water_curtain`.
    """
    nozzles = params.water.nozzles
    if nozzles is not None and len(nozzles) > 0:
        n_per = max(1, n // len(nozzles))
        return particle_field_from_nozzles(
            nozzles=nozzles,
            fall_height_m=params.water.fall_height_m,
            n_per_nozzle=n_per,
            gravity_mps2=params.water.gravity_mps2,
            seed=seed,
        )
    return sample_water_curtain(
        inner_radius_m=params.water.curtain_radius_inner_m,
        outer_radius_m=params.water.curtain_radius_outer_m,
        release_z_m=params.geometry.top_leaf_z_m + params.water.fall_height_m,
        fall_height_m=params.water.fall_height_m,
        n=n,
        gravity_mps2=params.water.gravity_mps2,
        seed=seed,
    )
