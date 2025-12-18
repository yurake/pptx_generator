from pathlib import Path

from pptx_generator.settings.paths import build_output_dir, get_output_root


def test_get_output_root_defaults(monkeypatch) -> None:
    monkeypatch.delenv("PPTX_OUTPUT_ROOT", raising=False)

    assert get_output_root() == Path(".pptx")


def test_build_output_dir_with_env_and_ids(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))

    path = build_output_dir("gen", transaction_id="tx-1", job_id="job-1")

    assert path == tmp_path / "tx-1" / "gen" / "job-1"


def test_build_output_dir_without_ids(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))

    path = build_output_dir("prepare")

    assert path == tmp_path / "prepare"
