"""GH-side bridge: read all available metrics for a run, return as a dict.

Runs inside Rhino 8 embedded CPython 3.9. MUST NOT import `leaflab`.
Only uses stdlib (json, os) for maximum portability inside GH.

Usage from a GH Python 3 Script component:

    import sys, pathlib
    repo = pathlib.Path(r"C:\\Users\\user\\Documents\\LFTH_CFD")
    sys.path.insert(0, str(repo))
    from gh.scripts.import_results import import_results

    results = import_results(repo / "runs" / candidate_id)
    # results is a dict like {"score": {...}, "fast_metrics": {...}, "geometry_check": None}
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Union

PathLike = Union[str, "os.PathLike[str]"]

# Map output key -> filename in the run directory
_FILES = {
    "params": "params.json",
    "geometry_check": "geometry_metrics.json",
    "fast_metrics": "fast_metrics.json",
    "karamba_metrics": "karamba_metrics.json",
    "cfd_metrics": "cfd_metrics.json",
    "visual_metrics": "visual_metrics.json",
    "score": "score.json",
}


def _read_json_if_exists(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        data: Dict[str, Any] = json.load(fh)
    return data


def import_results(run_dir: PathLike) -> Dict[str, Optional[Dict[str, Any]]]:
    """Read all known metrics files from ``run_dir``.

    Returns a dict keyed by metric type. Each value is the parsed JSON dict
    or ``None`` if the file does not exist.
    """
    run_dir_s = os.fspath(run_dir)
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    for key, filename in _FILES.items():
        out[key] = _read_json_if_exists(os.path.join(run_dir_s, filename))
    return out


def get_score_or_none(run_dir: PathLike) -> Optional[Dict[str, Any]]:
    """Quick accessor for just the score JSON."""
    return _read_json_if_exists(os.path.join(os.fspath(run_dir), "score.json"))
