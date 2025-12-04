"""外部フック設定ファイルのスキャフォールド生成。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .manager import EXTERNAL_ROOT, HOOKS_FILENAME, KNOWN_STAGES


def ensure_hook_skeleton(template_id: str, slide_keys: Iterable[str]) -> Path | None:
    """テンプレート ID に対応する hooks.json の骨組みを生成する。

    既にファイルが存在する場合は何もしない。
    """
    base_dir = EXTERNAL_ROOT / template_id
    config_path = base_dir / HOOKS_FILENAME
    if config_path.exists():
        return None

    base_dir.mkdir(parents=True, exist_ok=True)
    stage_section = {stage: None for stage in sorted(KNOWN_STAGES)}
    slides_section = {
        key: {stage: None for stage in sorted(KNOWN_STAGES)} for key in slide_keys
    }
    payload = {
        "stage": stage_section,
        "slides": slides_section,
    }
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path
