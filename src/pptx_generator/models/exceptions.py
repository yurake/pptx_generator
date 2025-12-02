"""モデル共通の例外。"""

from __future__ import annotations

from pydantic import ValidationError

__all__ = ["SpecValidationError", "PipelineFallbackError"]


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(
        self,
        message: str,
        *,
        errors: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


class PipelineFallbackError(RuntimeError):
    """フォールバック禁止ポリシーに反した場合の実行時エラー。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
