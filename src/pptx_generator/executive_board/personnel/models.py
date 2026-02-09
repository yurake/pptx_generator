"""開発要員計画専用モデル。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(self, message: str, *, errors: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


class PersonnelMonthData(BaseModel):
    """月ごとの工数データ。"""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=2000, le=2100, description="年")
    month: int = Field(..., ge=1, le=12, description="月")
    employee: float = Field(0.0, ge=0.0, description="社員工数")
    pn: float = Field(0.0, ge=0.0, description="PN工数")
    si: float = Field(0.0, ge=0.0, description="SI工数")

    @property
    def total(self) -> float:
        return self.employee + self.pn + self.si

    @property
    def fiscal_year(self) -> int:
        if 1 <= self.month <= 3:
            return self.year - 1
        return self.year

    @property
    def quarter(self) -> int:
        if 4 <= self.month <= 6:
            return 1
        if 7 <= self.month <= 9:
            return 2
        if 10 <= self.month <= 12:
            return 3
        return 4


class PersonnelTaskData(BaseModel):
    """タスクごとの工数データ。"""

    model_config = ConfigDict(extra="forbid")

    task_name: str = Field(..., max_length=100, description="タスク名")
    months: list[PersonnelMonthData] = Field(default_factory=list, description="月別工数データ")

    @property
    def total_employee(self) -> float:
        return sum(m.employee for m in self.months)

    @property
    def total_pn(self) -> float:
        return sum(m.pn for m in self.months)

    @property
    def total_si(self) -> float:
        return sum(m.si for m in self.months)

    @property
    def total(self) -> float:
        return self.total_employee + self.total_pn + self.total_si


class PersonnelPhaseData(BaseModel):
    """フェーズごとの工数データ。"""

    model_config = ConfigDict(extra="forbid")

    phase_name: str = Field(..., max_length=100, description="フェーズ名")
    tasks: list[PersonnelTaskData] = Field(default_factory=list, description="タスク別工数データ")

    @property
    def total_employee(self) -> float:
        return sum(t.total_employee for t in self.tasks)

    @property
    def total_pn(self) -> float:
        return sum(t.total_pn for t in self.tasks)

    @property
    def total_si(self) -> float:
        return self.total_employee + self.total_pn + self.total_si

    @property
    def total(self) -> float:
        return self.total_employee + self.total_pn + self.total_si


class PersonnelData(BaseModel):
    """開発要員計画の工数データ（中間生成ファイル1）。"""

    model_config = ConfigDict(extra="forbid")

    extracted_at: str = Field(..., description="抽出日時（ISO8601）")
    source_path: str = Field(..., description="元ファイルパス")
    phases: list[PersonnelPhaseData] = Field(default_factory=list, description="フェーズ別工数データ")

    @classmethod
    def parse_file(cls, path: str | Path) -> "PersonnelData":
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc


class PersonnelScheduleTask(BaseModel):
    """スケジュールと工数を統合したタスクデータ。"""

    model_config = ConfigDict(extra="forbid")

    task_name: str = Field(..., max_length=100, description="タスク名")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="開始日（YYYY-MM-DD）")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="終了日（YYYY-MM-DD）")
    months: list[PersonnelMonthData] = Field(default_factory=list, description="月別工数データ")


class PersonnelSchedulePhase(BaseModel):
    """スケジュールと工数を統合したフェーズデータ。"""

    model_config = ConfigDict(extra="forbid")

    phase_name: str = Field(..., max_length=100, description="フェーズ名")
    tasks: list[PersonnelScheduleTask] = Field(default_factory=list, description="タスク一覧")


class PersonnelScheduleMilestone(BaseModel):
    """マイルストーン情報。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100, description="マイルストーン名")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="日付（YYYY-MM-DD）")


class PersonnelQuarterSummary(BaseModel):
    """四半期ごとの工数サマリ。"""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: int = Field(..., description="年度")
    quarter: int = Field(..., ge=1, le=4, description="四半期（1-4）")
    employee: float = Field(0.0, ge=0.0, description="社員工数")
    pn: float = Field(0.0, ge=0.0, description="PN工数")
    si: float = Field(0.0, ge=0.0, description="SI工数")

    @property
    def total(self) -> float:
        return self.employee + self.pn + self.si


class PersonnelMonthSummary(BaseModel):
    """月ごとの工数サマリ（月単位表示用）。"""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., description="年（暦年）")
    month: int = Field(..., ge=1, le=12, description="月（1-12）")
    employee: float = Field(0.0, ge=0.0, description="社員工数")
    pn: float = Field(0.0, ge=0.0, description="PN工数")
    si: float = Field(0.0, ge=0.0, description="SI工数")

    @property
    def total(self) -> float:
        return self.employee + self.pn + self.si

    @property
    def fiscal_year(self) -> int:
        if 1 <= self.month <= 3:
            return self.year - 1
        return self.year


class PersonnelPhaseMonthSummary(BaseModel):
    """フェーズごとの月別工数サマリ（月単位表示用）。"""

    model_config = ConfigDict(extra="forbid")

    phase_name: str = Field(..., max_length=100, description="フェーズ名")
    months: list[PersonnelMonthSummary] = Field(default_factory=list, description="月別工数")
    total_employee: float = Field(0.0, ge=0.0, description="社員工数合計")
    total_pn: float = Field(0.0, ge=0.0, description="PN工数合計")
    total_si: float = Field(0.0, ge=0.0, description="SI工数合計")

    @property
    def total(self) -> float:
        return self.total_employee + self.total_pn + self.total_si


class PersonnelPhaseSummary(BaseModel):
    """フェーズごとの四半期別工数サマリ。"""

    model_config = ConfigDict(extra="forbid")

    phase_name: str = Field(..., max_length=100, description="フェーズ名")
    quarters: list[PersonnelQuarterSummary] = Field(default_factory=list, description="四半期別工数")
    total_employee: float = Field(0.0, ge=0.0, description="社員工数合計")
    total_pn: float = Field(0.0, ge=0.0, description="PN工数合計")
    total_si: float = Field(0.0, ge=0.0, description="SI工数合計")

    @property
    def total(self) -> float:
        return self.total_employee + self.total_pn + self.total_si


class PersonnelMessage(BaseModel):
    """要員計画のメッセージ項目。"""

    model_config = ConfigDict(extra="forbid")

    number: int = Field(..., ge=1, description="番号（①②③など）")
    text: str = Field(..., max_length=500, description="メッセージ本文")
    highlight_quarters: list[tuple[int, int]] = Field(default_factory=list, description="ハイライトする四半期リスト（年度, 四半期）")


DisplayUnit = Literal["month", "quarter"]


class DevelopmentPersonnelPlan(BaseModel):
    """開発要員計画の統合データ（中間生成ファイル2）。"""

    model_config = ConfigDict(extra="forbid")

    generated_at: str = Field(..., description="生成日時（ISO8601）")
    schedule_source: str = Field(..., description="スケジュールファイルパス")
    personnel_source: str = Field(..., description="工数ファイルパス")

    title: str = Field("開発要員計画", max_length=100, description="スライドタイトル")
    department: str = Field("情報システム部", max_length=100, description="部門名")

    display_unit: DisplayUnit = Field("quarter", description="表示単位（month=月単位, quarter=四半期単位）")
    total_months: int = Field(0, ge=0, description="プロジェクト全体の月数")

    fiscal_years: list[int] = Field(default_factory=list, description="対象年度一覧")
    target_months: list[tuple[int, int]] = Field(default_factory=list, description="対象月一覧（暦年, 月）")

    phases: list[PersonnelSchedulePhase] = Field(default_factory=list, description="フェーズ別データ")
    milestones: list[PersonnelScheduleMilestone] = Field(default_factory=list, description="マイルストーン一覧")

    phase_summaries: list[PersonnelPhaseSummary] = Field(default_factory=list, description="フェーズ別四半期サマリ")
    total_summary: list[PersonnelQuarterSummary] = Field(default_factory=list, description="全体四半期サマリ")

    phase_month_summaries: list[PersonnelPhaseMonthSummary] = Field(default_factory=list, description="フェーズ別月サマリ")
    total_month_summary: list[PersonnelMonthSummary] = Field(default_factory=list, description="全体月サマリ")

    messages: list[PersonnelMessage] = Field(default_factory=list, description="メッセージ一覧")

    @classmethod
    def parse_file(cls, path: str | Path) -> "DevelopmentPersonnelPlan":
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc
