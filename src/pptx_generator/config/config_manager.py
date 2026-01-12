"""設定の優先度解決を担うユーティリティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

PriorityOrder = tuple[str, ...]


@dataclass(slots=True)
class ResolvedConfig:
    """最終的に採用された設定値とその出典を保持する。"""

    values: dict[str, Any]
    sources: dict[str, str]
    priority_order: PriorityOrder

    def get(self, key: str, default: Any | None = None) -> Any | None:
        return self.values.get(key, default)


class ConfigManager:
    """複数の設定ソースを優先度付きで扱うマネージャ。"""

    DEFAULT_PRIORITY: PriorityOrder = (
        "cli_options",
        "env_variables",
        "project_config",
        "template_config",
        "defaults",
    )

    def __init__(self, priority_order: PriorityOrder | None = None) -> None:
        self.priority_order: PriorityOrder = priority_order or self.DEFAULT_PRIORITY
        self._sources: dict[str, dict[str, Any]] = {name: {} for name in self.priority_order}
        self._resolved: dict[str, Any] = {}
        self._resolved_sources: dict[str, str] = {}

    def add_source(self, name: str, values: Mapping[str, Any]) -> None:
        """設定ソースを登録する。既存キーは上書きされる。"""

        if name not in self._sources:
            self._sources[name] = {}
        for key, value in values.items():
            if value is None:
                continue
            self._sources[name][key] = value

    def resolve_with_source(self, key: str, default: Any | None = None) -> tuple[Any | None, str | None]:
        """優先度順に値を探索し、値とソース名を返す。"""

        for source in self.priority_order:
            candidate_map = self._sources.get(source, {})
            if key in candidate_map:
                return candidate_map[key], source
        return default, None

    def record(self, key: str, value: Any, source: str | None) -> None:
        """最終的に採用した値を記録する。"""

        if value is None:
            return
        if source is None:
            source = "auto_resolved"
        self._resolved[key] = value
        self._resolved_sources[key] = source

    def snapshot(self, keys: Iterable[str] | None = None) -> ResolvedConfig:
        """現在の設定をスナップショットとして返す。"""

        merged: dict[str, Any] = {}
        used_sources: dict[str, str] = {}

        target_keys = list(keys) if keys is not None else self._collect_keys()
        for key in target_keys:
            if key in self._resolved:
                merged[key] = self._resolved[key]
                used_sources[key] = self._resolved_sources.get(key, "auto_resolved")
                continue

            value, source = self.resolve_with_source(key)
            if value is None:
                continue
            merged[key] = value
            if source is not None:
                used_sources[key] = source

        return ResolvedConfig(values=merged, sources=used_sources, priority_order=self.priority_order)

    # ------------------------------------------------------------------ #
    # private helpers
    # ------------------------------------------------------------------ #
    def _collect_keys(self) -> list[str]:
        keys: set[str] = set(self._resolved)
        for source in self.priority_order:
            keys.update(self._sources.get(source, {}).keys())
        return sorted(keys)


__all__ = ["ConfigManager", "ResolvedConfig"]
