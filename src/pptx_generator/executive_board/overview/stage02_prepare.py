#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from overview import generate_ready_from_input_sample, ensure_slide_inputs_manifest


def main() -> int:
    # generate_ready 用の入力を準備（PPTX_STAGE=prepare で実行される前提）
    sys.argv = [__file__]
    generate_ready_from_input_sample.main()
    sys.argv = [__file__]
    ensure_slide_inputs_manifest.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
