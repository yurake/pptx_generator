from __future__ import annotations

from pptx_generator import cli


def test_prepare_card_default_filename_matches_constant():
    default_path = cli.DEFAULT_PREPARE_OUTPUT_DIR / cli.PREPARE_CARD_FILENAME
    assert default_path.name == cli.PREPARE_CARD_FILENAME
    assert str(default_path).endswith(f"/{cli.PREPARE_CARD_FILENAME}")
