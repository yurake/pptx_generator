from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from pptx_generator.cli_commands import (
    create_layout_validate_command,
    create_outline_command,
    create_tpl_extract_command,
    create_tpl_release_command,
)
from pptx_generator.cli_commands.utils import echo_command_errors
from pptx_generator.pipeline import PrepareNormalizationError
from pptx_generator.pipeline.draft_structuring import DraftStructuringError
from pptx_generator.cli_handlers.layout_validation import LayoutValidateCommandError
from pptx_generator.cli_handlers.template_commands import TemplateCommandError


def _invoke(command, args: list[str]) -> tuple[int, str, str]:
    runner = CliRunner()
    result = runner.invoke(command, args)
    return result.exit_code, result.output, result.stderr


def test_outline_command_invokes_handler(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(config) -> None:  # noqa: ANN001
        captured["run_config"] = config

    class DummyOutlineConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)
            captured["config"] = self

    monkeypatch.setattr(
        "pptx_generator.cli_commands.outline.run_outline_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.outline.OutlineCommandConfig",
        DummyOutlineConfig,
    )

    spec_path = tmp_path / "spec.json"
    spec_path.write_text("{}", encoding="utf-8")

    defaults = {
        "default_output_dir": tmp_path / "draft",
        "default_appendix_limit": 7,
        "default_prepare_cards_path": tmp_path / "prepare" / "prepare_card.json",
        "default_draft_filename": "draft.json",
        "default_approved_filename": "approved.json",
        "default_draft_log_filename": "draft_log.json",
        "default_generate_ready_filename": "ready.json",
        "default_generate_ready_meta_filename": "ready_meta.json",
        "default_draft_meta_filename": "draft_meta.json",
    }
    command = create_outline_command(**defaults)

    exit_code, *_ = _invoke(
        command,
        [
            str(spec_path),
            "--target-length",
            "5",
            "--structure-pattern",
            "demo",
            "--appendix-limit",
            "2",
        ],
    )

    assert exit_code == 0
    config = captured["run_config"]
    assert config.spec_path == spec_path
    assert config.target_length == 5
    assert config.structure_pattern == "demo"
    assert config.appendix_limit == 2
    assert config.output_dir == defaults["default_output_dir"]
    assert config.generate_ready_filename == "ready.json"


@pytest.mark.parametrize(
    "exc_type, message",
    [
        (PrepareNormalizationError, "プレペア成果物の読み込みに失敗しました"),
        (DraftStructuringError, "ドラフト構成の生成に失敗しました"),
    ],
)
def test_outline_command_error_paths(monkeypatch, tmp_path: Path, exc_type, message) -> None:
    def fake_run(config) -> None:  # noqa: ANN001
        raise exc_type("failure")  # type: ignore[call-arg]

    class DummyOutlineConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        "pptx_generator.cli_commands.outline.run_outline_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.outline.OutlineCommandConfig",
        DummyOutlineConfig,
    )

    spec_path = tmp_path / "spec.json"
    spec_path.write_text("{}", encoding="utf-8")

    command = create_outline_command(
        default_output_dir=tmp_path / "draft",
        default_appendix_limit=5,
        default_prepare_cards_path=tmp_path / "prepare_card.json",
        default_draft_filename="draft.json",
        default_approved_filename="approved.json",
        default_draft_log_filename="draft_log.json",
        default_generate_ready_filename="ready.json",
        default_generate_ready_meta_filename="ready_meta.json",
        default_draft_meta_filename="draft_meta.json",
    )

    exit_code, _, stderr = _invoke(command, [str(spec_path)])
    assert exit_code == 4
    assert message in stderr


def test_layout_validate_command_success(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(config):  # noqa: ANN001
        captured["run_config"] = config
        return object()

    def fake_echo(result) -> None:  # noqa: ANN001
        captured["result"] = result

    class DummyLayoutValidateConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)
            captured["config"] = self

    monkeypatch.setattr(
        "pptx_generator.cli_commands.layout_validate.run_layout_validate_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.layout_validate.echo_layout_validation_result",
        fake_echo,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.layout_validate.LayoutValidateCommandConfig",
        DummyLayoutValidateConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")
    baseline_path = tmp_path / "baseline.jsonl"
    baseline_path.write_text("{}", encoding="utf-8")

    command = create_layout_validate_command(default_output_dir=tmp_path / "validation")

    exit_code, _, _ = _invoke(
        command,
        [
            "--template",
            str(template_path),
            "--template-id",
            "demo",
            "--baseline",
            str(baseline_path),
        ],
    )

    assert exit_code == 0
    config = captured["run_config"]
    assert config.template_path == template_path
    assert config.output_dir == tmp_path / "validation"
    assert config.template_id == "demo"
    assert captured["result"] is not None


def test_layout_validate_command_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(config) -> None:  # noqa: ANN001
        raise LayoutValidateCommandError("boom", exit_code=9)

    class DummyLayoutValidateConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        "pptx_generator.cli_commands.layout_validate.run_layout_validate_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.layout_validate.LayoutValidateCommandConfig",
        DummyLayoutValidateConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_layout_validate_command(default_output_dir=tmp_path / "validation")

    exit_code, _, stderr = _invoke(command, ["--template", str(template_path)])
    assert exit_code == 9
    assert "boom" in stderr


def test_tpl_extract_command_success(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(config) -> None:  # noqa: ANN001
        captured["run_config"] = config

    class DummyExtractConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)
            captured["config"] = self

    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_extract.run_template_extract_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_extract.TemplateExtractCommandConfig",
        DummyExtractConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_tpl_extract_command(
        default_output_dir=tmp_path / "extract",
        default_layout_mode="dynamic",
    )

    exit_code, _, _ = _invoke(
        command,
        [
            "--template",
            str(template_path),
            "--layout",
            "Title",
            "--anchor",
            "Main",
            "--format",
            "yaml",
            "--layout-mode",
            "static",
        ],
    )

    assert exit_code == 0
    config = captured["run_config"]
    assert config.template_path == template_path
    assert config.format == "yaml"
    assert config.layout_mode == "static"
    assert config.output_dir == tmp_path / "extract"


def test_tpl_extract_command_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(config) -> None:  # noqa: ANN001
        raise TemplateCommandError("extract failed", exit_code=12)

    class DummyExtractConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_extract.run_template_extract_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_extract.TemplateExtractCommandConfig",
        DummyExtractConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_tpl_extract_command(
        default_output_dir=tmp_path / "extract",
        default_layout_mode="dynamic",
    )

    exit_code, _, stderr = _invoke(command, ["--template", str(template_path)])
    assert exit_code == 12
    assert "extract failed" in stderr


def test_tpl_release_command_success(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(config):  # noqa: ANN001
        captured["run_config"] = config

        class DummyResult:
            pass

        return DummyResult()

    def fake_echo(result) -> None:  # noqa: ANN001
        captured["result"] = result

    class DummyReleaseConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)
            captured["config"] = self

    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_release.run_template_release_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_release.echo_template_release_result",
        fake_echo,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_release.TemplateReleaseCommandConfig",
        DummyReleaseConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_tpl_release_command(
        default_output_dir=tmp_path / "release",
        default_layout_mode="dynamic",
    )

    exit_code, _, _ = _invoke(
        command,
        [
            "--template",
            str(template_path),
            "--brand",
            "Acme",
            "--version",
            "1.0.0",
            "--template-id",
            "tmpl",
            "--layout-mode",
            "static",
        ],
    )

    assert exit_code == 0
    config = captured["run_config"]
    assert config.template_path == template_path
    assert config.brand == "Acme"
    assert config.version == "1.0.0"
    assert config.layout_mode == "static"
    assert captured["result"] is not None


def test_tpl_release_command_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(config) -> None:  # noqa: ANN001
        raise TemplateCommandError("release failed", exit_code=15)

    class DummyReleaseConfig:
        def __init__(self, **kwargs) -> None:  # noqa: ANN001
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_release.run_template_release_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.tpl_release.TemplateReleaseCommandConfig",
        DummyReleaseConfig,
    )

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_tpl_release_command(
        default_output_dir=tmp_path / "release",
        default_layout_mode="dynamic",
    )

    exit_code, _, stderr = _invoke(
        command,
        [
            "--template",
            str(template_path),
            "--brand",
            "Acme",
            "--version",
            "1.0.0",
        ],
    )

    assert exit_code == 15
    assert "release failed" in stderr


def test_echo_command_errors_with_payload(capsys) -> None:
    echo_command_errors("problem", [{"code": "E001"}])
    captured = capsys.readouterr()
    assert "problem" in captured.err
    assert '"code": "E001"' in captured.err


def test_echo_command_errors_without_payload(capsys) -> None:
    echo_command_errors("warning", None)
    captured = capsys.readouterr()
    assert captured.err.strip() == "warning"
