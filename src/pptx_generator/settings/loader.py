"""Lazy-loading helpers for settings modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .paths import find_config_path
from .rules import RulesConfig

PIPELINE_RULES_FILENAME = "pipeline_rules.json"
LEGACY_RULES_FILENAME = "rules.json"

__all__ = ["load_rules_config"]


@lru_cache(maxsize=None)
def load_rules_config(path: Path | str) -> RulesConfig:
    """Load and cache RulesConfig from the given path."""

    candidate = Path(path)
    package_root = Path(__file__).resolve().parent.parent
    packaged_pipeline = package_root / "config" / PIPELINE_RULES_FILENAME
    packaged_legacy = package_root / "config" / LEGACY_RULES_FILENAME

    # デフォルト指定（pipeline_rules.json / rules.json）はパッケージ同梱のみを参照する
    if candidate.name in {PIPELINE_RULES_FILENAME, LEGACY_RULES_FILENAME} and (
        candidate.parent == Path("config") or candidate.parent == Path(".") or candidate.parent == Path()
    ):
        if packaged_pipeline.exists():
            return RulesConfig.load(packaged_pipeline)
        if packaged_legacy.exists():
            return RulesConfig.load(packaged_legacy)

    resolved = find_config_path(path)
    if resolved is not None:
        return RulesConfig.load(resolved)

    # 互換性維持: 明示的に旧名を指定された場合は新名へもフォールバック
    fallback_names = []
    if candidate.name == PIPELINE_RULES_FILENAME:
        fallback_names.append(candidate.with_name(LEGACY_RULES_FILENAME))
    elif candidate.name == LEGACY_RULES_FILENAME:
        fallback_names.append(candidate.with_name(PIPELINE_RULES_FILENAME))

    for fallback in fallback_names:
        resolved_fallback = find_config_path(fallback)
        if resolved_fallback is not None:
            return RulesConfig.load(resolved_fallback)

    msg = f"RulesConfig の既定ファイルが見つかりませんでした: {candidate}"
    raise FileNotFoundError(msg)
