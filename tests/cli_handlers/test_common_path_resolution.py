from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.cli_handlers import common
from pptx_generator.config_manager import ConfigManager


class _DummySpec:
    def __init__(self, meta: object | None) -> None:
        self.meta = meta


def test_resolve_layouts_path_prefers_config_and_records(tmp_path: Path) -> None:
    spec_source = tmp_path / "jobspec.json"
    spec_source.write_text("{}", encoding="utf-8")

    layouts_file = tmp_path / "custom" / "layouts.jsonl"
    layouts_file.parent.mkdir(parents=True, exist_ok=True)
    layouts_file.write_text("[]", encoding="utf-8")

    config = ConfigManager()
    config.add_source("cli_options", {"layouts_path": str(layouts_file)})

    result = common.resolve_layouts_path(
        spec=_DummySpec(meta={}),
        spec_source=spec_source,
        config_manager=config,
    )

    assert result == layouts_file
    snapshot = config.snapshot(keys=("layouts_path",))
    assert snapshot.values["layouts_path"] == str(layouts_file)
    assert snapshot.sources["layouts_path"] == "cli_options"


def test_resolve_layouts_path_prefers_spec_relative(tmp_path: Path) -> None:
    spec_dir = tmp_path / "specdir"
    spec_dir.mkdir()
    spec_source = spec_dir / "jobspec.json"
    spec_source.write_text('{"meta":{"layouts_path":"layouts/layouts.jsonl"}}', encoding="utf-8")

    layouts_in_spec = spec_dir / "layouts" / "layouts.jsonl"
    layouts_in_spec.parent.mkdir(parents=True, exist_ok=True)
    layouts_in_spec.write_text("[]", encoding="utf-8")

    result = common.resolve_layouts_path(
        spec=_DummySpec(meta=None),
        spec_source=spec_source,
        config_manager=None,
    )

    assert result == layouts_in_spec


def test_resolve_layouts_path_raises_with_candidates(tmp_path: Path) -> None:
    spec_source = tmp_path / "jobspec.json"
    spec_source.write_text('{"meta":{"layouts_path":"missing/layouts.jsonl"}}', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        common.resolve_layouts_path(
            spec=_DummySpec(meta=None),
            spec_source=spec_source,
            config_manager=None,
        )

    message = str(excinfo.value)
    assert "jobspec.meta.layouts_path" in message
    assert "確認したパス" in message


def test_resolve_template_path_prefers_spec_relative(tmp_path: Path) -> None:
    spec_dir = tmp_path / "specdir"
    spec_dir.mkdir()
    template_rel = "templates/template.pptx"
    spec_source = spec_dir / "jobspec.json"
    spec_source.write_text(f'{{"meta":{{"template_path":"{template_rel}"}}}}', encoding="utf-8")

    template_file = spec_dir / template_rel
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text("", encoding="utf-8")

    result = common.resolve_template_path(
        spec=_DummySpec(meta=None),
        spec_source=spec_source,
        config_manager=None,
    )

    assert result == template_file


def test_resolve_template_path_requires_value(tmp_path: Path) -> None:
    spec_source = tmp_path / "jobspec.json"
    spec_source.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        common.resolve_template_path(
            spec=_DummySpec(meta={}),
            spec_source=spec_source,
            config_manager=None,
        )

    assert "jobspec.meta.template_path" in str(excinfo.value)


def test_resolve_template_path_raises_with_candidates(tmp_path: Path) -> None:
    spec_dir = tmp_path / "specdir"
    spec_dir.mkdir()
    spec_source = spec_dir / "jobspec.json"
    spec_source.write_text('{"meta":{"template_path":"missing/template.pptx"}}', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        common.resolve_template_path(
            spec=_DummySpec(meta=None),
            spec_source=spec_source,
            config_manager=None,
        )

    message = str(excinfo.value)
    assert "jobspec.meta.template_path" in message
    assert "確認したパス" in message
