from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from pptx_generator.pipeline.pdf_exporter import LibreOfficeConverter, PdfExportError


def test_resolve_soffice_env_warns(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.delenv("LIBREOFFICE_PATH", raising=False)
    converter = LibreOfficeConverter(soffice_path=None, timeout_sec=1, max_retries=1)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        with pytest.raises(PdfExportError):
            converter._resolve_soffice()
    assert any("LibreOffice (soffice) が見つかりません" in msg for msg in caplog.messages)
