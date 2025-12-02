"""テンプレートリリース関連モデル。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "TemplateReleaseLayoutDetail",
    "TemplateReleaseLayouts",
    "TemplateReleaseDiagnostics",
    "TemplateReleaseGoldenRun",
    "TemplateReleaseAnalyzerIssueSummary",
    "TemplateReleaseAnalyzerFixSummary",
    "TemplateReleaseAnalyzerRunMetrics",
    "TemplateReleaseAnalyzerSummary",
    "TemplateReleaseAnalyzerMetrics",
    "TemplateReleaseAnalyzerSummaryDelta",
    "TemplateReleaseAnalyzerReport",
    "TemplateReleaseEnvironment",
    "TemplateReleaseSummary",
    "TemplateReleaseSummaryDelta",
    "TemplateRelease",
    "TemplateReleaseLayoutDiff",
    "TemplateReleaseChanges",
    "TemplateReleaseReport",
]


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
    by_type: dict[str, int] = Field(default_factory=dict, description="issue type ごとの件数")
    by_severity: dict[str, int] = Field(default_factory=dict, description="severity ごとの件数")


class TemplateReleaseAnalyzerFixSummary(BaseModel):
    """Analyzer が提示した修正案の件数サマリ。"""

    total: int = Field(0, description="修正案件数合計")
    by_type: dict[str, int] = Field(default_factory=dict, description="fix type ごとの件数")


class TemplateReleaseAnalyzerRunMetrics(BaseModel):
    """ゴールデンサンプル単位の Analyzer メトリクス。"""

    spec_path: str = Field(..., description="対象となった spec ファイルパス")
    status: Literal["included", "skipped"] = Field(..., description="集計に含めたかどうか")
    issues: TemplateReleaseAnalyzerIssueSummary = Field(..., description="指摘サマリ")
    fixes: TemplateReleaseAnalyzerFixSummary = Field(..., description="修正案サマリ")


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
    runs: list[TemplateReleaseAnalyzerRunMetrics] = Field(default_factory=list, description="各ゴールデンサンプルのメトリクス")
    summary: TemplateReleaseAnalyzerSummary = Field(
        default_factory=TemplateReleaseAnalyzerSummary,
        description="集計サマリ",
    )


class TemplateReleaseAnalyzerSummaryDelta(BaseModel):
    """Analyzer メトリクスの差分サマリ。"""

    issues: dict[str, int] = Field(default_factory=dict, description="issue type ごとの件数差分")
    severity: dict[str, int] = Field(default_factory=dict, description="severity ごとの件数差分")
    fixes: dict[str, int] = Field(default_factory=dict, description="fix type ごとの件数差分")
    total_issue_change: int = Field(0, description="指摘件数合計の差分（current - baseline）")
    total_fix_change: int = Field(0, description="修正案件数合計の差分（current - baseline）")


class TemplateReleaseAnalyzerReport(BaseModel):
    """リリースレポートに含める Analyzer メトリクスの比較。"""

    current: TemplateReleaseAnalyzerSummary = Field(..., description="現在バージョンの Analyzer サマリ")
    baseline: TemplateReleaseAnalyzerSummary | None = Field(None, description="比較元バージョンの Analyzer サマリ")
    delta: TemplateReleaseAnalyzerSummaryDelta | None = Field(None, description="差分サマリ")


class TemplateReleaseEnvironment(BaseModel):
    """リリース生成時の実行環境メタ情報。"""

    python_version: str = Field(..., description="Python のバージョン")
    platform: str = Field(..., description="OS / プラットフォーム情報")
    pptx_generator_version: str = Field(..., description="pptx-generator CLI のバージョン")
    libreoffice_version: str | None = Field(None, description="LibreOffice (soffice) のバージョン")
    dotnet_sdk_version: str | None = Field(None, description=".NET SDK のバージョン")


class TemplateReleaseSummary(BaseModel):
    """テンプレートリリースの品質サマリ。"""

    layouts: int = Field(..., description="レイアウト総数")
    anchors: int = Field(..., description="アンカー総数")
    placeholders: int = Field(..., description="プレースホルダー総数")
    warning_count: int = Field(..., description="警告件数")
    error_count: int = Field(..., description="エラー件数")
    analyzer_issue_total: int | None = Field(None, description="Analyzer の指摘件数合計")
    analyzer_fix_total: int | None = Field(None, description="Analyzer の修正提案件数合計")


class TemplateReleaseSummaryDelta(BaseModel):
    """テンプレートリリースサマリの差分。"""

    layouts: int = Field(..., description="レイアウト数の差分")
    anchors: int = Field(..., description="アンカー数の差分")
    placeholders: int = Field(..., description="プレースホルダー数の差分")
    warning_count: int = Field(..., description="警告件数の差分")
    error_count: int = Field(..., description="エラー件数の差分")
    analyzer_issue_total: int | None = Field(None, description="Analyzer 指摘件数の差分")
    analyzer_fix_total: int | None = Field(None, description="Analyzer 修正提案件数の差分")


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
    extractor: dict[str, str] | None = Field(default=None, description="抽出処理に関するメタ情報")
    layouts: TemplateReleaseLayouts = Field(..., description="レイアウトの統計情報")
    diagnostics: TemplateReleaseDiagnostics = Field(..., description="診断結果")
    analyzer_metrics: TemplateReleaseAnalyzerMetrics | None = Field(
        default=None, description="Analyzer 出力に基づく監査メトリクス"
    )
    golden_runs: list[TemplateReleaseGoldenRun] = Field(default_factory=list, description="ゴールデンサンプル検証の結果一覧")
    summary: TemplateReleaseSummary = Field(..., description="品質メトリクスのサマリ")
    environment: TemplateReleaseEnvironment = Field(..., description="実行環境メタ情報")


class TemplateReleaseLayoutDiff(BaseModel):
    """レイアウト単位の差分情報。"""

    name: str = Field(..., description="レイアウト名")
    anchors_added: list[str] = Field(default_factory=list, description="追加されたアンカー名")
    anchors_removed: list[str] = Field(default_factory=list, description="削除されたアンカー名")
    placeholders_added: list[str] = Field(default_factory=list, description="追加されたプレースホルダー名")
    placeholders_removed: list[str] = Field(default_factory=list, description="削除されたプレースホルダー名")
    duplicate_anchor_names: list[str] = Field(default_factory=list, description="現在のレイアウトで検出された重複アンカー名")


class TemplateReleaseChanges(BaseModel):
    """テンプレートリリース間の差分サマリ。"""

    layouts_added: list[str] = Field(default_factory=list, description="追加されたレイアウト名")
    layouts_removed: list[str] = Field(default_factory=list, description="削除されたレイアウト名")
    layout_diffs: list[TemplateReleaseLayoutDiff] = Field(default_factory=list, description="差分が発生したレイアウトの詳細")


class TemplateReleaseReport(BaseModel):
    """テンプレートリリース差分レポート。"""

    template_id: str = Field(..., description="比較対象のテンプレート識別子")
    baseline_id: str | None = Field(None, description="比較元テンプレート識別子")
    generated_at: str = Field(..., description="レポート生成日時（ISO8601）")
    hashes: dict[str, str | None] = Field(..., description="現在およびベースラインのハッシュ値")
    changes: TemplateReleaseChanges = Field(..., description="差分サマリ")
    diagnostics: TemplateReleaseDiagnostics = Field(..., description="現在テンプレートの診断結果")
    analyzer: TemplateReleaseAnalyzerReport | None = Field(
        default=None, description="Analyzer メトリクスの比較結果"
    )
    summary: TemplateReleaseSummary | None = Field(
        default=None, description="現在テンプレートの品質サマリ"
    )
    summary_baseline: TemplateReleaseSummary | None = Field(
        default=None, description="ベースラインテンプレートの品質サマリ"
    )
    summary_delta: TemplateReleaseSummaryDelta | None = Field(
        default=None, description="品質サマリの差分"
    )
