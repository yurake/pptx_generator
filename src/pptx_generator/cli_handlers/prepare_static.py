from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from pptx_generator.models import (
    JobSpec,
    SpecValidationError,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateSpec,
)
from pptx_generator.content_import import ContentImportService
from pptx_generator.prepare import PrepareDocument
from pptx_generator.prepare.source import PrepareSourceDocument
from pptx_generator.template import load_jobspec_from_path

from .prepare_errors import PrepareCommandError

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_FILENAME_PATTERN = re.compile(r"^(?P<index>\d{1,2})_(?P<slug>[a-z0-9-]+)\.md$", re.IGNORECASE)
PROMPT_USER_SECTION_START = "<<<user-editable:start"
PROMPT_USER_SECTION_END = "<<<user-editable:end"
PROMPT_DEFAULT_LINES = {
    "- 例: このスライドでは ROI の定量値を箇条書きで入れる",
    "- 例: リスクを最低 2 点列挙する",
}


def resolve_static_context(
    *,
    jobspec_path: Path | None,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path,
    mode: str,
    prepare_path: Path | None,
    has_inline_source: bool,
):
    if mode != "static":
        from .prepare_models import PrepareStaticContext

        return PrepareStaticContext(
            blueprint_spec=None,
            blueprint_ref=None,
            template_spec_path=None,
            prompt_overrides=[],
            slide_input_sources=None,
            slide_input_refs=None,
            source_document=None,
            messages=[],
            import_metadata=[],
        )

    resolved_jobspec = jobspec_path or default_jobspec_path
    if not resolved_jobspec.exists():
        raise PrepareCommandError(
            "static モードでは --jobspec で jobspec.json のパスを指定するか、.pptx/template/jobspec.json を用意してください",
            exit_code=2,
        )

    try:
        jobspec = _load_jobspec(resolved_jobspec)
    except (FileNotFoundError, ValidationError, SpecValidationError) as exc:
        raise PrepareCommandError(f"jobspec.json の読み込みに失敗しました: {exc}", exit_code=2) from exc

    template_spec_ref = getattr(jobspec.meta, "template_spec_path", None)
    if not template_spec_ref:
        raise PrepareCommandError(
            "jobspec.meta.template_spec_path が設定されていません。テンプレ抽出を再実行してください",
            exit_code=2,
        )

    template_spec_path = Path(template_spec_ref)
    if not template_spec_path.is_absolute():
        template_spec_path = (resolved_jobspec.parent / template_spec_path).resolve()

    if not template_spec_path.exists():
        raise PrepareCommandError(
            f"template_spec.json が見つかりません: {template_spec_path}",
            exit_code=2,
        )

    blueprint_spec = _load_template_spec(template_spec_path)

    if blueprint_spec.layout_mode != "static":
        raise PrepareCommandError("template_spec の layout_mode が static ではありません", exit_code=2)
    if blueprint_spec.blueprint is None:
        raise PrepareCommandError("template_spec に blueprint が含まれていません", exit_code=2)

    blueprint_hash = hashlib.sha256(
        json.dumps(
            blueprint_spec.blueprint.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    blueprint_ref = {
        "path": str(template_spec_path),
        "hash": f"sha256:{blueprint_hash}",
        "template_source": blueprint_spec.template_source,
    }

    prompt_overrides = load_prompt_overrides(
        prompts_dir=template_spec_path.parent / prompts_dirname,
        blueprint=blueprint_spec.blueprint,
    )
    messages: list[str] = []
    if prompt_overrides:
        applied_names = ", ".join(
            Path(override.template_path).name if override.template_path else f"slide{override.slide_index:02d}"
            for override in prompt_overrides
        )
        messages.append(f"カスタムプロンプトを適用します: {applied_names}")

    slide_manifest = template_spec_path.parent.parent / slide_inputs_filename
    slide_input_sources: dict[str, PrepareSourceDocument] | None = None
    slide_input_refs: dict[str, str] | None = None
    first_source: PrepareSourceDocument | None = None
    import_metadata: list[dict[str, Any]] = []
    service = ContentImportService()
    if slide_manifest.exists():
        try:
            slide_input_paths = _load_slide_inputs_manifest(
                manifest_path=slide_manifest,
                blueprint=blueprint_spec.blueprint,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise PrepareCommandError(f"slide_inputs の読み込みに失敗しました: {exc}", exit_code=2) from exc

        if slide_input_paths:
            slide_input_sources = {}
            slide_input_refs = {}
            for slide_id, data_path in slide_input_paths.items():
                from pptx_generator.cli_handlers import prepare as prepare_module

                document, per_source_meta, per_source_messages = prepare_module._load_prepare_input(  # type: ignore[attr-defined]
                    str(data_path),
                    service,
                )
                slide_input_sources[slide_id] = document
                slide_input_refs[slide_id] = str(data_path)
                import_metadata.extend(per_source_meta)
                messages.extend(per_source_messages)
                if first_source is None:
                    first_source = document

            messages.append(f"スライド入力マニフェストを利用します: {slide_manifest}")
        else:
            messages.append(f"スライド入力マニフェストはプレースホルダーのみのためスキップします: {slide_manifest}")
            if not has_inline_source:
                raise PrepareCommandError(
                    "slide_inputs.md に有効な入力が含まれていません。--prepare 引数などでプレペア入力ファイルを指定してください",
                    exit_code=2,
                )
    elif prepare_path is None and not has_inline_source:
        raise PrepareCommandError(
            ".pptx/slide_inputs.md が見つかりません。プレペア入力ファイルを指定するか、マニフェストを用意してください",
            exit_code=2,
        )

    from .prepare_models import PrepareStaticContext

    return PrepareStaticContext(
        blueprint_spec=blueprint_spec,
        blueprint_ref=blueprint_ref,
        template_spec_path=template_spec_path,
        prompt_overrides=prompt_overrides,
        slide_input_sources=slide_input_sources,
        slide_input_refs=slide_input_refs,
        source_document=first_source,
        messages=messages,
        import_metadata=import_metadata,
    )


def load_prompt_overrides(
    *,
    prompts_dir: Path,
    blueprint: TemplateBlueprint,
):
    if not prompts_dir.exists() or not prompts_dir.is_dir():
        return []

    from pptx_generator.prepare_ai import StaticPromptOverride

    slides = list(enumerate(blueprint.slides, start=1))
    overrides: list[StaticPromptOverride] = []

    for path in sorted(prompts_dir.glob("*.md")):
        match = PROMPT_TEMPLATE_FILENAME_PATTERN.match(path.name)
        if not match:
            logger.debug("Prompts: ファイル名が規約に一致しないためスキップします: %s", path)
            continue
        index = int(match.group("index"))
        if index < 1 or index > len(slides):
            logger.debug("Prompts: インデックス %d が Blueprint の範囲外です", index)
            continue

        slide = slides[index - 1][1]
        instructions = _extract_prompt_instructions(path)
        if not instructions:
            continue

        slide_id = slide.slide_id or f"slide-{index:02d}"
        from pptx_generator.prepare_ai import StaticPromptOverride as SPO

        override = SPO(
            slide_id=slide_id,
            slide_index=index,
            instructions=instructions,
            template_path=str(path),
        )
        overrides.append(override)

    return overrides


def _extract_prompt_instructions(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Prompts: ファイルが存在しません: %s", path)
        return ""

    start_idx = text.find(PROMPT_USER_SECTION_START)
    end_idx = text.find(PROMPT_USER_SECTION_END)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        logger.debug("Prompts: user-editable セクションが見つかりません: %s", path)
        return ""

    start_idx += len(PROMPT_USER_SECTION_START)
    section = text[start_idx:end_idx]
    lines = [line.rstrip() for line in section.splitlines()]

    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in PROMPT_DEFAULT_LINES:
            continue
        cleaned.append(stripped)

    return "\n".join(cleaned).strip()


def _load_slide_inputs_manifest(
    *,
    manifest_path: Path,
    blueprint: TemplateBlueprint,
) -> dict[str, Path]:
    text = manifest_path.read_text(encoding="utf-8")
    mapping: dict[str, Path] = {}
    placeholder_identifiers: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"slide_inputs の形式が不正です: '{line}'")
        key, value = line.split(":", 1)
        identifier = key.strip()
        path_value = value.strip()
        if not identifier or not path_value:
            raise ValueError(f"slide_inputs の行に空の値があります: '{line}'")
        if path_value.startswith("<") and path_value.endswith(">"):
            placeholder_identifiers.add(identifier)
            continue
        resolved = Path(path_value)
        if not resolved.is_absolute():
            default_path = (manifest_path.parent / resolved).resolve()
            project_path = (Path.cwd() / resolved).resolve()
            if project_path.exists():
                resolved = project_path
            else:
                resolved = default_path
        mapping[identifier] = resolved

    expected: dict[str, Path] = {}
    missing: list[str] = []
    for index, slide in enumerate(blueprint.slides, start=1):
        identifier = build_prompt_identifier(index, slide)
        if identifier not in mapping:
            if identifier in placeholder_identifiers:
                continue
            missing.append(identifier)
            continue
        expected[slide.slide_id or identifier] = mapping[identifier]

    if missing:
        missing_list = ", ".join(missing)
        raise ValueError("slide_inputs.md に不足しているスライドがあります: " + missing_list)

    return expected


def build_prompt_identifier(index: int, slide: TemplateBlueprintSlide) -> str:
    slug_source = slide.layout or slide.slide_id or f"slide{index:02}"
    slug = slugify_prompt_layout(slug_source)
    return f"{index:02}_{slug}"


def slugify_prompt_layout(source: str) -> str:
    lowered = source.strip().lower()
    if not lowered:
        lowered = "layout"
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = normalized.strip("-") or "layout"
    return normalized[:48]


def _load_jobspec(path: Path) -> JobSpec:
    logger.info("Loading JobSpec from %s", path.resolve())
    return load_jobspec_from_path(path)


def _load_template_spec(path: Path) -> TemplateSpec:
    try:
        template_spec_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PrepareCommandError(f"template_spec の読み込みに失敗しました: {exc}", exit_code=2) from exc

    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            import yaml

            payload = yaml.safe_load(template_spec_text)
            return TemplateSpec.model_validate(payload)
        return TemplateSpec.model_validate_json(template_spec_text)
    except ValueError as exc:
        raise PrepareCommandError(f"template_spec の検証に失敗しました: {exc}", exit_code=2) from exc


__all__ = [
    "PROMPT_DEFAULT_LINES",
    "PROMPT_TEMPLATE_FILENAME_PATTERN",
    "PROMPT_USER_SECTION_END",
    "PROMPT_USER_SECTION_START",
    "resolve_static_context",
    "load_prompt_overrides",
    "_load_slide_inputs_manifest",
    "build_prompt_identifier",
    "slugify_prompt_layout",
]
