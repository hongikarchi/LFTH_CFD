"""`leaflab migrate <path>` — migrate params.json files to the current schema version.

Currently only schema V1.0 exists, so any migration is a no-op. The dispatch
framework is in place so adding V1.1 means registering a single function in
``PARAMS_MIGRATIONS``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from leaflab.schema.version import CURRENT_PARAMS_VERSION

ParamsDict = dict[str, Any]
MigrationFn = Callable[[ParamsDict], ParamsDict]

# Registry of pairwise migrations: (from_version, to_version) -> transform.
# Add a function here when introducing a new params schema version.
# The transform receives and returns a raw dict (pre-validation).
PARAMS_MIGRATIONS: dict[tuple[str, str], MigrationFn] = {}


def _next_migration_step(current: str) -> tuple[str, MigrationFn] | None:
    for (from_v, to_v), fn in PARAMS_MIGRATIONS.items():
        if from_v == current:
            return to_v, fn
    return None


def _migrate_params_dict(data: ParamsDict, target_version: str) -> ParamsDict:
    """Walk PARAMS_MIGRATIONS step-by-step from data's version to target_version."""
    current = data.get("schema_version")
    if current is None:
        raise ValueError("params.json missing required 'schema_version' field")
    if current == target_version:
        return data

    visited: set[str] = {current}
    while current != target_version:
        step = _next_migration_step(current)
        if step is None:
            raise ValueError(
                f"no migration path from {current!r} to {target_version!r} "
                f"(registered: {list(PARAMS_MIGRATIONS)})"
            )
        next_version, fn = step
        if next_version in visited:
            raise ValueError(f"migration cycle detected at {next_version!r}")
        data = fn(data)
        data["schema_version"] = next_version
        current = next_version
        visited.add(current)
    return data


def _collect_params_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("params.json"))
    return []


def run(
    path: Path = typer.Argument(..., help="params.json file or runs/ directory"),
    target: str = typer.Option(
        CURRENT_PARAMS_VERSION.value,
        "--target",
        help="target schema_version (default: current)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="show plan without writing"),
) -> None:
    """Migrate one or many params.json files to the target schema version."""
    if not path.exists():
        typer.echo(f"error: path not found: {path}", err=True)
        raise typer.Exit(code=1)

    files = _collect_params_files(path)
    if not files:
        typer.echo(f"no params.json found under {path}", err=True)
        raise typer.Exit(code=1)

    migrated = 0
    skipped = 0
    failed = 0
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            typer.echo(f"error: {fp}: invalid JSON: {exc}", err=True)
            failed += 1
            continue

        old_version = data.get("schema_version", "<missing>")
        if old_version == target:
            typer.echo(f"skip: {fp} (already {target})")
            skipped += 1
            continue

        try:
            new_data = _migrate_params_dict(data, target)
        except ValueError as exc:
            typer.echo(f"error: {fp}: {exc}", err=True)
            failed += 1
            continue

        if dry_run:
            typer.echo(f"would migrate: {fp} ({old_version} -> {target})")
        else:
            fp.write_text(
                json.dumps(new_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            typer.echo(f"migrated: {fp} ({old_version} -> {target})")
        migrated += 1

    typer.echo(
        f"{'would migrate' if dry_run else 'migrated'}: {migrated} | "
        f"skipped: {skipped} | failed: {failed} | total: {len(files)}"
    )
    if failed:
        raise typer.Exit(code=1)
