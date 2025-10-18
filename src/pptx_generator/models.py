"""JSON 入力仕様を表現する Pydantic モデル群。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal

from pydantic import (BaseModel, ConfigDict, Field, HttpUrl, ValidationError,
                      ValidationInfo, field_validator)


class FontSpec(BaseModel):
    name: str = Field(..., description="フォントファミリ名")
    size_pt: float = Field(..., ge=6.0, description="フォントサイズ")
    bold: bool = False
    italic: bool = False
    color_hex: str = Field("#000000", pattern=r"^#?[0-9A-Fa-f]{6}$")

    @field_validator("color_hex")
    @classmethod
    def normalize_hex(cls, value: str) -> str:
        return value if value.startswith("#") else f"#{value}"


class SlideBullet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(..., max_length=200)
    level: int = Field(0, ge=0, le=5)
    font: FontSpec | None = None


class SlideBulletGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor: str | None = None
    items: list[SlideBullet] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def ensure_items_not_empty(cls, value: list[SlideBullet]) -> list[SlideBullet]:
        if not value:
            raise ValueError("items には 1 つ以上の bullet を指定してください")
        return value


class SlideImage(BaseModel):
    id: str
    source: HttpUrl | str
    anchor: str | None = None
    sizing: Literal["fit", "fill", "stretch"] = "fit"
    left_in: float | None = None
    top_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None


class TableStyle(BaseModel):
    header_fill: str | None = Field(None, pattern=r"^#?[0-9A-Fa-f]{6}$")
    zebra: bool = False

    @field_validator("header_fill")
    @classmethod
    def normalize_header_fill(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.startswith("#") else f"#{value}"


class SlideTable(BaseModel):
    id: str
    anchor: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str | int | float]] = Field(default_factory=list)
    style: TableStyle | None = None


class ChartSeries(BaseModel):
    name: str
    values: list[int | float] = Field(default_factory=list)
    color_hex: str | None = Field(None, pattern=r"^#?[0-9A-Fa-f]{6}$")

    @field_validator("color_hex")
    @classmethod
    def normalize_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.startswith("#") else f"#{value}"


class ChartOptions(BaseModel):
    data_labels: bool = False
    y_axis_format: str | None = None


class SlideChart(BaseModel):
    id: str
    anchor: str | None = None
    type: str
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    options: ChartOptions | None = None


class TextboxPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_in: float
    top_in: float
    width_in: float
    height_in: float


class TextboxParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: int = Field(0, ge=0, le=5)
    line_spacing_pt: float | None = Field(None, ge=0.0)
    space_before_pt: float | None = Field(None, ge=0.0)
    space_after_pt: float | None = Field(None, ge=0.0)
    align: Literal[
        "left",
        "center",
        "right",
        "justify",
        "distributed",
    ] | None = None


class SlideTextbox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    anchor: str | None = None
    position: TextboxPosition | None = None
    font: FontSpec | None = None
    paragraph: TextboxParagraph | None = None


class Slide(BaseModel):
    id: str
    layout: str
    title: str | None = None
    subtitle: str | None = None
    notes: str | None = None
    bullets: list[SlideBulletGroup] = Field(default_factory=list)
    images: list[SlideImage] = Field(default_factory=list)
    tables: list[SlideTable] = Field(default_factory=list)
    charts: list[SlideChart] = Field(default_factory=list)
    textboxes: list[SlideTextbox] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def iter_bullet_groups(self) -> Iterable[SlideBulletGroup]:
        """箇条書きグループを順序通りに返す。"""

        return tuple(self.bullets)

    def iter_bullets(self) -> Iterator[SlideBullet]:
        """すべての箇条書き項目を順序通りにイテレートする。"""

        for group in self.bullets:
            yield from group.items


class JobMeta(BaseModel):
    schema_version: str
    title: str
    client: str | None = None
    author: str | None = None
    created_at: str | None = None
    theme: str | None = None
    locale: str = "ja-JP"


class JobAuth(BaseModel):
    created_by: str
    department: str | None = None


class JobSpec(BaseModel):
    meta: JobMeta
    auth: JobAuth
    slides: list[Slide] = Field(default_factory=list)

    @classmethod
    def parse_file(cls, path: str | Path) -> "JobSpec":
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc


ContentSlideStatus = Literal["draft", "approved", "returned"]


class ContentTableData(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)

    @field_validator("rows", mode="before")
    @classmethod
    def normalize_rows(cls, value: list[list[str | int | float]]) -> list[list[str]]:
        return [[str(cell) for cell in row] for row in value]

    @field_validator("rows")
    @classmethod
    def validate_row_length(
        cls, value: list[list[str]], info: ValidationInfo
    ) -> list[list[str]]:
        headers: list[str] = info.data.get("headers", [])
        if headers:
            expected = len(headers)
            for row in value:
                if len(row) != expected:
                    msg = "各行の列数は headers と一致する必要があります"
                    raise ValueError(msg)
        return value


class ContentElements(BaseModel):
    title: str = Field(..., max_length=120)
    body: list[str] = Field(default_factory=list)
    table_data: ContentTableData | None = None
    note: str | None = None

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: list[str]) -> list[str]:
        if len(value) > 6:
            msg = "body は最大 6 行までです"
            raise ValueError(msg)
        for line in value:
            if len(line) > 40:
                msg = "body の各行は 40 文字以内で入力してください"
                raise ValueError(msg)
        return value


JsonPatchOp = Literal["add", "remove", "replace", "move", "copy", "test"]


class JsonPatchOperation(BaseModel):
    op: JsonPatchOp
    path: str
    value: object | None = None
    from_path: str | None = Field(default=None, alias="from")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("path")
    @classmethod
    def ensure_absolute_path(cls, value: str) -> str:
        if not value.startswith("/"):
            msg = "JSON Patch path は '/' で開始する必要があります"
            raise ValueError(msg)
        return value

    @field_validator("from_path")
    @classmethod
    def ensure_from_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/"):
            msg = "JSON Patch from は '/' で開始する必要があります"
            raise ValueError(msg)
        return value


class AutoFixProposal(BaseModel):
    patch_id: str
    description: str
    patch: list[JsonPatchOperation] = Field(default_factory=list)

    @field_validator("patch", mode="before")
    @classmethod
    def normalize_patch(
        cls, value: list[JsonPatchOperation] | JsonPatchOperation | None
    ) -> list[JsonPatchOperation]:
        if value is None:
            return []
        if isinstance(value, JsonPatchOperation):
            return [value]
        return value

    @field_validator("patch")
    @classmethod
    def ensure_non_empty(cls, value: list[JsonPatchOperation]) -> list[JsonPatchOperation]:
        if not value:
            msg = "Auto-fix 提案には少なくとも 1 件の JSON Patch を含めてください"
            raise ValueError(msg)
        return value


class AIReviewIssue(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] | None = None


class AIReviewResult(BaseModel):
    grade: Literal["A", "B", "C"]
    issues: list[AIReviewIssue] = Field(default_factory=list)
    autofix_proposals: list[AutoFixProposal] = Field(default_factory=list)


class ContentSlide(BaseModel):
    id: str
    intent: str
    type_hint: str | None = None
    elements: ContentElements
    status: ContentSlideStatus = "draft"
    ai_review: AIReviewResult | None = None
    applied_autofix: list[str] = Field(default_factory=list)

    @field_validator("applied_autofix", mode="before")
    @classmethod
    def normalize_autofix_ids(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return value


class ContentDocumentMeta(BaseModel):
    tone: str | None = None
    audience: str | None = None
    summary: str | None = None


class ContentApprovalDocument(BaseModel):
    slides: list[ContentSlide] = Field(default_factory=list)
    meta: ContentDocumentMeta | None = None

    def ensure_all_approved(self) -> None:
        not_approved = [slide.id for slide in self.slides if slide.status != "approved"]
        if not_approved:
            msg = f"承認済みドキュメント内に未承認のカードがあります: {', '.join(not_approved)}"
            raise ValueError(msg)


class ContentReviewLogEntry(BaseModel):
    slide_id: str
    action: Literal["approve", "return", "comment", "autofix"]
    actor: str
    timestamp: datetime
    notes: str | None = None
    ai_grade: Literal["A", "B", "C"] | None = None
    applied_autofix: list[str] = Field(default_factory=list)

    @field_validator("applied_autofix", mode="before")
    @classmethod
    def normalize_autofix(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return value


DraftStatus = Literal["draft", "approved", "returned"]


class DraftLayoutCandidate(BaseModel):
    layout_id: str
    score: float = Field(ge=0.0, le=1.0)


class DraftSlideCard(BaseModel):
    ref_id: str
    order: int
    layout_hint: str
    locked: bool = False
    status: DraftStatus = "draft"
    layout_candidates: list[DraftLayoutCandidate] = Field(default_factory=list)
    appendix: bool = False


class DraftSection(BaseModel):
    name: str
    order: int
    status: DraftStatus = "draft"
    slides: list[DraftSlideCard] = Field(default_factory=list)

    @field_validator("slides")
    @classmethod
    def ensure_unique_slide_refs(cls, value: list[DraftSlideCard]) -> list[DraftSlideCard]:
        ref_ids = {card.ref_id for card in value}
        if len(ref_ids) != len(value):
            msg = "セクション内の ref_id は一意である必要があります"
            raise ValueError(msg)
        return value


class DraftMeta(BaseModel):
    target_length: int | None = None
    structure_pattern: str | None = None
    appendix_limit: int | None = None


class DraftDocument(BaseModel):
    sections: list[DraftSection] = Field(default_factory=list)
    meta: DraftMeta = Field(default_factory=DraftMeta)

    @field_validator("sections")
    @classmethod
    def ensure_section_order(cls, value: list[DraftSection]) -> list[DraftSection]:
        orders = {section.order for section in value}
        if len(orders) != len(value):
            msg = "セクション order が重複しています"
            raise ValueError(msg)
        return value


class DraftLogEntry(BaseModel):
    target_type: Literal["section", "slide"]
    target_id: str
    action: Literal["generate", "move", "hint", "approve", "appendix", "return"]
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    changes: dict[str, object] | None = None


class MappingSlideMeta(BaseModel):
    section: str | None = None
    page_no: int | None = None
    sources: list[str] = Field(default_factory=list)
    fallback: str = "none"


class RenderingReadySlide(BaseModel):
    layout_id: str
    elements: dict[str, Any] = Field(default_factory=dict)
    meta: MappingSlideMeta


class RenderingReadyMeta(BaseModel):
    template_version: str | None = None
    content_hash: str | None = None
    generated_at: str


class RenderingReadyDocument(BaseModel):
    slides: list[RenderingReadySlide] = Field(default_factory=list)
    meta: RenderingReadyMeta


class MappingCandidate(BaseModel):
    layout_id: str
    score: float = Field(ge=0.0, le=1.0)


class MappingFallbackState(BaseModel):
    applied: bool = False
    history: list[str] = Field(default_factory=list)
    reason: str | None = None


class MappingAIPatch(BaseModel):
    patch_id: str
    description: str
    patch: list[JsonPatchOperation] = Field(default_factory=list)


class MappingLogSlide(BaseModel):
    ref_id: str
    selected_layout: str
    candidates: list[MappingCandidate] = Field(default_factory=list)
    fallback: MappingFallbackState = Field(default_factory=MappingFallbackState)
    ai_patch: list[MappingAIPatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MappingLogMeta(BaseModel):
    mapping_time_ms: int | None = None
    fallback_count: int = 0
    ai_patch_count: int = 0


class MappingLog(BaseModel):
    slides: list[MappingLogSlide] = Field(default_factory=list)
    meta: MappingLogMeta = Field(default_factory=MappingLogMeta)


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(
        self, message: str, *, errors: list[dict[str, object]] | None = None
    ) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


# テンプレート抽出用モデル

class ShapeInfo(BaseModel):
    """図形情報を表現するモデル。"""
    
    name: str = Field(..., description="図形名（アンカー名）")
    shape_type: str = Field(..., description="図形種別")
    left_in: float = Field(..., description="左端位置（インチ）")
    top_in: float = Field(..., description="上端位置（インチ）")
    width_in: float = Field(..., description="幅（インチ）")
    height_in: float = Field(..., description="高さ（インチ）")
    text: str | None = Field(None, description="初期テキスト")
    placeholder_type: str | None = Field(None, description="プレースホルダー種別")
    is_placeholder: bool = Field(False, description="プレースホルダーかどうか")
    error: str | None = Field(None, description="抽出時のエラー")
    missing_fields: list[str] = Field(default_factory=list, description="欠落フィールド")
    conflict: str | None = Field(None, description="SlideBullet拡張仕様との競合")


class LayoutInfo(BaseModel):
    """レイアウト情報を表現するモデル。"""

    name: str = Field(..., description="レイアウト名")
    identifier: str | None = Field(None, description="レイアウト固有識別子")
    anchors: list[ShapeInfo] = Field(default_factory=list, description="図形・プレースホルダー一覧")
    error: str | None = Field(None, description="レイアウト抽出時のエラー")


class TemplateSpec(BaseModel):
    """テンプレート仕様全体を表現するモデル。"""

    template_path: str = Field(..., description="テンプレートファイルパス")
    extracted_at: str = Field(..., description="抽出日時（ISO8601）")
    layouts: list[LayoutInfo] = Field(default_factory=list, description="レイアウト一覧")
    warnings: list[str] = Field(default_factory=list, description="警告メッセージ")
    errors: list[str] = Field(default_factory=list, description="エラーメッセージ")


# テンプレートリリース管理用モデル


class TemplateReleaseLayoutDetail(BaseModel):
    """各レイアウトの要約情報。"""

    name: str = Field(..., description="レイアウト名")
    anchor_count: int = Field(..., description="図形・アンカー数")
    placeholder_count: int = Field(..., description="プレースホルダー数")
    anchor_names: list[str] = Field(default_factory=list, description="アンカー名一覧")
    placeholder_names: list[str] = Field(default_factory=list, description="プレースホルダー名一覧")
    duplicate_anchor_names: list[str] = Field(default_factory=list, description="重複しているアンカー名一覧")
    issues: list[str] = Field(default_factory=list, description="レイアウト内で検出された問題")


class TemplateReleaseLayouts(BaseModel):
    """テンプレート全体のレイアウトサマリ。"""

    total: int = Field(..., description="レイアウト総数")
    placeholders_avg: float = Field(..., description="レイアウトあたりプレースホルダー平均数")
    details: list[TemplateReleaseLayoutDetail] = Field(default_factory=list, description="レイアウト詳細一覧")


class TemplateReleaseDiagnostics(BaseModel):
    """テンプレートリリース時の診断結果。"""

    warnings: list[str] = Field(default_factory=list, description="警告一覧")
    errors: list[str] = Field(default_factory=list, description="エラー一覧")


class TemplateReleaseGoldenRun(BaseModel):
    """ゴールデンサンプルによる互換性検証の結果。"""

    spec_path: str = Field(..., description="検証に使用した spec ファイルパス")
    status: Literal["passed", "failed"] = Field(..., description="検証結果のステータス")
    output_dir: str = Field(..., description="検証成果物を保存したディレクトリ")
    pptx_path: str | None = Field(None, description="生成された PPTX ファイルのパス")
    analysis_path: str | None = Field(None, description="Analyzer 出力のパス")
    pdf_path: str | None = Field(None, description="生成された PDF のパス")
    warnings: list[str] = Field(default_factory=list, description="検証時に検出された警告")
    errors: list[str] = Field(default_factory=list, description="検証時に検出されたエラー")


class TemplateReleaseAnalyzerIssueSummary(BaseModel):
    """Analyzer が検出した指摘の件数サマリ。"""

    total: int = Field(0, description="指摘件数合計")
    by_type: dict[str, int] = Field(
        default_factory=dict, description="issue type ごとの件数"
    )
    by_severity: dict[str, int] = Field(
        default_factory=dict, description="severity ごとの件数"
    )


class TemplateReleaseAnalyzerFixSummary(BaseModel):
    """Analyzer が提示した修正案の件数サマリ。"""

    total: int = Field(0, description="修正案件数合計")
    by_type: dict[str, int] = Field(
        default_factory=dict, description="fix type ごとの件数"
    )


class TemplateReleaseAnalyzerRunMetrics(BaseModel):
    """ゴールデンサンプル単位の Analyzer メトリクス。"""

    spec_path: str = Field(..., description="対象となった spec ファイルパス")
    status: Literal["included", "skipped"] = Field(
        ..., description="集計に含めたかどうか"
    )
    issues: TemplateReleaseAnalyzerIssueSummary = Field(
        ..., description="指摘サマリ"
    )
    fixes: TemplateReleaseAnalyzerFixSummary = Field(
        ..., description="修正案サマリ"
    )


class TemplateReleaseAnalyzerSummary(BaseModel):
    """Analyzer メトリクスの集計結果。"""

    run_count: int = Field(0, description="集計対象となったゴールデンサンプル数")
    issues: TemplateReleaseAnalyzerIssueSummary = Field(
        default_factory=TemplateReleaseAnalyzerIssueSummary,
        description="指摘サマリ",
    )
    fixes: TemplateReleaseAnalyzerFixSummary = Field(
        default_factory=TemplateReleaseAnalyzerFixSummary,
        description="修正案サマリ",
    )


class TemplateReleaseAnalyzerMetrics(BaseModel):
    """テンプレートリリース時に集計した Analyzer メトリクス。"""

    aggregated_at: str = Field(..., description="集計日時（ISO8601）")
    runs: list[TemplateReleaseAnalyzerRunMetrics] = Field(
        default_factory=list, description="各ゴールデンサンプルのメトリクス"
    )
    summary: TemplateReleaseAnalyzerSummary = Field(
        default_factory=TemplateReleaseAnalyzerSummary, description="集計サマリ"
    )


class TemplateReleaseAnalyzerSummaryDelta(BaseModel):
    """Analyzer メトリクスの差分サマリ。"""

    issues: dict[str, int] = Field(
        default_factory=dict, description="issue type ごとの件数差分"
    )
    severity: dict[str, int] = Field(
        default_factory=dict, description="severity ごとの件数差分"
    )
    fixes: dict[str, int] = Field(
        default_factory=dict, description="fix type ごとの件数差分"
    )
    total_issue_change: int = Field(
        0, description="指摘件数合計の差分（current - baseline）"
    )
    total_fix_change: int = Field(
        0, description="修正案件数合計の差分（current - baseline）"
    )


class TemplateReleaseAnalyzerReport(BaseModel):
    """リリースレポートに含める Analyzer メトリクスの比較。"""

    current: TemplateReleaseAnalyzerSummary = Field(
        ..., description="現在バージョンの Analyzer サマリ"
    )
    baseline: TemplateReleaseAnalyzerSummary | None = Field(
        None, description="比較元バージョンの Analyzer サマリ"
    )
    delta: TemplateReleaseAnalyzerSummaryDelta | None = Field(
        None, description="差分サマリ"
    )


class TemplateRelease(BaseModel):
    """テンプレートリリースメタ情報。"""

    template_id: str = Field(..., description="テンプレート識別子")
    brand: str = Field(..., description="ブランド名")
    version: str = Field(..., description="テンプレートバージョン")
    template_path: str = Field(..., description="テンプレートファイルのパス")
    hash: str = Field(..., description="テンプレートファイルの SHA256 ハッシュ")
    generated_at: str = Field(..., description="リリース生成日時（ISO8601）")
    generated_by: str | None = Field(None, description="リリース生成者")
    reviewed_by: str | None = Field(None, description="レビュー担当者")
    extractor: dict[str, str] | None = Field(
        default=None, description="抽出処理に関するメタ情報"
    )
    layouts: TemplateReleaseLayouts = Field(..., description="レイアウトの統計情報")
    diagnostics: TemplateReleaseDiagnostics = Field(..., description="診断結果")
    analyzer_metrics: TemplateReleaseAnalyzerMetrics | None = Field(
        default=None, description="Analyzer 出力に基づく監査メトリクス"
    )
    golden_runs: list[TemplateReleaseGoldenRun] = Field(
        default_factory=list, description="ゴールデンサンプル検証の結果一覧"
    )


class TemplateReleaseLayoutDiff(BaseModel):
    """レイアウト単位の差分情報。"""

    name: str = Field(..., description="レイアウト名")
    anchors_added: list[str] = Field(default_factory=list, description="追加されたアンカー名")
    anchors_removed: list[str] = Field(default_factory=list, description="削除されたアンカー名")
    placeholders_added: list[str] = Field(default_factory=list, description="追加されたプレースホルダー名")
    placeholders_removed: list[str] = Field(default_factory=list, description="削除されたプレースホルダー名")
    duplicate_anchor_names: list[str] = Field(
        default_factory=list, description="現在のレイアウトで検出された重複アンカー名"
    )


class TemplateReleaseChanges(BaseModel):
    """テンプレートリリース間の差分サマリ。"""

    layouts_added: list[str] = Field(default_factory=list, description="追加されたレイアウト名")
    layouts_removed: list[str] = Field(default_factory=list, description="削除されたレイアウト名")
    layout_diffs: list[TemplateReleaseLayoutDiff] = Field(
        default_factory=list, description="差分が発生したレイアウトの詳細"
    )


class TemplateReleaseReport(BaseModel):
    """テンプレートリリース差分レポート。"""

    template_id: str = Field(..., description="比較対象のテンプレート識別子")
    baseline_id: str | None = Field(None, description="比較元テンプレート識別子")
    generated_at: str = Field(..., description="レポート生成日時（ISO8601）")
    hashes: dict[str, str | None] = Field(
        ..., description="現在およびベースラインのハッシュ値"
    )
    changes: TemplateReleaseChanges = Field(..., description="差分サマリ")
    diagnostics: TemplateReleaseDiagnostics = Field(..., description="現在テンプレートの診断結果")
    analyzer: TemplateReleaseAnalyzerReport | None = Field(
        default=None, description="Analyzer メトリクスの比較結果"
    )
