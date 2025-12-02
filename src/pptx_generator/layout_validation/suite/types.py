"""レイアウト検証スイートで使用する型。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LayoutValidationOptions:
    """レイアウト検証処理のオプション。"""

    template_path: Path
    output_dir: Path
    template_id: str | None = None
    baseline_path: Path | None = None
    analyzer_snapshot_path: Path | None = None
    template_ai_policy_path: Path | None = None
    template_ai_policy_id: str | None = None
    disable_template_ai: bool = False


@dataclass(slots=True)
class LayoutValidationResult:
    """検証処理の結果。"""

    layouts_path: Path
    diagnostics_path: Path
    diff_report_path: Path | None
    record_count: int
    warnings_count: int
    errors_count: int


class LayoutValidationError(RuntimeError):
    """レイアウト検証に関する例外。"""
