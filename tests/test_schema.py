from __future__ import annotations

import pytest
from pydantic import ValidationError

from leaflab.schema.params_schema import ParamsV1, load_params
from leaflab.schema.version import CURRENT_PARAMS_VERSION, SchemaVersion


def test_template_params_validates(sample_params_dict: dict) -> None:
    params = load_params(sample_params_dict)
    assert isinstance(params, ParamsV1)
    assert params.candidate_id == "cand_test"
    assert params.schema_version == CURRENT_PARAMS_VERSION.value


def test_missing_schema_version_rejected(sample_params_dict: dict) -> None:
    del sample_params_dict["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        load_params(sample_params_dict)


def test_unknown_schema_version_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["schema_version"] = "99.0"
    with pytest.raises(ValueError, match="unknown params schema_version"):
        load_params(sample_params_dict)


def test_negative_height_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["height_total_m"] = -1.0
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_height_exceeds_15m_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["geometry"]["height_total_m"] = 20.0
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_extra_field_rejected(sample_params_dict: dict) -> None:
    sample_params_dict["nonsense_field"] = 123
    with pytest.raises(ValidationError):
        load_params(sample_params_dict)


def test_schema_version_enum_has_v1() -> None:
    assert SchemaVersion.V1_0.value == "1.0"
