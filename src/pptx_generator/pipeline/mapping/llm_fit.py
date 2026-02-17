from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class MappingTextFitRequest:
    slide_id: str
    layout_id: str | None
    max_lines: int | None
    max_chars: int | None
    body: list[str]
    subtitle: str | None = None
    note: str | None = None


@dataclass(slots=True)
class MappingTextFitResponse:
    model: str
    body: list[str]
    subtitle: str | None = None
    note: str | None = None
    raw_text: str | None = None


class MappingTextFitClient(Protocol):
    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        """本文を制約内に収める。"""


class MappingTextFitClientConfigurationError(RuntimeError):
    """LLM 設定に関するエラー。"""


class MappingTextFitClientExecutionError(RuntimeError):
    """LLM 実行時のエラー。"""


class MappingTextFitResponseFormatError(RuntimeError):
    """LLM 応答が期待形式ではない場合のエラー。"""


class MockMappingTextFitClient:
    def __init__(self) -> None:
        self._model = "mock-mapping-text-fit"

    def fit(self, request: MappingTextFitRequest) -> MappingTextFitResponse:
        body = _fit_mock_body(request.body, request.max_lines, request.max_chars)
        return MappingTextFitResponse(
            model=self._model,
            body=body,
            subtitle=request.subtitle,
            note=request.note,
            raw_text=None,
        )


def create_mapping_text_fit_client() -> MappingTextFitClient:
    return MockMappingTextFitClient()


def _fit_mock_body(body: list[str], max_lines: int | None, max_chars: int | None) -> list[str]:
    lines = list(body)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
    if max_chars is not None:
        trimmed: list[str] = []
        for line in lines:
            if len(line) > max_chars:
                trimmed.append(line[:max_chars])
            else:
                trimmed.append(line)
        lines = trimmed
    return lines
