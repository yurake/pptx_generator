from pathlib import Path

from pptx_generator.pipeline.slide_image_exporter import _collect_slide_images, _parse_slide_index


def test_parse_slide_index_variants():
    stem = "deck"
    cases = {
        "deck.png": 0,
        "deck-1.png": 0,
        "deck-2.png": 1,
        "deck_3.png": 2,
        "deck4.png": 3,
    }
    for name, expected in cases.items():
        assert _parse_slide_index(Path(name), stem) == expected


def test_collect_slide_images(tmp_path):
    stem = "deck"
    names = ["deck.png", "deck-2.png", "deck_3.png"]
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"")
        paths.append(path)

    images = _collect_slide_images(tmp_path, stem, "png")

    assert images[0] == paths[0]
    assert images[1] == paths[1]
    assert images[2] == paths[2]
