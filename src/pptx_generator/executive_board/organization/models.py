"""組織図専用モデル。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(self, message: str, *, errors: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


class OrganizationGroup(BaseModel):
    """組織グループ（# 見出しの単位）。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=100, description="グループタイトル（例: PMO、プロジェクトオーナー）")
    members: list[str] = Field(default_factory=list, description="メンバー一覧")

    @field_validator("members")
    @classmethod
    def ensure_members_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("グループには少なくとも1人のメンバーが必要です")
        return value


OrganizationCategoryColor = Literal["light_green", "light_blue", "green", "blue"]


class OrganizationCategory(BaseModel):
    """組織カテゴリー（## 見出しの単位）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100, description="カテゴリー名（例: SMBC、JRI、開発ベンダー）")
    groups: list[OrganizationGroup] = Field(default_factory=list, description="グループ一覧")
    color: OrganizationCategoryColor = Field("light_blue", description="背景色")
    box_title_color: OrganizationCategoryColor = Field("blue", description="タイトルボックスの背景色")

    @field_validator("groups")
    @classmethod
    def ensure_groups_not_empty(cls, value: list[OrganizationGroup]) -> list[OrganizationGroup]:
        if not value:
            raise ValueError("カテゴリーには少なくとも1つのグループが必要です")
        return value


class OrganizationChartMeta(BaseModel):
    """組織図のメタ情報。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field("組織図", max_length=200, description="タイトル")
    generated_at: str | None = Field(None, description="生成日時（ISO8601）")


class OrganizationChart(BaseModel):
    """組織図全体の構造。"""

    model_config = ConfigDict(extra="forbid")

    meta: OrganizationChartMeta = Field(default_factory=OrganizationChartMeta, description="メタ情報")
    categories: list[OrganizationCategory] = Field(default_factory=list, description="カテゴリー一覧")

    @field_validator("categories")
    @classmethod
    def ensure_categories_not_empty(cls, value: list[OrganizationCategory]) -> list[OrganizationCategory]:
        if not value:
            raise ValueError("組織図には少なくとも1つのカテゴリーが必要です")
        return value

    @classmethod
    def parse_file(cls, path: str | Path) -> "OrganizationChart":
        """JSONファイルからOrganizationChartインスタンスを生成する。"""
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc
