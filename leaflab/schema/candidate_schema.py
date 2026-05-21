"""Candidate aggregator — loads params + all available metrics from a run directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from leaflab.schema.metrics_schema import (
    CFDMetricsV1,
    FastMetricsV1,
    KarambaMetricsV1,
    ScoreV1,
    VisualMetricsV1,
    load_metrics,
)
from leaflab.schema.params_schema import ParamsV1, load_params


class Candidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidate_id: str
    run_dir: Path
    params: ParamsV1
    fast_metrics: FastMetricsV1 | None = None
    karamba_metrics: KarambaMetricsV1 | None = None
    cfd_metrics: CFDMetricsV1 | None = None
    visual_metrics: VisualMetricsV1 | None = None
    score: ScoreV1 | None = None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def load_candidate(run_dir: Path) -> Candidate:
    """Load candidate from `runs/<id>/`.

    Required: `params.json`. Optional: fast/karamba/cfd/visual_metrics.json,
    score.json.
    """
    run_dir = Path(run_dir)
    params_path = run_dir / "params.json"
    if not params_path.exists():
        raise FileNotFoundError(f"missing params.json: {params_path}")
    params = load_params(_read_json(params_path))

    def _try_load_path(filename: str, kind: str) -> Any:
        path = run_dir / filename
        if not path.exists():
            return None
        return load_metrics(kind, _read_json(path))

    return Candidate(
        candidate_id=params.candidate_id,
        run_dir=run_dir,
        params=params,
        fast_metrics=_try_load_path("fast_metrics.json", "fast"),
        karamba_metrics=_try_load_path("karamba_metrics.json", "karamba"),
        cfd_metrics=_try_load_path("cfd_metrics.json", "cfd"),
        visual_metrics=_try_load_path("visual_metrics.json", "visual"),
        score=_try_load_path("score.json", "score"),
    )
