"""`leaflab check-geometry <run_dir>` — validate the exported STL against params."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from leaflab.geometry import MeshValidationError, validate_mesh
from leaflab.schema.params_schema import load_params


def run(
    run_dir: Path = typer.Argument(..., help="run directory (runs/<candidate_id>)"),
    strict: bool = typer.Option(False, "--strict", help="treat non-manifold mesh as fatal error"),
) -> None:
    """Validate runs/<id>/geometry/leaf.stl against runs/<id>/params.json constraints."""
    run_dir = Path(run_dir)
    params_path = run_dir / "params.json"
    stl_path = run_dir / "geometry" / "leaf.stl"

    if not params_path.exists():
        typer.echo(f"error: missing params.json: {params_path}", err=True)
        raise typer.Exit(code=1)
    if not stl_path.exists():
        typer.echo(f"error: missing STL: {stl_path}", err=True)
        raise typer.Exit(code=1)

    with params_path.open(encoding="utf-8") as fh:
        params_data = json.load(fh)
    try:
        params = load_params(params_data)
    except (ValueError, Exception) as exc:
        typer.echo(f"error: params.json invalid: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        check = validate_mesh(
            stl_path=stl_path,
            candidate_id=params.candidate_id,
            max_height_m=params.global_constraints.max_height_m,
            strict=strict,
        )
    except MeshValidationError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    out_path = run_dir / "geometry_metrics.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(check.model_dump(), fh, indent=2)
        fh.write("\n")

    typer.echo(f"ok: {stl_path.name}")
    typer.echo(f"  height: {check.height_m:.3f} m")
    typer.echo(f"  radius: {check.radius_m:.3f} m")
    typer.echo(f"  triangles: {check.triangle_count}")
    typer.echo(f"  watertight: {check.is_watertight}")
    typer.echo(f"  manifold: {check.is_manifold}")
    typer.echo(f"  normal_consistency: {check.normal_consistency:.3f}")
    for w in check.warnings:
        typer.echo(f"  warning: {w}")
    typer.echo(f"wrote: {out_path}")
