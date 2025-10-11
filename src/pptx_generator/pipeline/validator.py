"""入力 JSON の業務ルール検証を担うステップ。"""

from __future__ import annotations

import logging

from ..models import JobSpec, SpecValidationError
from .base import PipelineContext

logger = logging.getLogger(__name__)


class SpecValidatorStep:
    """スキーマ検証後のビジネスルール確認。"""

    name = "validator"

    def __init__(
        self,
        *,
        max_title_length: int = 25,
        max_bullet_length: int = 120,
        max_bullet_level: int = 3,
        forbidden_words: tuple[str, ...] = (),
    ) -> None:
        self.max_title_length = max_title_length
        self.max_bullet_length = max_bullet_length
        self.max_bullet_level = max_bullet_level
        self.forbidden_words = forbidden_words

    def run(self, context: PipelineContext) -> None:
        spec = context.spec
        logger.debug("slide count=%s", len(spec.slides))
        self._validate_slide_presence(spec)
        self._validate_title_length(spec)
        self._validate_bullet_length(spec)
        self._validate_bullet_level(spec)
        self._validate_forbidden_words(spec)

    def _validate_slide_presence(self, spec: JobSpec) -> None:
        if not spec.slides:
            raise SpecValidationError("スライドが 1 件も定義されていません")

    def _validate_title_length(self, spec: JobSpec) -> None:
        for slide in spec.slides:
            if slide.title and len(slide.title) > self.max_title_length:
                msg = f"スライド '{slide.id}' のタイトルが {self.max_title_length} 文字を超えています"
                raise SpecValidationError(msg)

    def _validate_bullet_length(self, spec: JobSpec) -> None:
        for slide in spec.slides:
            for bullet in slide.iter_bullets():
                if len(bullet.text) > self.max_bullet_length:
                    msg = (
                        f"スライド '{slide.id}' の箇条書き '{bullet.id}' が {self.max_bullet_length} 文字を超えています"
                    )
                    raise SpecValidationError(msg)

    def _validate_bullet_level(self, spec: JobSpec) -> None:
        for slide in spec.slides:
            for bullet in slide.iter_bullets():
                if bullet.level > self.max_bullet_level:
                    msg = (
                        f"スライド '{slide.id}' の箇条書き '{bullet.id}' のレベルが {self.max_bullet_level} を超えています"
                    )
                    raise SpecValidationError(msg)

    def _validate_forbidden_words(self, spec: JobSpec) -> None:
        if not self.forbidden_words:
            return
        for slide in spec.slides:
            self._check_text(slide.id, "title", slide.title)
            for bullet in slide.iter_bullets():
                self._check_text(slide.id, bullet.id, bullet.text)

    def _check_text(self, slide_id: str, label: str, text: str | None) -> None:
        if not text:
            return
        for word in self.forbidden_words:
            if word and word in text:
                msg = f"スライド '{slide_id}' の '{label}' に禁止ワード '{word}' が含まれています"
                raise SpecValidationError(msg)
