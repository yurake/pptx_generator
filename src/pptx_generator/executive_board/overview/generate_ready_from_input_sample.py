#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.stage_shared import load_context, resolve_input_path


def _require_markers(text: str, markers: list[str]) -> None:
    missing = [m for m in markers if m not in text]
    if missing:
        raise ValueError(
            "input_sample.md の想定セクションが見つかりません: " + ", ".join(missing)
        )


TEMPLATE_PATH = "templates/executive_board.pptx"
LAYOUT_PROJECT_BACKGROUND = "project_background_layout-01"
DEFAULT_INPUT_SAMPLE = Path("input/inputs.json")
DEFAULT_IMAGE = "./samples/compose/system_dependencies.png"


def _build_generated_payload() -> dict:
    return {
        "slides": [
            {
                "layout_id": LAYOUT_PROJECT_BACKGROUND,
                "elements": {
                    "title": "１．案件の背景",
                    "Date_dept": {
                        "text": "２０ＸＸ年Ｘ月Ｘ日\nＸＸ部門",
                    },
                    "Message_line": {
                        "text": "・モバイル中心の新規ユーザーニーズに既存決済システムが対応できず、市場競争力が低下している\n・モバイル決済、QRコード決済、非接触型決済に対応した新システムを構築し、顧客利便性と競争力を強化する",
                    },
                    "Problem_title": {"text": "課題"},
                    "Problem_Message_line": {
                        "text": "既存決済システムの機能不足により、キャッシュレス決済市場での競争力低下と顧客離れが発生",
                    },
                    "Problem": {
                        "headers": ["項目", "課題"],
                        "rows": [
                            ["顧客体験", "・モバイル決済、QRコード決済、非接触型決済に未対応\n・利便性の低さによる顧客満足度低下"],
                            ["業務", "・既存システムの老朽化による保守コスト増大\n・手作業が多く業務効率が低い"],
                            ["収益性", "・市場シェア低下による収益減少\n・競合他社（PayPay、LINE Pay等）への顧客流出"],
                            ["技術", "・ブロックチェーン技術未導入によるセキュリティ透明性不足\n・レガシーアーキテクチャによる拡張性限界"],
                            ["法規制", "・PCI DSS準拠への対応が不十分\n・個人情報保護法への完全対応が必要"],
                        ],
                    },
                    "Solusion_title": {"text": "対応方針"},
                    "Solusion_Message_line": {
                        "text": "クラウドネイティブなマイクロサービスアーキテクチャとブロックチェーン技術を採用し、セキュリティと拡張性を強化",
                    },
                    "Solusion": {
                        "text": "・1秒あたり1,000トランザクション処理、応答時間200ms以内、可用性99.99%を実現\n・APIゲートウェイ（Kong）により4つの決済チャネル（モバイル、Web、QR、非接触）を統合管理\n・Hyperledger Fabricによるブロックチェーン統合で月1,000万件の取引記録を改ざん防止\n・予算5億円、期間18ヶ月で開発（人件費3億円、システム構築費1.5億円、その他0.5億円）",
                    },
                },
                "meta": {
                    "section": "背景",
                    "page_no": 1,
                    "sources": ["project_plan", "requirements", "market_research"],
                    "fallback": "none",
                },
            },
        ],
        "meta": {
            "template_path": TEMPLATE_PATH,
            "content_hash": "neobank_payment_system",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "job_meta": {
                "schema_version": "1.1",
                "title": "ネオバンク向け決済システム刷新",
                "client": "ネオバンク",
                "author": "システム企画部",
                "created_at": "2025-12-04",
                "theme": "corporate",
                "locale": "ja-JP",
            },
            "job_auth": {
                "created_by": "pptx_generator",
                "department": "information_systems",
            },
        },
    }


def _merge_slides(base: dict, replacement: dict) -> dict:
    base_slides = base.get("slides") if isinstance(base.get("slides"), list) else []
    replacement_slides = replacement.get("slides") if isinstance(replacement.get("slides"), list) else []
    replacement_map = {slide.get("layout_id"): slide for slide in replacement_slides}
    used = set()

    merged = []
    for slide in base_slides:
        layout_id = slide.get("layout_id")
        if layout_id in replacement_map:
            merged.append(replacement_map[layout_id])
            used.add(layout_id)
        else:
            merged.append(slide)

    missing = [slide for slide in replacement_slides if slide.get("layout_id") not in used]
    if missing:
        merged = missing + merged

    base["slides"] = merged
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="input_sample.md から generate_ready.json を生成する")
    parser.add_argument("input", type=Path, nargs="?", default=None, help="input_sample.md のパス")
    parser.add_argument("output", type=Path, nargs="?", default=None, help="出力先 generate_ready.json")
    parser.add_argument(
        "--merge-with",
        type=Path,
        default=None,
        help="既存の generate_ready.json を読み込んで先頭2枚を差し替える",
    )
    args = parser.parse_args()

    stage = os.environ.get("PPTX_STAGE", "").lower()
    input_path = args.input or DEFAULT_INPUT_SAMPLE
    output_path = args.output or Path(os.environ.get("PPTX_GENERATE_READY_PATH", ""))
    if not args.output and stage == "prepare":
        output_path = Path(os.environ.get("PPTX_PREPARE_OUTPUT_DIR", ".pptx/prepare")) / "overview_generate_ready.json"
    if not args.output and stage == "compose":
        output_path = Path(os.environ.get("PPTX_GENERATE_READY_PATH", ""))
    if not output_path:
        raise ValueError("output が指定されていません。引数または PPTX_GENERATE_READY_PATH を設定してください。")

    if not input_path.is_absolute() and not input_path.exists():
        base_path = os.environ.get("PPTX_GENERATE_READY_PATH")
        if base_path:
            repo_root = Path(base_path).resolve().parent.parent.parent
            input_path = (repo_root / input_path).resolve()
        else:
            repo_root = Path(__file__).resolve().parents[3]
            input_path = (repo_root / input_path).resolve()

    if input_path.suffix == ".json":
        context = load_context()
        requirements_path = resolve_input_path(
            env_var="PPTX_REQUIREMENTS_MD",
            inputs_key="requirements_md_path",
            context=context,
        )
    else:
        requirements_path = input_path

    text = requirements_path.read_text(encoding="utf-8")
    _require_markers(
        text,
        [
            "# 案件名：",
            "## プロジェクト計画書（サンプル）",
        ],
    )

    payload = _build_generated_payload()

    merge_target = args.merge_with or (output_path if output_path.exists() else None)
    if merge_target and merge_target.exists():
        base_payload = json.loads(merge_target.read_text(encoding="utf-8"))
        payload = _merge_slides(base_payload, payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
