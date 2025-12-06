from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnalyzerOptions:
    output_filename: str = "analysis.json"
    min_font_size: float = 18.0
    min_contrast_ratio: float = 4.5
    large_text_min_contrast: float = 3.0
    large_text_threshold_pt: float = 18.0
    max_bullet_level: int = 3
    margin_in: float = 0.5
    slide_width_in: float = 10.0
    slide_height_in: float = 7.5
    default_font_size: float = 18.0
    default_font_color: str = "#333333"
    preferred_text_color: str | None = None
    background_color: str = "#FFFFFF"
    grid_size_in: float = 0.125
    grid_tolerance_in: float = 0.02
    snapshot_output_filename: str | None = None
