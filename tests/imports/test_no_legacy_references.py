from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_DIRS = [
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "samples",
    PROJECT_ROOT / "scripts",
]
DEPRECATED_TOKENS = [
    "pptx_generator.spec_loader",
    "pptx_generator.branding_extractor",
    "pptx_generator.draft_intel",
    "pptx_generator.draft_recommender",
]
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".rst",
    ".sh",
}


def _iter_text_files(base: Path) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return files


@pytest.mark.parametrize("token", DEPRECATED_TOKENS)
def test_no_deprecated_references(token: str) -> None:
    offenders: list[Path] = []
    for target in TARGET_DIRS:
        for path in _iter_text_files(target):
            text = path.read_text(encoding="utf-8")
            if token in text:
                offenders.append(path.relative_to(PROJECT_ROOT))
    assert not offenders, f"Deprecated token '{token}' found in: {offenders}"
