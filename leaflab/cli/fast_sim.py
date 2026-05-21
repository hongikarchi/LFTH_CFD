"""`leaflab fast-sim <run_dir>` — particle-based water proxy evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import trimesh
import typer

from leaflab.fast_sim.run import run_fast_sim
from leaflab.schema.params_schema import load_params


def run(
    run_dir: Path = typer.Argument(..., help="run directory (runs/<candidate_id>)"),
    n_particles: int = typer.Option(500, "-n", "--n-particles", help="particle count"),
    seed: int = typer.Option(42, "--seed"),
    n_slide_steps: int = typer.Option(200, "--slide-steps"),
    dt_s: float = typer.Option(0.01, "--dt"),
    out: Path | None = typer.Option(
        None, "-o", "--out", help="output path (default: <run_dir>/fast_metrics.json)"
    ),
) -> None:
    """Read params.json + leaf.stl from run_dir, write fast_metrics.json."""
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
        params = load_params(json.load(fh))

    mesh = trimesh.load_mesh(stl_path)
    if not isinstance(mesh, trimesh.Trimesh):
        typer.echo(f"error: {stl_path} did not load as a single Trimesh", err=True)
        raise typer.Exit(code=1)

    metrics = run_fast_sim(
        mesh,
        params,
        n_particles=n_particles,
        seed=seed,
        n_slide_steps=n_slide_steps,
        dt_s=dt_s,
    )

    out_path = out if out is not None else run_dir / "fast_metrics.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(metrics.model_dump(), fh, indent=2)
        fh.write("\n")

    wp = metrics.water_proxy
    typer.echo(f"ok: {params.candidate_id}")
    typer.echo(f"  impact_angle_mean_deg: {wp.impact_angle_mean_deg:.2f}")
    typer.echo(f"  normal_impact_score:   {wp.normal_impact_score:.3f}")
    typer.echo(f"  attachment_length_m:   {wp.attachment_length_m:.2f}")
    typer.echo(f"  edge_escape_rate:      {wp.edge_escape_rate:.3f}")
    typer.echo(f"  drain_target_error_m:  {wp.drain_target_error_m:.2f}")
    typer.echo(f"  splash_proxy:          {wp.splash_proxy:.4f}")
    if wp.normal_impact_score < 0.25:
        typer.echo("  filter: normal_impact_score < 0.25 → would be rejected")
    typer.echo(f"wrote: {out_path}")
