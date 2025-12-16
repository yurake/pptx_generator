from __future__ import annotations

from pathlib import Path

from pptx_generator.cli_handlers import template_extraction as mod


class _DummyPolicyResolution:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.source = "dummy"


def test_run_template_extraction_when_policy_missing(monkeypatch, tmp_path):
    """Template AI ポリシーが見つからない場合でも実行が継続することを確認する。"""

    template_path = tmp_path / "template.pptx"
    template_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        mod,
        "resolve_template_ai_policy_path",
        lambda path=None: _DummyPolicyResolution(None),
    )

    class _FakeTemplateSpec:
        layout_mode = "dynamic"
        blueprint = None
        layouts: list[object] = []
        warnings: list[str] = []
        errors: list[str] = []

        def model_dump(self, *, mode="json", exclude_none=False):
            return {"layouts": []}

    class _FakeMeta:
        def __init__(self) -> None:
            self._data: dict[str, object] = {}

        def model_copy(self, update=None):
            copied = _FakeMeta()
            copied._data.update(self._data)
            if update:
                copied._data.update(update)
            return copied

    class _FakeJobSpec:
        def __init__(self) -> None:
            self.meta = _FakeMeta()
            self.slides: list[object] = []

    class _FakeTemplateExtractor:
        def __init__(self, options) -> None:  # pragma: no cover - init only
            self.options = options

        def extract(self):
            return _FakeTemplateSpec()

        def build_jobspec_scaffold(self, template_spec):
            return _FakeJobSpec()

        def save_jobspec_scaffold(self, scaffold, path: Path) -> None:
            path.write_text("{}", encoding="utf-8")

    class _FakeBranding:
        def to_branding_payload(self) -> dict[str, object]:
            return {}

    monkeypatch.setattr(mod, "TemplateExtractor", _FakeTemplateExtractor)
    monkeypatch.setattr(mod, "extract_branding_config", lambda *_: _FakeBranding())

    result = mod.run_template_extraction(
        template_path=template_path,
        output_dir=tmp_path / "out",
        layout=None,
        anchor=None,
        output_format="json",
        template_ai_policy=None,
        template_ai_policy_id=None,
        disable_template_ai=False,
        layout_mode="dynamic",
        static_source="slide",
        skip_validation=True,
        emit_slide_snapshot=False,
    )

    assert result.validation_result is None
    assert result.template_spec_path.exists()
    assert result.branding_path.exists()
    assert result.jobspec_path.exists()
