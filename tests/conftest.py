from __future__ import annotations

import json
from pathlib import Path

import pytest

from leaflab.cli.init_run import _template_params

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_params_dict() -> dict:
    return _template_params("cand_test")


@pytest.fixture
def sample_params_file(tmp_path: Path, sample_params_dict: dict) -> Path:
    p = tmp_path / "params.json"
    with p.open("w", encoding="utf-8") as fh:
        json.dump(sample_params_dict, fh, indent=2)
    return p


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
