#!/usr/bin/env python3
"""Stage2 hook: 開発要員計画の JSON を生成する（AI パーサー対応）。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.stage_shared import load_context, persist_context, resolve_input_path  # noqa: E402


def _configure_sys_path() -> None:
    src_dir = Path(__file__).resolve().parents[3] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_configure_sys_path()

from schedule.schedule_parser import parse_schedule_markdown  # noqa: E402
from personnel.models import PersonnelData  # noqa: E402
from personnel_parser import (  # noqa: E402
    DevelopmentPersonnelPlan,
    integrate_personnel_schedule,
    save_development_personnel_plan,
    save_personnel_data,
    parse_personnel_xlsx,
)


DEFAULT_LAYOUT = "2_System_layout"


def _load_personnel_data_from_json(path: Path) -> PersonnelData:
    data = json.loads(path.read_text(encoding="utf-8"))
    return PersonnelData.model_validate(data)


def _load_plan_from_json(path: Path) -> DevelopmentPersonnelPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return DevelopmentPersonnelPlan.model_validate(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="personnel prepare hook for executive_board")
    parser.add_argument("--schedule-md", help="スケジュールMarkdown (PPTX_PERSONNEL_SCHEDULE_MD より優先)")
    parser.add_argument("--xlsx", help="工数xlsx (PPTX_PERSONNEL_XLSX より優先)")
    parser.add_argument("--output", help="出力ディレクトリ (PPTX_PREPARE_OUTPUT_DIR より優先)")
    args = parser.parse_args(argv)

    layout_mode = os.environ.get("PPTX_MODE", "").lower()
    if layout_mode and layout_mode != "static":
        return 0

    context = load_context()

    schedule_md = Path(args.schedule_md).expanduser().resolve() if args.schedule_md else resolve_input_path(
        env_var="PPTX_PERSONNEL_SCHEDULE_MD",
        inputs_key="personnel_schedule_md_path",
        context=context,
    )
    xlsx_path = Path(args.xlsx).expanduser().resolve() if args.xlsx else resolve_input_path(
        env_var="PPTX_PERSONNEL_XLSX",
        inputs_key="personnel_xlsx_path",
        context=context,
    )

    if not schedule_md.exists():
        raise FileNotFoundError(f"schedule markdown not found: {schedule_md}")
    if not xlsx_path.exists():
        raise FileNotFoundError(f"personnel xlsx not found: {xlsx_path}")

    output_dir_env = os.environ.get("PPTX_PREPARE_OUTPUT_DIR")
    output_dir = Path(args.output).expanduser() if args.output else Path(output_dir_env) if output_dir_env else Path(".pptx/prepare")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 入力のロード
    schedule_data = parse_schedule_markdown(schedule_md)

    personnel_data_env = os.environ.get("PPTX_PERSONNEL_DATA_JSON")
    personnel_data: PersonnelData | None = None
    if personnel_data_env:
        pd_path = Path(personnel_data_env).expanduser().resolve()
        if pd_path.exists():
            personnel_data = _load_personnel_data_from_json(pd_path)

    if personnel_data is None:
        # AI パーサーではなくローカルパーサーを使用
        personnel_data = parse_personnel_xlsx(xlsx_path)

    personnel_json = output_dir / "personnel_data.json"
    save_personnel_data(personnel_data, personnel_json)

    plan = integrate_personnel_schedule(
        schedule_data,
        personnel_data,
        schedule_source=str(schedule_md),
        personnel_source=str(xlsx_path),
    )
    plan_json = output_dir / "development_personnel_plan.json"
    save_development_personnel_plan(plan, plan_json)

    # コンテキスト更新
    context.update(
        {
            "personnel_schedule_md_path": str(schedule_md),
            "personnel_xlsx_path": str(xlsx_path),
            "personnel_data_path": str(personnel_json),
            "personnel_plan_path": str(plan_json),
            "personnel_layout": os.environ.get("PPTX_PERSONNEL_LAYOUT", DEFAULT_LAYOUT),
        }
    )
    persist_context(context)

    print(f"[stage02_prepare] personnel_data.json -> {personnel_json}")
    print(f"[stage02_prepare] development_personnel_plan.json -> {plan_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
