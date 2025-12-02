"""Pipeline rules configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .coercers import (
    coerce_args,
    coerce_bool,
    coerce_float,
    coerce_hex,
    coerce_int,
    coerce_str,
)

__all__ = [
    "AnalyzerRuleConfig",
    "RefinerRuleConfig",
    "PolisherRuleConfig",
    "RulesConfig",
]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalyzerRuleConfig:
    min_font_size: float | None = None
    default_font_size: float | None = None
    default_font_color: str | None = None
    preferred_text_color: str | None = None
    background_color: str | None = None
    min_contrast_ratio: float | None = None
    large_text_min_contrast: float | None = None
    large_text_threshold_pt: float | None = None
    margin_in: float | None = None
    slide_width_in: float | None = None
    slide_height_in: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "AnalyzerRuleConfig":
        if not payload:
            return cls()
        return cls(
            min_font_size=coerce_float(payload.get("min_font_size")),
            default_font_size=coerce_float(payload.get("default_font_size")),
            default_font_color=coerce_hex(payload.get("default_font_color")),
            preferred_text_color=coerce_hex(payload.get("preferred_text_color")),
            background_color=coerce_hex(payload.get("background_color")),
            min_contrast_ratio=coerce_float(payload.get("min_contrast_ratio")),
            large_text_min_contrast=coerce_float(payload.get("large_text_min_contrast")),
            large_text_threshold_pt=coerce_float(payload.get("large_text_threshold_pt")),
            margin_in=coerce_float(payload.get("margin_in")),
            slide_width_in=coerce_float(payload.get("slide_width_in")),
            slide_height_in=coerce_float(payload.get("slide_height_in")),
        )


@dataclass(slots=True)
class RefinerRuleConfig:
    enable_bullet_reindent: bool = True
    enable_font_raise: bool = False
    min_font_size: float | None = None
    enable_color_adjust: bool = False
    preferred_text_color: str | None = None
    fallback_font_color: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "RefinerRuleConfig":
        if not payload:
            return cls()

        return cls(
            enable_bullet_reindent=coerce_bool(payload.get("enable_bullet_reindent"), True),
            enable_font_raise=coerce_bool(payload.get("enable_font_raise"), False),
            min_font_size=coerce_float(payload.get("min_font_size")),
            enable_color_adjust=coerce_bool(payload.get("enable_color_adjust"), False),
            preferred_text_color=coerce_hex(payload.get("preferred_text_color")),
            fallback_font_color=coerce_hex(payload.get("fallback_font_color")),
        )


@dataclass(slots=True)
class PolisherRuleConfig:
    enabled: bool = False
    executable: str | None = None
    rules_path: str | None = None
    timeout_sec: int = 90
    arguments: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "PolisherRuleConfig":
        if not payload:
            return cls()

        timeout = coerce_int(payload.get("timeout_sec"))
        if timeout is None or timeout <= 0:
            timeout = 90

        return cls(
            enabled=coerce_bool(payload.get("enabled"), False),
            executable=coerce_str(payload.get("executable")),
            rules_path=coerce_str(payload.get("rules_path")),
            timeout_sec=timeout,
            arguments=coerce_args(payload.get("arguments")),
        )


@dataclass(slots=True)
class RulesConfig:
    max_title_length: int | None = None
    max_bullet_length: int | None = None
    max_bullet_level: int | None = None
    forbidden_words: tuple[str, ...] = ()
    analyzer: AnalyzerRuleConfig = field(default_factory=AnalyzerRuleConfig)
    refiner: RefinerRuleConfig = field(default_factory=RefinerRuleConfig)
    polisher: PolisherRuleConfig = field(default_factory=PolisherRuleConfig)

    @classmethod
    def load(cls, path: Path | str) -> "RulesConfig":
        path = Path(path)
        logger.info("Loading rules config from %s", path.resolve())
        data = json.loads(path.read_text(encoding="utf-8"))
        config = cls.from_dict(data)
        logger.info("Loaded rules config from %s", path.resolve())
        return config

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RulesConfig":
        title_payload = data.get("title")
        bullet_payload = data.get("bullet")
        analyzer = AnalyzerRuleConfig.from_dict(data.get("analyzer", {}))
        refiner = RefinerRuleConfig.from_dict(data.get("refiner", {}))
        polisher = PolisherRuleConfig.from_dict(data.get("polisher", {}))

        title_max = coerce_int(title_payload.get("max_length")) if isinstance(title_payload, dict) else None
        bullet_max_length = (
            coerce_int(bullet_payload.get("max_length")) if isinstance(bullet_payload, dict) else None
        )
        bullet_max_level = (
            coerce_int(bullet_payload.get("max_level")) if isinstance(bullet_payload, dict) else None
        )

        forbidden_words: tuple[str, ...] = ()
        forbidden_raw = data.get("forbidden_words", ())
        if isinstance(forbidden_raw, Iterable):
            normalized = [str(word).strip() for word in forbidden_raw if str(word).strip()]
            forbidden_words = tuple(normalized)

        return cls(
            max_title_length=title_max,
            max_bullet_length=bullet_max_length,
            max_bullet_level=bullet_max_level,
            forbidden_words=forbidden_words,
            analyzer=analyzer,
            refiner=refiner,
            polisher=polisher,
        )
