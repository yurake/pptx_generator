"""PDF 変換ステップ。"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .base import PipelineContext


class PdfExportError(RuntimeError):
    """PDF 変換失敗時に送出される例外。"""


@dataclass(slots=True)
class PdfExportOptions:
    """PDF 変換に関する設定。"""

    enabled: bool = False
    mode: str = "both"  # `both` or `only`
    output_filename: str = "proposal.pdf"
    soffice_path: Path | None = None
    timeout_sec: int = 120
    max_retries: int = 2


class PdfExportStep:
    """LibreOffice を利用して PPTX を PDF 化するステップ。"""

    name = "pdf_export"

    def __init__(self, options: PdfExportOptions | None = None) -> None:
        self.options = options or PdfExportOptions()

    def run(self, context: PipelineContext) -> None:
        if not self.options.enabled:
            return

        pptx_object = context.require_artifact("pptx_path")
        pptx_path = Path(pptx_object)
        if not pptx_path.exists():  # pragma: no cover - 異常系
            msg = f"PPTX ファイルが存在しません: {pptx_path}"
            raise PdfExportError(msg)

        output_dir = pptx_path.parent

        if os.environ.get("PPTXGEN_SKIP_PDF_CONVERT"):
            target_path = output_dir / self.options.output_filename
            target_path.write_bytes(b"")
            context.add_artifact("pdf_path", target_path)
            context.add_artifact(
                "pdf_export_metadata",
                {
                    "status": "skipped",
                    "attempts": 0,
                    "elapsed_sec": 0.0,
                    "converter": "skipped",
                },
            )
            if self.options.mode == "only":
                pptx_path.unlink(missing_ok=True)
                context.artifacts.pop("pptx_path", None)
            return

        converter = LibreOfficeConverter(
            soffice_path=self.options.soffice_path,
            timeout_sec=self.options.timeout_sec,
            max_retries=self.options.max_retries,
        )
        result = converter.convert(pptx_path, output_dir)
        pdf_path = result.path

        target_path = output_dir / self.options.output_filename
        if pdf_path != target_path:
            if target_path.exists():
                target_path.unlink()
            pdf_path.rename(target_path)
            pdf_path = target_path

        context.add_artifact("pdf_path", pdf_path)
        context.add_artifact(
            "pdf_export_metadata",
            {
                "status": "success",
                "attempts": result.attempts,
                "elapsed_sec": result.elapsed_sec,
                "converter": "libreoffice",
            },
        )

        if self.options.mode == "only":
            pptx_path.unlink(missing_ok=True)
            context.artifacts.pop("pptx_path", None)


@dataclass(slots=True)
class PdfExportResult:
    path: Path
    attempts: int
    elapsed_sec: float


class LibreOfficeConverter:
    """LibreOffice (soffice) を用いた PDF 変換実装。"""

    def __init__(
        self,
        *,
        soffice_path: Path | None,
        timeout_sec: int,
        max_retries: int,
    ) -> None:
        self._soffice_path = soffice_path
        self._timeout_sec = timeout_sec
        self._max_retries = max(1, max_retries)

    def convert(self, pptx_path: Path, output_dir: Path) -> PdfExportResult:
        soffice = self._resolve_soffice()
        command = [
            str(soffice),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ]
        start = time.perf_counter()
        attempt = 0
        while attempt < self._max_retries:
            attempt += 1
            try:
                subprocess.run(  # noqa: S603, S607
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self._timeout_sec,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                if attempt >= self._max_retries:
                    raise PdfExportError(f"LibreOffice 変換に失敗しました: {exc}") from exc
                time.sleep(1)
                continue

            produced = output_dir / f"{pptx_path.stem}.pdf"
            if produced.exists():
                return PdfExportResult(
                    path=produced,
                    attempts=attempt,
                    elapsed_sec=time.perf_counter() - start,
                )

            if attempt >= self._max_retries:
                msg = f"LibreOffice 変換後に PDF が見つかりません: {produced}"
                raise PdfExportError(msg)
            time.sleep(1)

        msg = "LibreOffice 変換に失敗しました"
        raise PdfExportError(msg)

    def _resolve_soffice(self) -> Path:
        if self._soffice_path:
            candidate = Path(self._soffice_path)
            if candidate.exists():
                return candidate
            msg = f"指定された LibreOffice パスが見つかりません: {candidate}"
            raise PdfExportError(msg)

        env_path = os.environ.get("LIBREOFFICE_PATH")
        if env_path:
            candidate = Path(env_path)
            if candidate.exists():
                return candidate

        resolved = shutil.which("soffice")
        if resolved:
            return Path(resolved)

        msg = "LibreOffice (soffice) が見つかりません。PATH または LIBREOFFICE_PATH を確認してください"
        raise PdfExportError(msg)
