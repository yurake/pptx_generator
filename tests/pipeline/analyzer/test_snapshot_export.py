from __future__ import annotations

import json
from pathlib import Path

from pptx_generator.pipeline.analyzer.snapshot_export import _write_json_payload


def test_write_json_payload_creates_directory_and_writes_utf8(tmp_path: Path) -> None:
    workdir = tmp_path / "nested" / "dir"
    payload = {"message": "テスト", "value": 1}

    path = _write_json_payload(payload, workdir, "out.json")

    assert path.exists()
    assert path.parent == workdir
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == payload
