"""共通モデル: スケジュール系で共有する最小限のモデル群。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator, model_validator


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(self, message: str, *, errors: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


# スケジュールガントチャート用モデル


class ScheduleMilestone(BaseModel):
    """スケジュール内のマイルストーン。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100, description="マイルストーン名")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="マイルストーン日付（YYYY-MM-DD）")


class ScheduleGanttMeta(BaseModel):
    """スケジュールガントチャートのメタ情報。"""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=2000, le=2100, description="対象年（開始年として使用）")
    title: str = Field(..., max_length=200, description="スケジュールタイトル")
    start_month: int = Field(..., ge=1, le=12, description="開始月（1-12）")
    end_month: int = Field(..., ge=1, le=12, description="終了月（1-12）")
    end_year: int | None = Field(None, ge=2000, le=2100, description="終了年（未指定時はyearと同じ）")
    message_line: str | None = Field(None, max_length=500, description="Message_lineに表示するメッセージ")
    milestones: list[ScheduleMilestone] = Field(default_factory=list, description="マイルストーン一覧")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ScheduleGanttMeta":
        """年月の範囲を検証する。"""
        start_year = self.year
        end_year = self.end_year or start_year
        start_month = self.start_month
        end_month = self.end_month

        if end_year < start_year:
            raise ValueError("end_year は year 以上である必要があります")

        if end_year == start_year and end_month < start_month:
            raise ValueError("同一年内では end_month は start_month 以上である必要があります")

        return self

    def get_total_months(self) -> int:
        """スケジュール全体の月数を計算する。"""
        start_year = self.year
        end_year = self.end_year or self.year
        years = end_year - start_year
        months = years * 12 + (self.end_month - self.start_month + 1)
        return months

    def get_display_unit(self) -> Literal["month", "quarter", "year"]:
        """期間に応じた表示単位を返す。"""
        total_months = self.get_total_months()
        if total_months <= 12:
            return "month"
        if total_months <= 36:
            return "quarter"
        return "year"


class ScheduleTask(BaseModel):
    """スケジュール内の個別タスク。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100, description="タスク名")
    start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="開始日（YYYY-MM-DD）")
    end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="終了日（YYYY-MM-DD）")

    @field_validator("end")
    @classmethod
    def validate_date_range(cls, value: str, info: ValidationInfo) -> str:
        start = info.data.get("start")
        if start and value < start:
            raise ValueError("終了日は開始日以降である必要があります")
        return value


class ScheduleProject(BaseModel):
    """スケジュール内のプロジェクト（タスクのグループ）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100, description="プロジェクト名")
    tasks: list[ScheduleTask] = Field(default_factory=list, description="タスク一覧")

    @field_validator("tasks")
    @classmethod
    def ensure_tasks_not_empty(cls, value: list[ScheduleTask]) -> list[ScheduleTask]:
        if not value:
            raise ValueError("プロジェクトには少なくとも1つのタスクが必要です")
        return value


class ScheduleGantt(BaseModel):
    """スケジュールガントチャート全体の構造。"""

    model_config = ConfigDict(extra="forbid")

    meta: ScheduleGanttMeta = Field(..., description="メタ情報")
    projects: list[ScheduleProject] = Field(default_factory=list, description="プロジェクト一覧")

    @field_validator("projects")
    @classmethod
    def ensure_projects_not_empty(cls, value: list[ScheduleProject]) -> list[ScheduleProject]:
        if not value:
            raise ValueError("スケジュールには少なくとも1つのプロジェクトが必要です")
        return value

    @classmethod
    def parse_file(cls, path: str | Path) -> "ScheduleGantt":
        """JSONファイルからScheduleGanttインスタンスを生成する。"""
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc
