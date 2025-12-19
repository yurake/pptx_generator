from pathlib import Path

from pptx_generator.settings.paths import build_input_dir, get_input_root


def test_get_input_root_defaults(monkeypatch) -> None:
    monkeypatch.delenv("PPTX_INPUT_ROOT", raising=False)

    assert get_input_root() == Path(".pptx/input")


def test_build_input_dir_with_env_and_ids(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PPTX_INPUT_ROOT", str(tmp_path))

    path = build_input_dir(transaction_id="tx-1", job_id="job-1")

    assert path == tmp_path / "tx-1" / "job-1"


def test_build_input_dir_without_ids(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PPTX_INPUT_ROOT", str(tmp_path))

    path = build_input_dir()

    assert path == tmp_path
