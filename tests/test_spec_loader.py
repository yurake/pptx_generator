"""JobSpecScaffold 変換ユーティリティのテスト。"""

from __future__ import annotations

from pathlib import Path

import json

from pptx_generator.models import JobSpec
from pptx_generator.spec_loader import load_jobspec_from_path


def test_load_jobspec_from_scaffold() -> None:
    scaffold_path = Path("samples/extract/jobspec.json")
    spec = load_jobspec_from_path(scaffold_path)

    assert isinstance(spec, JobSpec)
    assert spec.meta.title
    assert spec.auth.created_by
    assert spec.slides, "スライドが変換されていること"
    first_slide = spec.slides[0]
    assert first_slide.textboxes, "テキストのプレースホルダが textboxes として変換される"
    # 画像プレースホルダなどは notes に要約される
    assert first_slide.notes is None or "Logo" in first_slide.notes


def test_load_jobspec_from_jobspec_json() -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    spec = load_jobspec_from_path(spec_path)

    assert isinstance(spec, JobSpec)
    expected = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec.meta.title == expected["meta"]["title"]
