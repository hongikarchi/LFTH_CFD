"""GH-side bridge: write params.json + leaf.stl into a run directory.

This module runs inside Rhino 8's embedded CPython 3.9 (Grasshopper
`Python 3 Script` component). It MUST NOT import from `leaflab`.

Communication is purely via files (JSON + STL); the `leaflab` Python CLI
later validates and consumes them.

Required deps:
- stdlib (json, os)
- trimesh (install in GH via magic comment: `# r: trimesh`)
- numpy (transitively from trimesh)

Usage from a GH Python 3 Script component:

    # r: trimesh
    import sys, pathlib
    repo = pathlib.Path(r"C:\\Users\\user\\Documents\\LFTH_CFD")
    sys.path.insert(0, str(repo))
    from gh.scripts.export_candidate import export_candidate

    # `mesh` is the GH input. Convert RhinoCommon Mesh to vertices/faces lists:
    verts = [(v.X, v.Y, v.Z) for v in mesh.Vertices]
    faces = [(f.A, f.B, f.C) for f in mesh.Faces]  # tri faces; quads need split

    out_dir = repo / "runs" / candidate_id
    export_candidate(verts, faces, params_dict, out_dir)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping, Sequence, Tuple, Union

import trimesh  # type: ignore[import-untyped]

VertexLike = Tuple[float, float, float]
FaceLike = Tuple[int, int, int]
PathLike = Union[str, "os.PathLike[str]"]


def export_candidate(
    vertices: Sequence[VertexLike],
    faces: Sequence[FaceLike],
    params_dict: Mapping[str, Any],
    out_dir: PathLike,
) -> Dict[str, Any]:
    """Write `params.json` + `geometry/leaf.stl` into ``out_dir``.

    Returns a small dict summarising the write (paths + counts) so GH can
    surface it.
    """
    out_dir_s = os.fspath(out_dir)
    os.makedirs(os.path.join(out_dir_s, "geometry"), exist_ok=True)

    params_path = os.path.join(out_dir_s, "params.json")
    with open(params_path, "w", encoding="utf-8") as fh:
        json.dump(dict(params_dict), fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    mesh = trimesh.Trimesh(
        vertices=list(vertices),
        faces=list(faces),
        process=False,
    )
    stl_path = os.path.join(out_dir_s, "geometry", "leaf.stl")
    mesh.export(stl_path, file_type="stl")

    return {
        "params_path": params_path,
        "stl_path": stl_path,
        "vertex_count": int(mesh.vertices.shape[0]),
        "triangle_count": int(mesh.faces.shape[0]),
    }
