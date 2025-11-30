from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from pptx_generator.models import (
    JobSpec,
    SpecValidationError,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateSpec,
)
from pptx_generator.prepare import (
    PrepareCard,
    PrepareDocument,
    PreparePolicyError,
    PrepareSourceDocument,
    load_prepare_policy_set,
)
from pptx_generator.prepare_ai import (
    PrepareAIOrchestrationError,
    PrepareAIOrchestrator,
    StaticPromptOverride,
)
from pptx_generator.spec_loader import load_jobspec_from_path

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_FILENAME_PATTERN = re.compile(r"^(?P<index>\d{2})_(?P<slug>[a-z0-9\-]+)\.md$", re.IGNORECASE)
PROMPT_USER_SECTION_START = "<<<user-editable:start"
PROMPT_USER_SECTION_END = "<<<user-editable:end"
PROMPT_DEFAULT_LINES = {
    "- 例: このスライドでは ROI の定量値を箇条書きで入れる",
    "- 例: リスクを最低 2 点列挙する",
}
SLIDE_INPUTS_FILENAME = Path("slide_inputs.md")


class PrepareCommandError(Exception):
    """エラー種別に応じて CLI へ exit code を伝えるための例外。"""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(slots=True)
class PrepareCommandConfig:
    prepare_path: Path | None
    output_dir: Path
    jobspec_path: Path | None
    mode: str
    page_limit: int | None
    policy_path: Path
    default_jobspec_path: Path
    prompts_dirname: Path
    slide_inputs_filename: Path


@dataclass(slots=True)
class PrepareCommandResult:
    cards_path: Path
    log_path: Path
    ai_log_path: Path
    meta_path: Path
    story_outline_path: Path
    audit_path: Path
    messages: list[str]


def run_prepare_command(
    config: PrepareCommandConfig,
    *,
    dump_json: Callable[[Path, object], None],
) -> PrepareCommandResult:
    normalized_mode = config.mode.lower()
    if normalized_mode not in {"dynamic", "static"}:
        raise PrepareCommandError("--mode には dynamic か static を指定してください", exit_code=2)
    if normalized_mode == "static" and config.page_limit is not None:
        raise PrepareCommandError("static モードでは --page-limit を利用できません", exit_code=2)

    source_document: PrepareSourceDocument | None = None
    if config.prepare_path is not None:
        source_document = _load_prepare_source(config.prepare_path)
    elif normalized_mode != "static":
        raise PrepareCommandError(
            "dynamic モードではプレペア入力ファイルを指定する必要があります", exit_code=2
        )

    policy_set = _load_prepare_policy(config.policy_path)

    static_context = _resolve_static_context(
        jobspec_path=config.jobspec_path,
        default_jobspec_path=config.default_jobspec_path,
        prompts_dirname=config.prompts_dirname,
        slide_inputs_filename=config.slide_inputs_filename,
        mode=normalized_mode,
        prepare_path=config.prepare_path,
    )

    if source_document is None and static_context.source_document is not None:
        source_document = static_context.source_document

    orchestrator = PrepareAIOrchestrator(policy_set)
    try:
        document, meta, ai_logs = orchestrator.generate_document(
            source_document,
            policy_id=None,
            page_limit=config.page_limit,
            mode=normalized_mode,  # type: ignore[arg-type]
            blueprint=static_context.blueprint_spec.blueprint if static_context.blueprint_spec else None,
            blueprint_ref=static_context.blueprint_ref,
            prompt_overrides=static_context.prompt_overrides,
            slide_sources=static_context.slide_input_sources,
            slide_input_refs=static_context.slide_input_refs,
        )
    except PrepareAIOrchestrationError as exc:
        exit_code = 6 if normalized_mode == "static" else 4
        raise PrepareCommandError(f"プレペアカードの生成に失敗しました: {exc}", exit_code=exit_code) from exc

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    cards_path = output_dir / "prepare_card.json"
    log_path = output_dir / "prepare_log.json"
    ai_log_path = output_dir / "prepare_ai_log.json"
    meta_path = output_dir / "ai_generation_meta.json"
    story_outline_path = output_dir / "prepare_story_outline.json"
    audit_path = output_dir / "audit_log.json"

    document.meta = dict(document.meta or {})
    document.meta.update(
        {
            "prepare_card_path": _relativize(cards_path, output_dir),
            "prepare_log_path": _relativize(log_path, output_dir),
            "prepare_ai_log_path": _relativize(ai_log_path, output_dir),
            "ai_generation_meta_path": _relativize(meta_path, output_dir),
            "prepare_story_outline_path": _relativize(story_outline_path, output_dir),
            "prepare_audit_log_path": _relativize(audit_path, output_dir),
        }
    )

    dump_json(cards_path, document.model_dump(mode="json", exclude_none=True))
    dump_json(log_path, [])
    dump_json(
        ai_log_path,
        [record.model_dump(mode="json", exclude_none=True) for record in ai_logs],
    )
    dump_json(meta_path, meta.model_dump(mode="json", exclude_none=True))
    dump_json(story_outline_path, _build_prepare_story_outline(document))

    audit_payload: dict[str, Any] = {
        "prepare_normalization": {
            "generated_at": meta.generated_at.isoformat(),
            "policy_id": meta.policy_id,
            "input_hash": meta.input_hash,
            "mode": meta.mode,
            "outputs": {
                "prepare_card": str(cards_path.resolve()),
                "prepare_log": str(log_path.resolve()),
                "prepare_ai_log": str(ai_log_path.resolve()),
                "ai_generation_meta": str(meta_path.resolve()),
                "prepare_story_outline": str(story_outline_path.resolve()),
            },
            "statistics": meta.statistics,
        }
    }
    if static_context.template_spec_path is not None:
        audit_payload["prepare_normalization"]["outputs"]["template_spec"] = str(
            static_context.template_spec_path
        )
    if static_context.blueprint_ref is not None:
        audit_payload["prepare_normalization"]["blueprint"] = static_context.blueprint_ref
    if meta.slot_coverage:
        audit_payload["prepare_normalization"]["slot_summary"] = meta.slot_coverage
    dump_json(audit_path, audit_payload)

    return PrepareCommandResult(
        cards_path=cards_path,
        log_path=log_path,
        ai_log_path=ai_log_path,
        meta_path=meta_path,
        story_outline_path=story_outline_path,
        audit_path=audit_path,
        messages=static_context.messages,
    )


@dataclass(slots=True)
class _StaticPrepareContext:
    blueprint_spec: TemplateSpec | None
    blueprint_ref: dict[str, str] | None
    template_spec_path: Path | None
    prompt_overrides: list[StaticPromptOverride]
    slide_input_sources: dict[str, PrepareSourceDocument] | None
    slide_input_refs: dict[str, str] | None
    source_document: PrepareSourceDocument | None
    messages: list[str]


def _resolve_static_context(
    *,
    jobspec_path: Path | None,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path,
    mode: str,
    prepare_path: Path | None,
) -> _StaticPrepareContext:
    if mode != "static":
        return _StaticPrepareContext(
            blueprint_spec=None,
            blueprint_ref=None,
            template_spec_path=None,
            prompt_overrides=[],
            slide_input_sources=None,
            slide_input_refs=None,
            source_document=None,
            messages=[],
        )

    resolved_jobspec = jobspec_path or default_jobspec_path
    if not resolved_jobspec.exists():
        raise PrepareCommandError(
            "static モードでは --jobspec で jobspec.json のパスを指定するか、.pptx/extract/jobspec.json を用意してください",
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
    }

    prompt_overrides = _load_prompt_overrides(
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
    if slide_manifest.exists():
        try:
            slide_input_paths = _load_slide_inputs_manifest(
                manifest_path=slide_manifest,
                blueprint=blueprint_spec.blueprint,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise PrepareCommandError(f"slide_inputs の読み込みに失敗しました: {exc}", exit_code=2) from exc

        slide_input_sources = {}
        slide_input_refs = {}
        for slide_id, data_path in slide_input_paths.items():
            try:
                parsed = PrepareSourceDocument.parse_file(data_path)
            except (FileNotFoundError, json.JSONDecodeError, ValidationError) as exc:
                raise PrepareCommandError(f"{data_path} の読み込みに失敗しました: {exc}", exit_code=2) from exc
            slide_input_sources[slide_id] = parsed
            slide_input_refs[slide_id] = str(data_path)
            if first_source is None:
                first_source = parsed

        messages.append(f"スライド入力マニフェストを利用します: {slide_manifest}")
    elif prepare_path is None:
        raise PrepareCommandError(
            ".pptx/slide_inputs.md が見つかりません。プレペア入力ファイルを指定するか、マニフェストを用意してください",
            exit_code=2,
        )

    return _StaticPrepareContext(
        blueprint_spec=blueprint_spec,
        blueprint_ref=blueprint_ref,
        template_spec_path=template_spec_path,
        prompt_overrides=prompt_overrides,
        slide_input_sources=slide_input_sources,
        slide_input_refs=slide_input_refs,
        source_document=first_source,
        messages=messages,
    )


def _load_prepare_source(path: Path) -> PrepareSourceDocument:
    try:
        return PrepareSourceDocument.parse_file(path)
    except FileNotFoundError as exc:
        raise PrepareCommandError(f"プレペア入力ファイルが見つかりません: {exc}", exit_code=2) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PrepareCommandError(f"プレペア入力の解析に失敗しました: {exc}", exit_code=2) from exc


def _load_prepare_policy(path: Path) -> Any:
    try:
        return load_prepare_policy_set(path)
    except PreparePolicyError as exc:
        raise PrepareCommandError(f"プレペアポリシーの読み込みに失敗しました: {exc}", exit_code=4) from exc


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


def _load_prompt_overrides(
    *,
    prompts_dir: Path,
    blueprint: TemplateBlueprint,
) -> list[StaticPromptOverride]:
    if not prompts_dir.exists() or not prompts_dir.is_dir():
        return []

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
        override = StaticPromptOverride(
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


def _relativize(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _build_prepare_story_outline(document: PrepareDocument) -> dict[str, Any]:
    chapter_cards: dict[str, list[str]] = {}

    def resolve_bucket(card: PrepareCard) -> str:
        if isinstance(card.meta, dict):
            source_chapter = card.meta.get("source_chapter")
            if isinstance(source_chapter, dict):
                source_id = source_chapter.get("id")
                source_title = source_chapter.get("title")
                if isinstance(source_id, str) and source_id.strip():
                    return source_id.strip()
                if isinstance(source_title, str) and source_title.strip():
                    return source_title.strip()
        blueprint = card.blueprint_meta()
        if blueprint and blueprint.get("slide_id"):
            return str(blueprint.get("slide_id"))
        return card.role.story_phase

    for card in document.cards:
        bucket = resolve_bucket(card)
        chapter_cards.setdefault(bucket, []).append(card.card_id)

    chapters_payload: list[dict[str, Any]] = []
    for chapter in document.story_context.chapters:
        cards = chapter_cards.pop(chapter.id, [])
        if not cards:
            cards = chapter_cards.pop(chapter.title, [])
        chapters_payload.append(
            {
                "id": chapter.id,
                "title": chapter.title,
                "cards": cards,
            }
        )

    for title, cards in chapter_cards.items():
        chapters_payload.append({"id": title, "title": title, "cards": cards})

    return {
        "prepare_id": document.prepare_id,
        "chapters": chapters_payload,
        "narrative_theme": None,
        "summary": None,
    }
