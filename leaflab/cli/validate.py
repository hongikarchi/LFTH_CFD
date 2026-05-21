"""`leaflab validate <path>` — validate a params.json or metrics.json file."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from leaflab.schema.metrics_schema import load_metrics
from leaflab.schema.params_schema import load_params

METRICS_KIND_BY_FILENAME = {
    "fast_metrics.json": "fast",
    "karamba_metrics.json": "karamba",
    "cfd_metrics.json": "cfd",
    "visual_metrics.json": "visual",
    "score.json": "score",
}


def run(
    path: Path = typer.Argument(..., help="path to params.json or *_metrics.json"),
) -> None:
    """Validate a JSON file against its schema."""
    if not path.exists():
        typer.echo(f"error: file not found: {path}", err=True)
        raise typer.Exit(code=1)

    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        typer.echo(f"error: invalid JSON: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    filename = path.name
    try:
        if filename == "params.json":
            params = load_params(data)
            typer.echo(
                f"ok: params.json (schema_version={params.schema_version}, "
                f"candidate_id={params.candidate_id})"
            )
        elif filename in METRICS_KIND_BY_FILENAME:
            kind = METRICS_KIND_BY_FILENAME[filename]
            metrics = load_metrics(kind, data)
            typer.echo(f"ok: {filename} (kind={kind}, schema_version={metrics.schema_version})")  # type: ignore[attr-defined]
        else:
            typer.echo(
                f"error: unsupported filename {filename!r}. "
                f"Expected params.json or one of {sorted(METRICS_KIND_BY_FILENAME)}",
                err=True,
            )
            raise typer.Exit(code=1)
    except ValidationError as exc:
        typer.echo(f"error: schema validation failed:\n{exc}", err=True)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
