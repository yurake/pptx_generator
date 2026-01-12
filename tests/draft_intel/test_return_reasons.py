from __future__ import annotations

from pathlib import Path

from pptx_generator.draft import ReturnReasonTemplate, load_return_reasons


def test_load_return_reasons_returns_builtin_templates(tmp_path: Path) -> None:
    dummy_path = tmp_path / "return_reasons.json"

    reasons = load_return_reasons(dummy_path)

    assert isinstance(reasons, tuple)
    assert [item.code for item in reasons] == [
        "STRUCTURE_GAP",
        "ANALYZER_BLOCKER",
        "CAPACITY_WARN",
    ]
    assert all(isinstance(item, ReturnReasonTemplate) for item in reasons)
