"""レイアウト検証のファイル入出力ユーティリティ。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_jsonl(records: Iterable[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            file.write("\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records
