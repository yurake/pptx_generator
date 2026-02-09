"""
Markdownからシステム依存関係図を生成する。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from diagram_generator import DiagramParser, MermaidBuilder, SystemExtractor

logger = logging.getLogger(__name__)


class DiagramGenError(RuntimeError):
    """diagram-gen エラー"""


def run_diagram_gen_command(
    *,
    input_path: Path,
    output_path: Path,
    output_format: str,
    width: int,
    height: int,
    theme: str,
    llm_provider: str | None,
) -> None:
    if llm_provider:
        os.environ["PPTX_DIAGRAM_LLM_PROVIDER"] = llm_provider

    logger.info("Reading input file: %s", input_path)
    markdown_text = input_path.read_text(encoding="utf-8")

    logger.info("Parsing markdown...")
    parser = DiagramParser()
    diagram_data = parser.parse_markdown(markdown_text)

    logger.info("Found %d cases", len(diagram_data.cases))
    for case in diagram_data.cases:
        logger.info("  Case: %s (%d components)", case.case_name, len(case.components))

    logger.info("Extracting relations...")
    extractor = SystemExtractor()
    diagram_data = extractor.extract_relations(diagram_data)

    total_relations = sum(len(case.relations) for case in diagram_data.cases)
    logger.info("Extracted %d relations", total_relations)

    logger.info("Building Mermaid syntax...")
    builder = MermaidBuilder()
    mermaid_text = builder.build(diagram_data)

    if output_format.lower() == "mermaid":
        logger.info("Writing Mermaid file: %s", output_path)
        output_path.write_text(mermaid_text, encoding="utf-8")
        logger.info("✓ Mermaid file generated successfully")
        return

    if output_format.lower() == "png":
        temp_mmd_path = output_path.with_suffix(".mmd")
        logger.info("Writing temporary Mermaid file: %s", temp_mmd_path)
        temp_mmd_path.write_text(mermaid_text, encoding="utf-8")

        try:
            logger.info("Rendering PNG with Mermaid CLI...")
            render_mermaid_to_png(
                mmd_path=temp_mmd_path,
                output_path=output_path,
                width=width,
                height=height,
                theme=theme,
            )
            logger.info("✓ PNG file generated successfully")
        finally:
            if temp_mmd_path.exists():
                temp_mmd_path.unlink()
                logger.debug("Temporary file removed: %s", temp_mmd_path)
        return

    raise DiagramGenError(f"Unknown output format: {output_format}")


def render_mermaid_to_png(
    *,
    mmd_path: Path,
    output_path: Path,
    width: int,
    height: int,
    theme: str,
) -> None:
    try:
        subprocess.run(
            ["mmdc", "--version"],
            capture_output=True,
            check=True,
            text=True,
        )
    except FileNotFoundError:
        raise DiagramGenError(
            "Mermaid CLI (mmdc) が見つかりません。\n"
            "インストール手順: npm install -g @mermaid-js/mermaid-cli\n"
            "詳細: docs/runbooks/mermaid-cli-setup.md"
        )
    except subprocess.CalledProcessError as exc:
        raise DiagramGenError(f"Mermaid CLI version check failed: {exc}")

    cmd = [
        "mmdc",
        "-i",
        str(mmd_path),
        "-o",
        str(output_path),
        "-w",
        str(width),
        "-H",
        str(height),
        "-t",
        theme,
        "-b",
        "transparent",
    ]

    logger.debug("Running command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            text=True,
        )
        if result.stdout:
            logger.debug("mmdc stdout: %s", result.stdout)
        if result.stderr:
            logger.warning("mmdc stderr: %s", result.stderr)
    except subprocess.CalledProcessError as exc:
        error_msg = f"Mermaid CLI failed (exit code {exc.returncode})"
        if exc.stderr:
            error_msg += f"\nError output: {exc.stderr}"
        raise DiagramGenError(error_msg)
    except Exception as exc:
        raise DiagramGenError(f"Unexpected error during PNG rendering: {exc}")
