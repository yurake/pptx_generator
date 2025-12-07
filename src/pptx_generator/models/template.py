"""テンプレート仕様関連モデル。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import FontSpec, TextCapacity, TextFramePadding, TextboxParagraph

__all__ = [
    "ShapeInfo",
    "LayoutInfo",
    "TemplateBlueprintSlot",
    "TemplateBlueprintSlide",
    "TemplateBlueprint",
    "TemplateSpec",
]


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
    font: FontSpec | None = Field(None, description="テンプレートが指定するフォント情報")
    paragraph: TextboxParagraph | None = Field(None, description="段落設定")
    text_frame_padding: TextFramePadding | None = Field(None, description="テキスト枠の余白")
    text_capacity: TextCapacity | None = Field(None, description="推定文字許容量")


class LayoutInfo(BaseModel):
    """レイアウト情報を表現するモデル。"""

    name: str = Field(..., description="レイアウト名")
    identifier: str | None = Field(None, description="レイアウト固有識別子")
    anchors: list[ShapeInfo] = Field(default_factory=list, description="図形・プレースホルダー一覧")
    error: str | None = Field(None, description="レイアウト抽出時のエラー")
    prototype_index: int | None = Field(
        None, description="実スライド抽出時に対応するテンプレートスライドの連番（1始まり）"
    )
    placeholder_summary: dict[str, Any] | None = Field(
        None, description="プレースホルダー統計情報"
    )
    heuristic: dict[str, Any] | None = Field(
        None, description="用途タグ推定のヒューリスティック結果"
    )
    layout_description: dict[str, Any] | None = Field(
        None, description="レイアウト構造の概要と要素一覧"
    )


class TemplateBlueprintSlot(BaseModel):
    """Blueprint 上の slot 情報。"""

    slot_id: str = Field(..., description="Blueprint 上の一意な slot ID")
    anchor: str = Field(..., description="紐付け先のアンカー名")
    content_type: Literal["text", "image", "table", "chart", "shape", "other"] = Field(
        ..., description="slot に期待するコンテンツ種別"
    )
    required: bool = Field(True, description="必須 slot かどうか")
    intent_tags: list[str] = Field(default_factory=list, description="意図タグ（プロンプト補助用）")
    default_text: list[str] | None = Field(
        None,
        description="静的テンプレートが提示する既定テキスト行",
    )
    default_payload: dict[str, Any] | None = Field(
        None,
        description="テキスト以外の要素向け既定ペイロード",
    )


class TemplateBlueprintSlide(BaseModel):
    """Blueprint 上のスライド情報。"""

    slide_id: str = Field(..., description="Blueprint 上のスライド ID")
    layout: str = Field(..., description="利用するレイアウト名")
    prototype_index: int | None = Field(
        None, description="実スライド抽出時に参照するテンプレートスライドの連番（1始まり）"
    )
    required: bool = Field(True, description="必須スライドかどうか")
    intent_tags: list[str] = Field(default_factory=list, description="スライド意図タグ")
    slots: list[TemplateBlueprintSlot] = Field(default_factory=list, description="slot 一覧")


class TemplateBlueprint(BaseModel):
    """テンプレートの Blueprint 定義。"""

    slides: list[TemplateBlueprintSlide] = Field(default_factory=list, description="Blueprint スライド一覧")


class TemplateSpec(BaseModel):
    """テンプレート仕様全体を表現するモデル。"""

    template_path: str = Field(..., description="テンプレートファイルパス")
    extracted_at: str = Field(..., description="抽出日時（ISO8601）")
    template_source: Literal["slide", "template"] = Field(
        "template",
        description="テンプレ抽出のソース。静的モードで実スライドを利用した場合は 'slide'。",
    )
    layouts: list[LayoutInfo] = Field(default_factory=list, description="レイアウト一覧")
    warnings: list[str] = Field(default_factory=list, description="警告メッセージ")
    errors: list[str] = Field(default_factory=list, description="エラーメッセージ")
    layout_mode: Literal["dynamic", "static"] = Field(
        "dynamic", description="テンプレートの運用モード"
    )
    blueprint: TemplateBlueprint | None = Field(
        None, description="静的テンプレート向け Blueprint 定義"
    )
