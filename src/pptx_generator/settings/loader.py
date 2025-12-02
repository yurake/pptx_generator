"""Lazy-loading helpers for settings modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .branding import BrandingConfig
from .rules import RulesConfig

__all__ = ["load_rules_config", "load_branding_config"]


@lru_cache(maxsize=None)
def load_rules_config(path: Path | str) -> RulesConfig:
    """Load and cache RulesConfig from the given path."""

    resolved = Path(path).resolve()
    return RulesConfig.load(resolved)


@lru_cache(maxsize=None)
def load_branding_config(path: Path | str) -> BrandingConfig:
    """Load and cache BrandingConfig from the given path."""

    resolved = Path(path).resolve()
    return BrandingConfig.load(resolved)
