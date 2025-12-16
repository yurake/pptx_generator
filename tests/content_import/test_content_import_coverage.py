import types
from pathlib import Path
from typing import Any

from pptx_generator.content_import.service import (
    ContentImportService,
    _truncate,
)


def test_load_http_source_pdf_uppercase(monkeypatch, tmp_path: Path) -> None:
    service = ContentImportService()
    service._convert_pdf = lambda path: "pdf-text"  # type: ignore[attr-defined]

    class FakeResponse:
        def __init__(self) -> None:
            self.headers = {"Content-Type": "APPLICATION/PDF"}

        def read(self) -> bytes:
            return b"%PDF-1.4"

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            return None

    monkeypatch.setattr(
        "pptx_generator.content_import.service.urlopen",
        lambda request, timeout: FakeResponse(),  # type: ignore[call-arg]
    )

    payload = service._load_http_source("https://example.com/file.pdf")
    assert payload.content_type == "application/pdf"
    assert payload.text == "pdf-text"


def test_truncate_adds_ellipsis() -> None:
    assert _truncate("abcdef", 3) == "ab…"
