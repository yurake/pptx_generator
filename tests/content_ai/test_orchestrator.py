"""AI オーケストレーターのテスト。"""

from __future__ import annotations

from pathlib import Path

from pptx_generator.content_ai import ContentAIOrchestrator, load_policy_set
from pptx_generator.models import JobSpec


def test_orchestrator_generates_document() -> None:
    spec = JobSpec.parse_file(Path("samples/json/sample_spec.json"))
    policy_set = load_policy_set(Path("config/content_ai_policies.json"))
    orchestrator = ContentAIOrchestrator(policy_set)

    document, meta, logs = orchestrator.generate_document(spec)

    assert len(document.slides) == len(spec.slides)
    assert meta["policy_id"] == policy_set.default_policy_id
    assert len(meta["slides"]) == len(document.slides)
    assert len(logs) == len(document.slides)

    for slide in document.slides:
        assert slide.status == "draft"
        assert slide.elements.title
        assert slide.elements.body
        assert len(slide.elements.body) <= 6
        for line in slide.elements.body:
            assert len(line) <= 40

    assert meta["spec"]["title"] in logs[0]["prompt"]
