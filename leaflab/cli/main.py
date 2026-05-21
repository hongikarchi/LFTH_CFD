"""leaflab CLI entry point."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import typer

from leaflab.cli import check_geometry, init_run, migrate, validate

app = typer.Typer(
    no_args_is_help=True,
    help="leaflab - Big Leaf water sculpture parametric design + evaluation",
)

app.command("init-run", help="Initialize a new candidate run directory")(init_run.run)
app.command("validate", help="Validate a params.json or metrics.json file")(validate.run)
app.command("check-geometry", help="Validate STL mesh in a run directory")(check_geometry.run)
app.command("migrate", help="Migrate params.json files to the current schema version")(migrate.run)


if __name__ == "__main__":
    app()
