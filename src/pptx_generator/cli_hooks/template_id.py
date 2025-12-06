"""テンプレート ID の導出・抽出ユーティリティ。"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)


def derive_template_id_from_template_path(path: Path) -> str:
    """PPTX ファイルパスからテンプレート ID を導出する。

    `template stage` で使用しているロジックと同一の正規化を行う。
    """
    stem = unicodedata.normalize("NFKC", path.stem)
    stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
    return stem or "template"


def extract_template_id_from_json_file(path: Path) -> str | None:
    """JSON ファイル内から template_id を抽出する。

    jobspec / generate_ready / template_spec など複数の候補フィールドを走査する。
    """
    try:
        text = path.read_text(encoding="utf-8")
        data: Any = json.loads(text)
    except FileNotFoundError:
        logger.debug("template_id 抽出対象のファイルが見つかりません: %s", path)
        return None
    except json.JSONDecodeError as exc:
        logger.debug("template_id 抽出対象の JSON 読み込みに失敗: %s (%s)", path, exc)
        return None

    return _search_template_id(data)


def _search_template_id(payload: Any) -> str | None:
    """辞書・リスト内を深さ優先で走査して template_id を探す。"""
    if isinstance(payload, dict):
        # 直接的なフィールド名を優先
        direct = payload.get("template_id")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        # meta 下に格納されているケース
        meta = payload.get("meta")
        if isinstance(meta, dict):
            direct = meta.get("template_id")
            if isinstance(direct, str) and direct.strip():
                return direct.strip()

        # blueprint や template_style などに含まれているケース
        template_style = payload.get("template_style")
        if isinstance(template_style, dict):
            direct = template_style.get("template_id")
            if isinstance(direct, str) and direct.strip():
                return direct.strip()

        # その他のネストを探索
        for value in payload.values():
            result = _search_template_id(value)
            if result:
                return result

    elif isinstance(payload, list):
        for item in payload:
            result = _search_template_id(item)
            if result:
                return result

    return None
