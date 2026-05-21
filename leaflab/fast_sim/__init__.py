"""Fast water proxy — particle-based heuristic evaluation pipeline.

See `docs/plans/2026-05-21-phase-c-kickoff.md`. Each module is independently
testable; `run.run_fast_sim` orchestrates the full pipeline.
"""

from __future__ import annotations

from leaflab.fast_sim.particle_drop import (
    DEFAULT_PARTICLE_COUNT,
    ParticleField,
    particle_field_from_params,
    sample_water_curtain,
)
from leaflab.fast_sim.run import ALGORITHM_VERSION, run_fast_sim

__all__ = [
    "ALGORITHM_VERSION",
    "DEFAULT_PARTICLE_COUNT",
    "ParticleField",
    "particle_field_from_params",
    "run_fast_sim",
    "sample_water_curtain",
]
