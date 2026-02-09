#!/usr/bin/env python3
"""Stage2 hook: system requirements からシステム構成図を生成する。"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from diagram_gen import DiagramGenError, run_diagram_gen_command  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "input" / "system_requirements.md"


def _resolve_output_dir() -> Path:
    for env_name in ("PPTX_PREPARE_OUTPUT_DIR", "PPTX_OUTPUT_DIR"):
        env_value = os.environ.get(env_name)
        if isinstance(env_value, str) and env_value.strip():
            return Path(env_value).expanduser().resolve()
    return Path(".pptx/prepare").resolve()


def main() -> None:
    output_dir = _resolve_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = DEFAULT_INPUT
    if not input_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

    output_path = output_dir / "system_dependencies.png"

    logger.info("system diagram input: %s", input_path)
    logger.info("system diagram output: %s", output_path)

    try:
        run_diagram_gen_command(
            input_path=input_path,
            output_path=output_path,
            output_format="png",
            width=1920,
            height=1080,
            theme="default",
            llm_provider=None,
        )
    except DiagramGenError as exc:
        logger.error("diagram-gen failed: %s", exc)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
