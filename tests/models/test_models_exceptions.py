from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from pptx_generator.models import PipelineFallbackError, SpecValidationError


def test_spec_validation_error_stores_errors() -> None:
    err = SpecValidationError("failed", errors=[{"loc": ("foo",), "msg": "error"}])
    assert err.errors == [{"loc": ("foo",), "msg": "error"}]


def test_spec_validation_error_from_validation_error() -> None:
    class Demo(BaseModel):
        value: int

    with pytest.raises(SpecValidationError) as exc_info:
        try:
            Demo(value="oops")  # type: ignore[arg-type]
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc

    assert exc_info.value.errors


def test_pipeline_fallback_error_init_sets_message() -> None:
    error = PipelineFallbackError("fallback forbidden")
    assert "fallback" in str(error)
