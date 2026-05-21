"""STL mesh validation via trimesh — scale, height, manifold, normals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from leaflab.schema.metrics_schema import GeometryCheckV1
from leaflab.schema.version import CURRENT_METRICS_VERSION

# Heuristic: if bbox max dimension exceeds this, suspect millimeter units (or worse)
SCALE_WARNING_THRESHOLD_M = 100.0


class MeshValidationError(ValueError):
    """Raised when mesh validation fails fatally (height exceeded, non-manifold under --strict)."""


def _normal_consistency(mesh: trimesh.Trimesh) -> float:
    """Fraction of face normals pointing 'outward' (consistent winding).

    trimesh exposes `mesh.is_winding_consistent` as a bool; we also compute a soft
    score from the agreement between face normals and the centroid-relative direction.
    Result in [0, 1]; 1.0 means fully consistent.
    """
    if mesh.faces.shape[0] == 0:
        return 0.0
    centroid = mesh.centroid
    face_centers = mesh.triangles_center
    outward = face_centers - centroid
    outward_norm = np.linalg.norm(outward, axis=1, keepdims=True)
    outward_norm[outward_norm == 0] = 1.0
    outward_unit = outward / outward_norm
    agreement = np.einsum("ij,ij->i", mesh.face_normals, outward_unit)
    fraction_positive = float(np.mean(agreement > 0))
    return fraction_positive


def validate_mesh(
    stl_path: Path,
    candidate_id: str,
    max_height_m: float,
    strict: bool = False,
) -> GeometryCheckV1:
    """Validate a leaf STL and return a `GeometryCheckV1` metrics object.

    Raises `MeshValidationError` on fatal issues:
    - file missing
    - height > max_height_m
    - non-manifold AND `strict=True`
    """
    stl_path = Path(stl_path)
    if not stl_path.exists():
        raise MeshValidationError(f"STL not found: {stl_path}")

    loaded = trimesh.load(stl_path, force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise MeshValidationError(
            f"STL did not load as a single mesh: {stl_path} (got {type(loaded).__name__})"
        )
    mesh: trimesh.Trimesh = loaded

    b_min = mesh.bounds[0]
    b_max = mesh.bounds[1]
    bbox_min: tuple[float, float, float] = (float(b_min[0]), float(b_min[1]), float(b_min[2]))
    bbox_max: tuple[float, float, float] = (float(b_max[0]), float(b_max[1]), float(b_max[2]))
    extents = mesh.extents  # (dx, dy, dz)
    height_m = float(extents[2])
    radius_m = float(np.hypot(extents[0], extents[1]) / 2.0)

    surface_area = float(mesh.area)
    volume = float(mesh.volume) if mesh.is_watertight else float(mesh.volume)
    triangle_count = int(mesh.faces.shape[0])
    vertex_count = int(mesh.vertices.shape[0])

    is_watertight = bool(mesh.is_watertight)
    is_manifold = bool(mesh.is_watertight and mesh.is_winding_consistent)
    normal_consistency = _normal_consistency(mesh)
    scale_warning = float(extents.max()) > SCALE_WARNING_THRESHOLD_M

    warnings: list[str] = []
    if scale_warning:
        warnings.append(
            f"bbox max dimension {extents.max():.1f} > {SCALE_WARNING_THRESHOLD_M} - "
            "suspect non-meter units (e.g. millimeters)"
        )
    if not is_watertight:
        warnings.append("mesh is not watertight (holes or open boundaries)")
    if not is_manifold:
        warnings.append("mesh is not manifold (non-watertight or inconsistent winding)")
    if normal_consistency < 0.9:
        warnings.append(
            f"normal_consistency {normal_consistency:.2f} < 0.9 - many face normals point inward"
        )

    if height_m > max_height_m:
        raise MeshValidationError(f"mesh height {height_m:.2f}m > max_height {max_height_m:.2f}m")
    if strict and not is_manifold:
        raise MeshValidationError("mesh is not manifold (strict mode)")

    return GeometryCheckV1(
        schema_version=CURRENT_METRICS_VERSION.value,
        candidate_id=candidate_id,
        stl_path=str(stl_path),
        height_m=height_m,
        radius_m=radius_m,
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        surface_area_m2=surface_area,
        volume_estimate_m3=volume,
        triangle_count=triangle_count,
        vertex_count=vertex_count,
        is_watertight=is_watertight,
        is_manifold=is_manifold,
        normal_consistency=normal_consistency,
        scale_warning=scale_warning,
        warnings=warnings,
    )
