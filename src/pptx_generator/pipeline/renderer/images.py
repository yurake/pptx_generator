from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from pptx.util import Inches

from ...models import SlideImage, TemplateImageDefaults
from .layout import LayoutBox

logger = logging.getLogger(__name__)


class ImageMixin:
    def _apply_images(self, slide, slide_spec) -> None:
        if not slide_spec.images:
            return

        for image_spec in slide_spec.images:
            self._render_single_image(slide, slide_spec.id, image_spec)

    def _render_single_image(
        self,
        slide,
        slide_id: str,
        image_spec: SlideImage,
    ) -> None:
        image_defaults = self._style.image
        fallback_box = self._determine_image_fallback_box(image_defaults)
        element_label = image_spec.id or (image_spec.anchor or "image")
        resolution = self._resolve_anchor(
            slide,
            image_spec.anchor,
            fallback_box,
            owner_description=f"画像要素 '{element_label}' (slide_id='{slide_id}')",
        )
        anchor_shape = resolution.shape
        if resolution.is_placeholder:
            self._prepare_placeholder(anchor_shape)

        image_path = self._resolve_image_source(image_spec.source, image_spec.id)
        left = self._override_emu(resolution.left, image_spec.left_in)
        top = self._override_emu(resolution.top, image_spec.top_in)
        target_width = self._override_emu(resolution.width, image_spec.width_in)
        target_height = self._override_emu(resolution.height, image_spec.height_in)

        picture = slide.shapes.add_picture(str(image_path), left, top)
        self._resize_picture(
            picture,
            target_width,
            target_height,
            image_spec.sizing or image_defaults.sizing,
        )
        self._assign_picture_name(picture, image_spec)

        if anchor_shape is not None:
            self._remove_shape(anchor_shape)

    @staticmethod
    def _determine_image_fallback_box(image_defaults: TemplateImageDefaults) -> LayoutBox:
        default_box = image_defaults.fallback_box
        if default_box is not None:
            return LayoutBox(
                default_box.left_in,
                default_box.top_in,
                default_box.width_in,
                default_box.height_in,
            )
        return LayoutBox(1.0, 1.75, 8.0, 4.5)

    @staticmethod
    def _assign_picture_name(picture, image_spec: SlideImage) -> None:
        target_name = image_spec.anchor or image_spec.id
        if not target_name:
            return
        try:
            picture.name = target_name
        except ValueError:
            logger.debug("画像図形名 '%s' の設定に失敗", target_name, exc_info=True)

    def _resolve_image_source(self, source: str, image_id: str) -> Path:
        parsed = urlparse(str(source))
        if parsed.scheme in {"http", "https"}:
            return self._download_remote_image(str(source), image_id)

        path = Path(source).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            msg = f"画像ファイルが見つかりません: {source}"
            raise FileNotFoundError(msg)
        return path

    def _download_remote_image(self, url: str, image_id: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(url).suffix or ".img"
        )
        try:
            with urlopen(url) as response:
                tmp.write(response.read())
        finally:
            tmp.close()
        path = Path(tmp.name)
        self._temp_files.append(path)
        logger.info("画像をダウンロードしました: id=%s, path=%s", image_id, path)
        return path

    def _resize_picture(self, picture, width: int, height: int, sizing: str) -> None:
        if width is None and height is None:
            return

        target_width = width or picture.width
        target_height = height or picture.height

        if sizing == "stretch":
            picture.width = target_width
            picture.height = target_height
            return

        original_width = picture.width
        original_height = picture.height
        if original_width == 0 or original_height == 0:
            picture.width = target_width
            picture.height = target_height
            return

        width_ratio = target_width / original_width
        height_ratio = target_height / original_height

        if sizing == "fill":
            scale = max(width_ratio, height_ratio)
        else:  # fit
            scale = min(width_ratio, height_ratio)

        picture.width = int(original_width * scale)
        picture.height = int(original_height * scale)

        if width is not None:
            picture.left += (target_width - picture.width) // 2
        if height is not None:
            picture.top += (target_height - picture.height) // 2

    def _cleanup_temp_files(self) -> None:
        for path in self._temp_files:
            try:
                os.unlink(path)
            except OSError:
                logger.debug("一時ファイル削除に失敗: %s", path)
        self._temp_files.clear()
