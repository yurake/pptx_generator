"""Markdownファイルから組織図用のJSONを生成する。

入力形式:
    ## SMBC
    # プロジェクトオーナー兼ビジネスオーナー
    〇〇部
    # PMO
    システム統括部

出力JSON:
    {
      "meta": {"title": "組織図", "generated_at": "..."},
      "categories": [
        {
          "name": "SMBC",
          "color": "light_green",
          "box_title_color": "green",
          "groups": [
            {"title": "プロジェクトオーナー兼ビジネスオーナー", "members": ["〇〇部"]},
            {"title": "PMO", "members": ["システム統括部"]}
          ]
        }
      ]
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from organization.models import (
    OrganizationCategory,
    OrganizationChart,
    OrganizationChartMeta,
    OrganizationGroup,
)


def parse_organization_markdown(
    md_path: str | Path,
    *,
    title: str | None = None,
) -> OrganizationChart:
    """Markdownファイルから組織図構造を生成する。

    Args:
        md_path: 入力Markdownファイルパス
        title: 組織図タイトル（Noneの場合は"組織図"を使用）

    Returns:
        OrganizationChart: パースされた組織図構造

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: 不正なMarkdown形式の場合
    """
    md_path = Path(md_path)
    if not md_path.exists():
        msg = f"Markdownファイルが見つかりません: {md_path}"
        raise FileNotFoundError(msg)

    content = md_path.read_text(encoding="utf-8")
    chart_title = title or "組織図"

    categories = _parse_categories(content)

    if not categories:
        msg = "カテゴリーが見つかりません"
        raise ValueError(msg)

    meta = OrganizationChartMeta(
        title=chart_title,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    return OrganizationChart(
        meta=meta,
        categories=categories,
    )


def _parse_categories(content: str) -> list[OrganizationCategory]:
    """Markdown内容からカテゴリーリストを抽出する。"""
    categories: list[OrganizationCategory] = []
    current_category: str | None = None
    current_group: str | None = None
    current_members: list[str] = []
    current_groups: list[OrganizationGroup] = []

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # カテゴリー名（レベル2見出し）
        if line.startswith("## "):
            # 前のグループを保存
            if current_group and current_members:
                current_groups.append(
                    OrganizationGroup(title=current_group, members=current_members)
                )

            # 前のカテゴリーを保存
            if current_category and current_groups:
                color, box_title_color = _determine_colors(current_category)
                categories.append(
                    OrganizationCategory(
                        name=current_category,
                        groups=current_groups,
                        color=color,
                        box_title_color=box_title_color,
                    )
                )
                current_groups = []

            current_category = line[3:].strip()
            current_group = None
            current_members = []

        # グループ名（レベル1見出し）
        elif line.startswith("# "):
            # 前のグループを保存
            if current_group and current_members:
                current_groups.append(
                    OrganizationGroup(title=current_group, members=current_members)
                )

            current_group = line[2:].strip()
            current_members = []

        # メンバー名（通常のテキスト行）
        else:
            if current_group:
                # 「〇〇部」などのメンバー名として追加
                current_members.append(line)

    # 最後のグループとカテゴリーを保存
    if current_group and current_members:
        current_groups.append(
            OrganizationGroup(title=current_group, members=current_members)
        )
    if current_category and current_groups:
        color, box_title_color = _determine_colors(current_category)
        categories.append(
            OrganizationCategory(
                name=current_category,
                groups=current_groups,
                color=color,
                box_title_color=box_title_color,
            )
        )

    return categories


def _determine_colors(category_name: str) -> tuple[str, str]:
    """カテゴリー名から背景色とタイトルボックス色を決定する。

    Args:
        category_name: カテゴリー名

    Returns:
        (background_color, box_title_color): 背景色とタイトルボックス色のタプル
    """
    # カテゴリー名を正規化（大文字・小文字、空白を無視）
    normalized = category_name.upper().replace(" ", "")

    # SMBCを含む場合は明るい緑
    if "SMBC" in normalized:
        return ("light_green", "green")

    # 日本総研、JRIを含む場合は薄い青
    if "日本総研" in normalized or "JRI" in normalized or "総研" in normalized:
        return ("light_blue", "blue")

    # 開発ベンダー、ベンダーを含む場合は薄い青
    if "ベンダー" in normalized or "VENDOR" in normalized:
        return ("light_blue", "light_green")

    # デフォルト: 薄い青
    return ("light_blue", "blue")


def organization_to_dict(chart: OrganizationChart) -> dict:
    """OrganizationChartインスタンスを辞書形式に変換する。"""
    return chart.model_dump(mode="json")


def save_organization_json(chart: OrganizationChart, output_path: str | Path) -> None:
    """OrganizationChartインスタンスをJSONファイルとして保存する。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(chart.model_dump_json(indent=2), encoding="utf-8")
