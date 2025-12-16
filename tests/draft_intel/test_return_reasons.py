from __future__ import annotations

from pathlib import Path

from pptx_generator import draft_intel
from pptx_generator.draft_intel import ReturnReasonTemplate


def test_load_return_reasons_returns_builtin_templates(tmp_path: Path) -> None:
    dummy_path = tmp_path / "return_reasons.json"

    reasons = draft_intel.load_return_reasons(dummy_path)

    assert isinstance(reasons, tuple)
    assert [item.code for item in reasons] == [
        "STRUCTURE_GAP",
        "ANALYZER_BLOCKER",
        "CAPACITY_WARN",
    ]
    assert all(isinstance(item, ReturnReasonTemplate) for item in reasons)
