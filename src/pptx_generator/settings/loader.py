"""Lazy-loading helpers for settings modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pathlib import Path

from .paths import find_config_path
from .rules import RulesConfig

__all__ = ["load_rules_config"]


@lru_cache(maxsize=None)
def load_rules_config(path: Path | str) -> RulesConfig:
    """Load and cache RulesConfig from the given path."""

    candidate = Path(path)
    package_root = Path(__file__).resolve().parent.parent
    packaged_pipeline = package_root / "config" / "pipeline_rules.json"
    packaged_legacy = package_root / "config" / "rules.json"

    # デフォルト指定（pipeline_rules.json / rules.json）はパッケージ同梱のみを参照する
    if candidate.name in {"pipeline_rules.json", "rules.json"} and (
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
    if candidate.name == "pipeline_rules.json":
        fallback_names.append(candidate.with_name("rules.json"))
    elif candidate.name == "rules.json":
        fallback_names.append(candidate.with_name("pipeline_rules.json"))

    for fallback in fallback_names:
        resolved_fallback = find_config_path(fallback)
        if resolved_fallback is not None:
            return RulesConfig.load(resolved_fallback)

    msg = f"RulesConfig の既定ファイルが見つかりませんでした: {candidate}"
    raise FileNotFoundError(msg)
