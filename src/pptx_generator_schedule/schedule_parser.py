"""Markdownファイルからスケジュールガントチャート用のJSONを生成する。

入力形式:
    ## プロジェクトA  
    # 仕様  
    開始: 1月第1週  
    終了: 1月第2週

出力JSON:
    {
      "meta": {"year": 2025, "title": "...", "start_month": 1, "end_month": 12},
      "projects": [
        {
          "name": "プロジェクトA",
          "tasks": [{"name": "仕様", "start": "2025-01-01", "end": "2025-01-08"}]
        }
      ]
    }
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ScheduleGantt, ScheduleMilestone, ScheduleProject, ScheduleTask


def parse_schedule_markdown(
    md_path: str | Path,
    *,
    year: int | None = None,
    title: str | None = None,
) -> ScheduleGantt:
    """Markdownファイルからスケジュールガントチャート構造を生成する。

    Args:
        md_path: 入力Markdownファイルパス
        year: 対象年（Noneの場合は現在年を使用）
        title: スケジュールタイトル（Noneの場合はファイル名を使用）

    Returns:
        ScheduleGantt: パースされたスケジュール構造

    Raises:
        ValueError: 不正なMarkdown形式の場合
    """
    md_path = Path(md_path)
    if not md_path.exists():
        msg = f"Markdownファイルが見つかりません: {md_path}"
        raise FileNotFoundError(msg)

    content = md_path.read_text(encoding="utf-8")
    target_year = year or datetime.now().year
    schedule_title = title or md_path.stem

    # プロジェクトとマイルストーンを分離
    project_content, milestone_content = _split_content(content)

    projects = _parse_projects(project_content, target_year)

    if not projects:
        msg = "プロジェクトが見つかりません"
        raise ValueError(msg)

    # マイルストーンを解析
    milestones = _parse_milestones(milestone_content, target_year)

    # 全タスクの日付範囲から開始年・終了年・開始月・終了月を計算
    all_dates = []
    for project in projects:
        for task in project.tasks:
            all_dates.append(datetime.strptime(task.start, "%Y-%m-%d"))
            all_dates.append(datetime.strptime(task.end, "%Y-%m-%d"))

    min_date = min(all_dates)
    max_date = max(all_dates)

    start_year = min_date.year
    end_year = max_date.year
    start_month = min_date.month
    end_month = max_date.month

    meta_dict = {
        "year": start_year,
        "title": schedule_title,
        "start_month": start_month,
        "end_month": end_month,
        "milestones": milestones,
    }

    # 終了年が開始年と異なる場合のみend_yearを設定
    if end_year != start_year:
        meta_dict["end_year"] = end_year

    return ScheduleGantt(
        meta=meta_dict,
        projects=projects,
    )


def _parse_projects(content: str, year: int) -> list[ScheduleProject]:
    """Markdown内容からプロジェクトリストを抽出する。

    月の順序が逆転する場合（例: 11月→1月）は年を跨ぐと判定する。
    """
    projects: list[ScheduleProject] = []
    current_project: str | None = None
    current_task: str | None = None
    task_start: str | None = None
    task_start_month: int | None = None
    task_start_year: int | None = None
    task_end: str | None = None
    current_tasks: list[ScheduleTask] = []

    # 年を跨ぐかを判定するための前の月を記録
    previous_month: int | None = None
    current_year = year

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # プロジェクト名（レベル2見出し）
        if line.startswith("## "):
            # 前のタスクを保存（未完成でも）
            if current_task and task_start and task_end:
                current_tasks.append(
                    ScheduleTask(name=current_task, start=task_start, end=task_end)
                )

            # 前のプロジェクトを保存
            if current_project and current_tasks:
                projects.append(
                    ScheduleProject(name=current_project, tasks=current_tasks)
                )
                current_tasks = []

            # プロジェクト名から「第X年度：」を除去
            project_name = line[3:].strip()
            project_name = re.sub(r"^第\d+年度[：:]\s*", "", project_name)
            current_project = project_name
            current_task = None
            task_start = None
            task_start_month = None
            task_start_year = None
            task_end = None

        # タスク名（レベル1見出し）
        elif line.startswith("# "):
            # 前のタスクを保存
            if current_task and task_start and task_end:
                current_tasks.append(
                    ScheduleTask(name=current_task, start=task_start, end=task_end)
                )

            current_task = line[2:].strip()
            task_start = None
            task_start_month = None
            task_start_year = None
            task_end = None

        # 開始日
        elif line.startswith("開始:"):
            date_str = line.split(":", 1)[1].strip()

            # 年度形式の場合は、日付文字列から年度を直接抽出
            if "年度" in date_str:
                start_date = _parse_japanese_date(date_str, current_year)
                # 実際の年月を取得
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                start_month = start_date_obj.month
                task_start_year = start_date_obj.year
            else:
                # 週形式の場合は従来の処理
                start_date = _parse_japanese_date(date_str, current_year)
                start_month = int(start_date.split("-")[1])

                # 前の月より現在の月が小さい場合は年を跨いだと判定
                if previous_month is not None and start_month < previous_month:
                    current_year += 1
                    start_date = _parse_japanese_date(date_str, current_year)

                task_start_year = current_year

            task_start = start_date
            task_start_month = start_month
            previous_month = start_month

        # 終了日
        elif line.startswith("終了:"):
            date_str = line.split(":", 1)[1].strip()

            # 月を抽出（年度形式と週形式の両方に対応）
            # "YYYY年度MM月" または "MM月第Y週" から月を抽出
            month_match = re.search(r"(\d+)月", date_str)
            if month_match:
                end_month_num = int(month_match.group(1))
            else:
                # 月が抽出できない場合はエラー
                msg = f"終了日から月を抽出できません: {date_str}"
                raise ValueError(msg)

            # 終了月が開始月より小さい場合、年を跨ぐ（週形式の場合のみ）
            # 年度形式の場合は、_parse_japanese_date内で年度から実際の年が計算される
            if "年度" not in date_str:
                end_year = (
                    task_start_year if task_start_year is not None else current_year
                )
                if task_start_month is not None and end_month_num < task_start_month:
                    end_year += 1
                task_end = _parse_japanese_date(date_str, end_year)
                previous_month = end_month_num
                current_year = end_year
            else:
                # 年度形式の場合は、年を渡さなくても日付文字列から年度を抽出
                task_end = _parse_japanese_date(date_str, current_year)
                # 年度形式から実際の年月を取得して previous_month を更新
                end_date_obj = datetime.strptime(task_end, "%Y-%m-%d")
                previous_month = end_date_obj.month
                current_year = end_date_obj.year

    # 最後のタスクとプロジェクトを保存
    if current_task and task_start and task_end:
        current_tasks.append(
            ScheduleTask(name=current_task, start=task_start, end=task_end)
        )
    if current_project and current_tasks:
        projects.append(ScheduleProject(name=current_project, tasks=current_tasks))

    return projects


def _split_content(content: str) -> tuple[str, str]:
    """マークダウン内容をプロジェクト部分とマイルストーン部分に分割する。

    Args:
        content: マークダウン全体の内容

    Returns:
        (project_content, milestone_content): プロジェクト部分とマイルストーン部分
    """
    lines = content.split("\n")
    separator_index = None

    # '---' を探す
    for i, line in enumerate(lines):
        if line.strip() == "---":
            separator_index = i
            break

    if separator_index is None:
        # セパレータがない場合は全てプロジェクト
        return (content, "")

    project_content = "\n".join(lines[:separator_index])
    milestone_content = "\n".join(lines[separator_index + 1 :])

    return (project_content, milestone_content)


def _parse_milestones(content: str, year: int) -> list[ScheduleMilestone]:
    """マイルストーンセクションを解析する。

    Args:
        content: マイルストーン部分の内容
        year: 開始年

    Returns:
        マイルストーンのリスト
    """
    if not content.strip():
        return []

    milestones: list[ScheduleMilestone] = []
    in_milestone_section = False
    current_year = year
    previous_month: int | None = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # マイルストーンセクションの開始
        if line.startswith("# マイルストーン"):
            in_milestone_section = True
            continue

        if not in_milestone_section:
            continue

        # マイルストーン行: "名前: X月第Y週" または "名前: YYYY年度MM月"
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                date_str = parts[1].strip()

                # 年度形式かどうかを確認
                is_fiscal_year_format = "年度" in date_str

                # 月を抽出
                month_match = re.search(r"(\d+)月", date_str)
                if month_match:
                    month = int(month_match.group(1))

                    # 週形式の場合のみ年跨ぎを判定
                    if not is_fiscal_year_format:
                        # 前の月より現在の月が小さい場合は年を跨いだと判定
                        if previous_month is not None and month < previous_month:
                            current_year += 1

                    # 日付を解析
                    try:
                        date_iso = _parse_japanese_date(date_str, current_year)
                        milestones.append(ScheduleMilestone(name=name, date=date_iso))

                        # 年度形式の場合は実際の年月を取得してprevious_monthを更新
                        if is_fiscal_year_format:
                            date_obj = datetime.strptime(date_iso, "%Y-%m-%d")
                            previous_month = date_obj.month
                            current_year = date_obj.year
                        else:
                            previous_month = month
                    except ValueError:
                        # 解析エラーはスキップ
                        pass

    return milestones


def _parse_japanese_date(date_str: str, year: int) -> str:
    """日本語日付形式をISO 8601形式に変換する。

    Args:
        date_str: 日本語日付文字列（例: "2024年度4月", "1月第1週"）
        year: デフォルト年（年度形式の場合は無視される）

    Returns:
        str: ISO 8601形式の日付（YYYY-MM-DD）

    Raises:
        ValueError: 不正な日付形式の場合
    """
    # パターン1: "YYYY年度MM月" 形式
    fiscal_pattern = r"(\d{4})年度(\d+)月"
    fiscal_match = re.match(fiscal_pattern, date_str)

    if fiscal_match:
        fiscal_year = int(fiscal_match.group(1))
        month = int(fiscal_match.group(2))

        if not 1 <= month <= 12:
            msg = f"月が範囲外です: {month} (1-12)"
            raise ValueError(msg)

        # 年度の計算（4月始まり）
        # 4月～12月: 年度と同じ年
        # 1月～3月: 年度+1年
        if 4 <= month <= 12:
            actual_year = fiscal_year
        else:  # 1-3月
            actual_year = fiscal_year + 1

        # 月初（1日）を返す
        try:
            date_obj = datetime(actual_year, month, 1)
        except ValueError as exc:
            msg = f"無効な日付です: {actual_year}-{month:02d}-01"
            raise ValueError(msg) from exc

        return date_obj.strftime("%Y-%m-%d")

    # パターン2: "X月第Y週" 形式（従来の形式）
    week_pattern = r"(\d+)月第(\d+)週"
    week_match = re.match(week_pattern, date_str)

    if week_match:
        month = int(week_match.group(1))
        week = int(week_match.group(2))

        if not 1 <= month <= 12:
            msg = f"月が範囲外です: {month} (1-12)"
            raise ValueError(msg)

        if not 1 <= week <= 5:
            msg = f"週が範囲外です: {week} (1-5)"
            raise ValueError(msg)

        # 月初を基準に週番号×7日でオフセット
        day_offset = (week - 1) * 7 + 1
        try:
            date_obj = datetime(year, month, day_offset)
        except ValueError as exc:
            msg = f"無効な日付です: {year}-{month:02d}-{day_offset:02d}"
            raise ValueError(msg) from exc

        return date_obj.strftime("%Y-%m-%d")

    # どちらの形式にも一致しない場合
    msg = f"日付形式が不正です: {date_str} (期待: YYYY年度MM月 または X月第Y週)"
    raise ValueError(msg)


def schedule_to_dict(schedule: ScheduleGantt) -> dict[str, Any]:
    """ScheduleGanttインスタンスを辞書形式に変換する。"""
    return schedule.model_dump(mode="json")


def save_schedule_json(schedule: ScheduleGantt, output_path: str | Path) -> None:
    """ScheduleGanttインスタンスをJSONファイルとして保存する。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(schedule.model_dump_json(indent=2), encoding="utf-8")