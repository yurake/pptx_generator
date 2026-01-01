"""テンプレート ID の導出・抽出ユーティリティ。"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

import logging

logger = logging.getLogger(__name__)


class TemplateIdExtractionError(RuntimeError):
    """template_id 抽出に失敗した際の例外。"""

    def __init__(self, *, path: Path, reason: str) -> None:
        super().__init__(reason)
        self.path = path
        self.reason = reason

    def format_user_message(self) -> str:
        return f"template_id の抽出に失敗しました: {self.reason} (path={self.path})"


def derive_template_id_from_template_path(path: Path) -> str:
    """PPTX ファイルパスからテンプレート ID を導出する。

    `template stage` で使用しているロジックと同一の正規化を行う。
    """
    stem = unicodedata.normalize("NFKC", path.stem)
    stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
    return stem or "template"


def extract_template_id_from_json_file(
    path: Path, *, strict: bool = False, require_id: bool = False
) -> str | None:
    """JSON ファイル内から template_id を抽出する。

    jobspec / generate_ready / template_spec など複数の候補フィールドを走査する。

    strict=True の場合はファイル欠落や JSON 不正時に TemplateIdExtractionError を送出し、
    呼び出し元で一貫したエラー処理を行えるようにする。
    require_id=True を指定すると template_id が存在しない場合にも TemplateIdExtractionError を送出する。
    """
    try:
        payload = _load_json(path)
    except TemplateIdExtractionError:
        if strict:
            raise
        logger.debug("template_id 抽出対象のファイルを読み込めません: %s", path)
        return None

    template_id = _search_template_id(payload)
    if template_id:
        return template_id

    if require_id:
        if strict:
            raise TemplateIdExtractionError(path=path, reason="template_id が見つかりません")
        return None
    return None


def _load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TemplateIdExtractionError(path=path, reason="ファイルが存在しません") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise TemplateIdExtractionError(path=path, reason=f"JSON が不正です: {exc}") from exc


def _search_template_id(payload: Any) -> str | None:
    """辞書・リスト内を深さ優先で走査して template_id を探す（優先順位: top > meta > template_style > その他）。"""

    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            direct = _extract_direct_template_id(current)
            if direct:
                return direct

            meta = current.get("meta")
            meta_direct = _extract_direct_template_id(meta) if isinstance(meta, dict) else None
            if meta_direct:
                return meta_direct

            template_style = current.get("template_style")
            style_direct = (
                _extract_direct_template_id(template_style) if isinstance(template_style, dict) else None
            )
            if style_direct:
                return style_direct

            if isinstance(meta, dict):
                stack.append(meta)
            if isinstance(template_style, dict):
                stack.append(template_style)

            for value in current.values():
                if value is meta or value is template_style:
                    continue
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)

    return None


def _extract_direct_template_id(mapping: Mapping[str, Any] | None) -> str | None:
    if not mapping:
        return None

    return _normalize_template_id(mapping.get("template_id"))


def _normalize_template_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None
