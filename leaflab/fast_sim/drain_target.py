"""Pond capture + drain-target error for sliding endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, eq=False)
class DrainResult:
    captured: NDArray[np.bool_]
    distance_to_target_m: NDArray[np.float64]


def evaluate_drain(
    endpoints: NDArray[np.float64],
    target_xyz: tuple[float, float, float],
    pond_radius_m: float,
) -> DrainResult:
    """Distance from endpoint to drain target (XY-plane); inside pond_radius → captured."""
    if pond_radius_m <= 0:
        raise ValueError(f"pond_radius_m must be > 0, got {pond_radius_m}")
    dxy = endpoints[:, :2] - np.array([target_xyz[0], target_xyz[1]], dtype=np.float64)
    d = np.linalg.norm(dxy, axis=1)
    captured = d <= pond_radius_m
    return DrainResult(captured=captured, distance_to_target_m=d)
