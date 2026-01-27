"""PPTX スライド画像の生成ユーティリティ。"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory


logger = logging.getLogger(__name__)

_IMAGE_MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


class SlideImageExportError(RuntimeError):
    """スライド画像生成に失敗した場合のエラー。"""


@dataclass(slots=True)
class SlideImageExportOptions:
    """スライド画像生成の設定。"""

    enabled: bool = True
    formats: tuple[str, ...] = ("png", "jpg")
    prefer_first_success: bool = True
    soffice_path: Path | None = None
    timeout_sec: int = 120
    max_retries: int = 2


@dataclass(slots=True)
class SlideImageAsset:
    slide_index: int
    format: str
    path: Path
    media_type: str


@dataclass(slots=True)
class SlideImageExportResult:
    images_by_slide: dict[int, list[SlideImageAsset]] = field(default_factory=dict)
    status: str = "skipped"
    errors: list[str] = field(default_factory=list)


class SlideImageExporter:
    """LibreOffice (soffice) を使って PPTX をスライド画像へ変換する。"""

    def __init__(self, options: SlideImageExportOptions | None = None) -> None:
        self.options = options or SlideImageExportOptions()

    def export(self, pptx_path: Path, output_dir: Path) -> SlideImageExportResult:
        if not self.options.enabled:
            return SlideImageExportResult(status="disabled")
        if not pptx_path.exists():
            return SlideImageExportResult(status="missing", errors=[f"pptx not found: {pptx_path}"])

        try:
            soffice = self._resolve_soffice()
        except SlideImageExportError as exc:
            return SlideImageExportResult(status="skipped", errors=[str(exc)])

        formats = self._normalized_formats()
        if not formats:
            return SlideImageExportResult(status="skipped", errors=["no image formats configured"])

        output_dir.mkdir(parents=True, exist_ok=True)
        images_by_slide: dict[int, list[SlideImageAsset]] = {}
        errors: list[str] = []

        for fmt in formats:
            try:
                produced = self._convert_format(soffice, pptx_path, output_dir, fmt)
            except SlideImageExportError as exc:
                errors.append(str(exc))
                continue
            for slide_index, path in produced.items():
                images_by_slide.setdefault(slide_index, []).append(
                    SlideImageAsset(
                        slide_index=slide_index,
                        format=fmt,
                        path=path,
                        media_type=_media_type_for_format(fmt),
                    )
                )
            if produced and self.options.prefer_first_success:
                break

        status = "success" if images_by_slide else ("skipped" if errors else "empty")
        return SlideImageExportResult(images_by_slide=images_by_slide, status=status, errors=errors)

    def _convert_format(self, soffice: Path, pptx_path: Path, output_dir: Path, fmt: str) -> dict[int, Path]:
        normalized = _normalize_format(fmt)
        target_dir = output_dir / normalized
        target_dir.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            self._run_soffice(soffice, pptx_path, tmp_path, normalized)
            produced = _collect_slide_images(tmp_path, pptx_path.stem, normalized)

            if not produced:
                return {}

            renamed: dict[int, Path] = {}
            for slide_index, source in produced.items():
                target = target_dir / f"slide_{slide_index + 1:03d}.{normalized}"
                if target.exists():
                    target.unlink()
                shutil.move(str(source), str(target))
                renamed[slide_index] = target
            return renamed

    def _run_soffice(self, soffice: Path, pptx_path: Path, output_dir: Path, fmt: str) -> None:
        command = [
            str(soffice),
            "--headless",
            "--convert-to",
            fmt,
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ]
        attempt = 0
        while attempt < max(1, self.options.max_retries):
            attempt += 1
            try:
                subprocess.run(  # noqa: S603, S607
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.options.timeout_sec,
                )
                return
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                logger.warning(
                    "slide_image_export attempt failed (%s/%s): %s",
                    attempt,
                    self.options.max_retries,
                    exc,
                )
                if attempt >= self.options.max_retries:
                    raise SlideImageExportError(f"LibreOffice 変換に失敗しました: {exc}") from exc
                time.sleep(1)

        raise SlideImageExportError("LibreOffice 変換に失敗しました")

    def _resolve_soffice(self) -> Path:
        if self.options.soffice_path:
            candidate = Path(self.options.soffice_path)
            if candidate.exists():
                return candidate
            msg = f"指定された LibreOffice パスが見つかりません: {candidate}"
            raise SlideImageExportError(msg)

        env_path = os.environ.get("LIBREOFFICE_PATH")
        if env_path:
            candidate = Path(env_path)
            if candidate.exists():
                return candidate

        resolved = shutil.which("soffice")
        if resolved:
            return Path(resolved)

        raise SlideImageExportError("LibreOffice (soffice) が見つかりません。PATH または LIBREOFFICE_PATH を確認してください")

    def _normalized_formats(self) -> list[str]:
        formats = []
        for fmt in self.options.formats:
            normalized = _normalize_format(fmt)
            if normalized and normalized not in formats:
                formats.append(normalized)
        return formats


def _normalize_format(fmt: str) -> str:
    trimmed = fmt.strip().lower().lstrip(".")
    if trimmed == "jpeg":
        return "jpg"
    return trimmed


def _media_type_for_format(fmt: str) -> str:
    return _IMAGE_MEDIA_TYPES.get(fmt, "application/octet-stream")


def _collect_slide_images(output_dir: Path, stem: str, fmt: str) -> dict[int, Path]:
    images: dict[int, Path] = {}
    for path in sorted(output_dir.glob(f"{stem}*.{fmt}")):
        slide_index = _parse_slide_index(path, stem)
        if slide_index is None or slide_index < 0:
            continue
        if slide_index in images:
            continue
        images[slide_index] = path
    return images


def _parse_slide_index(path: Path, stem: str) -> int | None:
    name = path.stem
    if name == stem:
        return 0
    for separator in ("-", "_"):
        if name.startswith(f"{stem}{separator}"):
            suffix = name[len(stem) + 1 :]
            if suffix.isdigit():
                return int(suffix) - 1
    if name.startswith(stem):
        suffix = name[len(stem) :]
        if suffix.isdigit():
            return int(suffix) - 1
    return None


__all__ = [
    "SlideImageAsset",
    "SlideImageExportError",
    "SlideImageExportOptions",
    "SlideImageExportResult",
    "SlideImageExporter",
]
