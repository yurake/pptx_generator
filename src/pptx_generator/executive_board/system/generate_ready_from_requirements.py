#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.stage_shared import load_context, resolve_input_path


LAYOUT_SYSTEM_OVERVIEW = "3_system_layout-02"
DEFAULT_IMAGE = "./samples/compose/system_dependencies.png"


def _require_markers(text: str, markers: list[str]) -> None:
    missing = [m for m in markers if m not in text]
    if missing:
        raise ValueError(
            "input_sample.md の想定セクションが見つかりません: " + ", ".join(missing)
        )


def _build_payload(image_path: str) -> dict[str, Any]:
    return {
        "slides": [
            {
                "layout_id": LAYOUT_SYSTEM_OVERVIEW,
                "elements": {
                    "title": "２．システム対応概要",
                    "Date_dept": {
                        "text": "２０ＸＸ年Ｘ月Ｘ日\nＸＸ部門",
                    },
                    "Message_line": {
                        "text": "・APIゲートウェイ（Kong）による統一インターフェースで複数決済チャネルを一元管理\n・マイクロサービスアーキテクチャにより各機能を独立してスケーラブルに展開\n・Hyperledger Fabricブロックチェーンで取引の透明性と改ざん防止を実現",
                    },
                    "Image": {
                        "source": image_path,
                        "sizing": "fit",
                    },
                    "Items": {
                        "headers": ["No", "項目", "内容"],
                        "rows": [
                            ["1", "APIゲートウェイ層（Kong導入）", "・複数決済チャネルのルーティング設定（モバイル、WebUI、QRコード、非接触決済）\n・DDoS対策（レート制限、IP制限、HTTPS強制化）\n・JWT検証、OAuth2.0統合、APIキー認証\n・リアルタイムダッシュボード構築"],
                            ["2", "認証サービス（Keycloak）", "・OAuth2.0対応、生体認証API統合\n・MFA（多要素認証）実装\n・全マイクロサービス共通の認証基盤提供"],
                            ["3", "決済エンジン（Stripe Connect）", "・複数決済ゲートウェイ連携\n・1秒1,000件処理、200ms応答\n・トランザクション追跡・監視"],
                            ["4", "顧客管理サービス（Salesforce）", "・KYC自動化、GDPR対応\n・監査ログ記録\n・顧客属性管理"],
                            ["5", "ブロックチェーン統合（Hyperledger Fabric）", "・スマートコントラクト開発（Go言語）\n・複数ノード冗長化、マルチチャネル構成\n・トランザクション確認3秒以内、月1,000万件対応"],
                            ["6", "データベース層（MySQL + Redis）", "・決済データ永続保管、レプリケーション構成\n・セッション管理、キャッシング実装\n・日次自動バックアップ、RPO 1時間以内"],
                            ["7", "セキュリティ対策", "・WAF導入（OWASP Top10対策）\n・IDS/IPS導入（不正アクセス検知・遮断）\n・TLS 1.3通信暗号化、年2回ペネトレーションテスト"],
                        ],
                    },
                    "Image_title": {"text": "システム構成図"},
                    "Items_titile": {"text": "対応項目一覧"},
                },
                "meta": {
                    "section": "システム対応",
                    "page_no": 2,
                    "sources": ["system_architecture", "technical_survey"],
                    "fallback": "none",
                },
            },
        ],
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
    parser = argparse.ArgumentParser(description="requirements から system スライドを生成する")
    parser.add_argument("input", type=Path, nargs="?", default=None, help="requirements md または inputs.json のパス")
    parser.add_argument("output", type=Path, nargs="?", default=None, help="出力先 generate_ready.json")
    args = parser.parse_args()

    stage = os.environ.get("PPTX_STAGE", "").lower()
    input_path = args.input or Path("input/inputs.json")
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
        image_path = resolve_input_path(
            env_var="PPTX_DIAGRAM_PNG",
            inputs_key="diagram_png_path",
            context=context,
        )
    else:
        requirements_path = input_path
        image_path = Path(DEFAULT_IMAGE)

    text = requirements_path.read_text(encoding="utf-8")
    _require_markers(
        text,
        [
            "## システム構成図（サンプル）",
            "## システム対応概要（サンプル）",
            "## システム対応項目（サンプル）",
        ],
    )

    payload = _build_payload(str(image_path))
    merge_target = output_path if output_path.exists() else None
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
