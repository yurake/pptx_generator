"""レイアウト検証成果物のバリデーション。"""

from __future__ import annotations

from typing import Any

from ..schema import (
    DIAGNOSTICS_VALIDATOR,
    DIFF_REPORT_VALIDATOR,
    LAYOUT_RECORD_VALIDATOR,
)
from .types import LayoutValidationError


def validate_records(records: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for index, record in enumerate(records):
        for err in LAYOUT_RECORD_VALIDATOR.iter_errors(record):
            path = ".".join(str(part) for part in err.path)
            errors.append(f"record[{index}].{path}: {err.message}")
    if errors:
        raise LayoutValidationError("layouts.jsonl のスキーマ検証に失敗しました\n" + "\n".join(errors))


def validate_diagnostics(diagnostics: dict[str, Any]) -> None:
    errors = [err.message for err in DIAGNOSTICS_VALIDATOR.iter_errors(diagnostics)]
    if errors:
        raise LayoutValidationError(
            "diagnostics.json のスキーマ検証に失敗しました\n" + "\n".join(errors)
        )


def validate_diff_report(diff_report: dict[str, Any]) -> None:
    errors = [err.message for err in DIFF_REPORT_VALIDATOR.iter_errors(diff_report)]
    if errors:
        raise LayoutValidationError(
            "diff_report.json のスキーマ検証に失敗しました\n" + "\n".join(errors)
        )
