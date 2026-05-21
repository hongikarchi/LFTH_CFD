"""Convert dumped Rhino mesh data into trimesh-compatible (verts, faces) lists.

The GH-side ``mesh_loader`` Py3 component extracts vertices and triangle
indices from the Rhino ``Mesh`` objects (since this module avoids any
``Rhino.*`` import to stay testable outside Rhino) and hands them off
here in doc units. We convert to meters and merge multi-mesh dumps into
a single (verts, faces) pair with re-indexed faces.

Strict Python 3.9 compat — no ``leaflab`` import.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

Vertex = Tuple[float, float, float]
TriFace = Tuple[int, int, int]


def rhino_mesh_to_tri_data(
    meshes_dump: List[Dict[str, Any]],
    doc_to_m: float = 1.0,
) -> Tuple[List[Vertex], List[TriFace]]:
    """Merge a list of per-mesh ``{"verts": [...], "faces": [...]}`` dumps.

    Each dump's vertex coordinates are scaled by ``doc_to_m`` (e.g. 0.001
    for mm-doc → meters). Face indices are re-based against the merged
    vertex list so the result can feed straight into ``trimesh.Trimesh``.
    """
    if doc_to_m == 0:
        raise ValueError("doc_to_m must be non-zero, got 0")
    all_verts: List[Vertex] = []
    all_faces: List[TriFace] = []
    for i, dump in enumerate(meshes_dump):
        if not isinstance(dump, dict):
            raise ValueError(
                "meshes_dump[{0}] must be a dict, got {1}".format(i, type(dump).__name__)
            )
        if "verts" not in dump or "faces" not in dump:
            raise ValueError("meshes_dump[{0}] missing 'verts' or 'faces' key".format(i))
        base_idx = len(all_verts)
        for v in dump["verts"]:
            all_verts.append(
                (
                    float(v[0]) * doc_to_m,
                    float(v[1]) * doc_to_m,
                    float(v[2]) * doc_to_m,
                )
            )
        for f in dump["faces"]:
            all_faces.append(
                (
                    int(f[0]) + base_idx,
                    int(f[1]) + base_idx,
                    int(f[2]) + base_idx,
                )
            )
    return all_verts, all_faces


def mesh_summary(verts: List[Vertex], faces: List[TriFace]) -> Dict[str, Any]:
    """Return aggregate stats — vertex / face count + bounding box in meters."""
    if not verts:
        return {
            "vert_count": 0,
            "face_count": 0,
            "bbox_m": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        }
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return {
        "vert_count": len(verts),
        "face_count": len(faces),
        "bbox_m": [
            [min(xs), min(ys), min(zs)],
            [max(xs), max(ys), max(zs)],
        ],
    }
