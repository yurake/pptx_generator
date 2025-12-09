"""Lazy-loading helpers for settings modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .branding import BrandingConfig
from .paths import find_config_path
from .rules import RulesConfig

__all__ = ["load_rules_config", "load_branding_config"]


@lru_cache(maxsize=None)
def load_rules_config(path: Path | str) -> RulesConfig:
    """Load and cache RulesConfig from the given path."""

    resolved = find_config_path(path)
    if resolved is not None:
        return RulesConfig.load(resolved)

    candidate = Path(path)
    msg = f"RulesConfig の既定ファイルが見つかりませんでした: {candidate}"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=None)
def load_branding_config(path: Path | str) -> BrandingConfig:
    """Load and cache BrandingConfig from the given path."""

    resolved = find_config_path(path)
    if resolved is not None:
        return BrandingConfig.load(resolved)

    candidate = Path(path)
    msg = f"BrandingConfig の既定ファイルが見つかりませんでした: {candidate}"
    raise FileNotFoundError(msg)
