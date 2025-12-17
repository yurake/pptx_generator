from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from pydantic import ValidationError

from pptx_generator.models import (
    JobSpec,
    JobMeta,
    JobAuth,
    SpecValidationError,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateSpec,
)
from pptx_generator.pipeline import PipelineContext, PipelineStage
from pptx_generator.cli_handlers.trace_utils import record_stage_trace
from pptx_generator.content_import import ContentImportError, ContentImportResult, ContentImportService
from pptx_generator.prepare import PrepareCard, PrepareDocument
from pptx_generator.prepare.source import (
    PrepareSourceChapter,
    PrepareSourceDocument,
    PrepareSourceMeta,
    PrepareSourceSupportingPoint,
)
from pptx_generator.prepare.models import PrepareGenerationMeta
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
    prepare_inputs: tuple[str, ...]
    output_dir: Path
    jobspec_path: Path | None
    mode: str
    page_limit: int | None
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
    source_metadata: list[dict[str, Any]] = []
    import_messages: list[str] = []

    if config.prepare_inputs:
        source_document, source_metadata, import_messages = _load_prepare_inputs(config.prepare_inputs)

    if source_document is None:
        if config.prepare_path is not None:
            source_document = _load_prepare_source(config.prepare_path)
            source_metadata.append(
                _build_structured_source_meta(config.prepare_path, source_document)
            )
        elif normalized_mode != "static":
            raise PrepareCommandError(
                "dynamic モードではプレペア入力を指定する必要があります", exit_code=2
            )

    static_context = resolve_static_context(
        jobspec_path=config.jobspec_path,
        default_jobspec_path=config.default_jobspec_path,
        prompts_dirname=config.prompts_dirname,
        slide_inputs_filename=config.slide_inputs_filename,
        mode=normalized_mode,
        prepare_path=config.prepare_path,
        has_inline_source=source_document is not None,
    )

    if static_context.import_metadata:
        source_metadata.extend(static_context.import_metadata)

    if source_document is None and static_context.source_document is not None:
        source_document = static_context.source_document
        if static_context.template_spec_path is not None:
            source_metadata.append(
                {
                    "source": str(static_context.template_spec_path),
                    "kind": "template_spec",
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    orchestrator = PrepareAIOrchestrator()
    try:
        document, meta, ai_logs = orchestrator.generate_document(
            source_document,
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

    if source_metadata:
        meta.import_sources = source_metadata

    artifacts = PrepareCommandArtifacts.initialize(config.output_dir)
    combined_messages = list(static_context.messages)
    combined_messages.extend(import_messages)
    result = artifacts.write_outputs(
        document=document,
        meta=meta,
        ai_logs=ai_logs,
        dump_json=dump_json,
        static_context=static_context,
        messages=combined_messages,
        import_metadata=source_metadata,
    )
    # trace: prepare stage
    stub_spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="prepare"),
        auth=JobAuth(created_by="cli"),
        slides=[],
    )
    context = PipelineContext(spec=stub_spec, workdir=config.output_dir)
    context.current_stage = PipelineStage.PREPARE
    record_stage_trace(context=context, stage="prepare", output_dir=config.output_dir)
    return result


@dataclass(slots=True)
class PrepareStaticContext:
    blueprint_spec: TemplateSpec | None
    blueprint_ref: dict[str, str] | None
    template_spec_path: Path | None
    prompt_overrides: list[StaticPromptOverride]
    slide_input_sources: dict[str, PrepareSourceDocument] | None
    slide_input_refs: dict[str, str] | None
    source_document: PrepareSourceDocument | None
    messages: list[str]
    import_metadata: list[dict[str, Any]]


@dataclass(slots=True)
class PrepareCommandArtifacts:
    output_dir: Path
    cards_path: Path
    log_path: Path
    ai_log_path: Path
    meta_path: Path
    story_outline_path: Path
    audit_path: Path

    @classmethod
    def initialize(cls, output_dir: Path) -> "PrepareCommandArtifacts":
        output_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            output_dir=output_dir,
            cards_path=output_dir / "prepare_card.json",
            log_path=output_dir / "prepare_log.json",
            ai_log_path=output_dir / "prepare_ai_log.json",
            meta_path=output_dir / "ai_generation_meta.json",
            story_outline_path=output_dir / "prepare_story_outline.json",
            audit_path=output_dir / "audit_log.json",
        )

    def write_outputs(
        self,
        *,
        document: PrepareDocument,
        meta: PrepareGenerationMeta,
        ai_logs: Sequence[Any],
        dump_json: Callable[[Path, object], None],
        static_context: PrepareStaticContext,
        messages: list[str],
        import_metadata: list[dict[str, Any]] | None = None,
    ) -> PrepareCommandResult:
        document.meta = dict(document.meta or {})
        document.meta.update(
            {
                "prepare_card_path": _relativize(self.cards_path, self.output_dir),
                "prepare_log_path": _relativize(self.log_path, self.output_dir),
                "prepare_ai_log_path": _relativize(self.ai_log_path, self.output_dir),
                "ai_generation_meta_path": _relativize(self.meta_path, self.output_dir),
                "prepare_story_outline_path": _relativize(self.story_outline_path, self.output_dir),
                "prepare_audit_log_path": _relativize(self.audit_path, self.output_dir),
            }
        )

        dump_json(self.cards_path, document.model_dump(mode="json", exclude_none=True))
        dump_json(self.log_path, [])
        dump_json(
            self.ai_log_path,
            [record.model_dump(mode="json", exclude_none=True) for record in ai_logs],
        )
        dump_json(self.meta_path, meta.model_dump(mode="json", exclude_none=True))
        dump_json(self.story_outline_path, _build_prepare_story_outline(document))

        audit_payload: dict[str, Any] = {
            "prepare_normalization": {
                "generated_at": meta.generated_at.isoformat(),
                "policy_id": meta.policy_id,
                "input_hash": meta.input_hash,
                "mode": meta.mode,
                "outputs": {
                    "prepare_card": str(self.cards_path.resolve()),
                    "prepare_log": str(self.log_path.resolve()),
                    "prepare_ai_log": str(self.ai_log_path.resolve()),
                    "ai_generation_meta": str(self.meta_path.resolve()),
                    "prepare_story_outline": str(self.story_outline_path.resolve()),
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
        if import_metadata:
            audit_payload["prepare_normalization"]["import_sources"] = import_metadata
        dump_json(self.audit_path, audit_payload)

        return PrepareCommandResult(
            cards_path=self.cards_path,
            log_path=self.log_path,
            ai_log_path=self.ai_log_path,
            meta_path=self.meta_path,
            story_outline_path=self.story_outline_path,
            audit_path=self.audit_path,
            messages=messages,
        )


def resolve_static_context(
    *,
        jobspec_path: Path | None,
        default_jobspec_path: Path,
        prompts_dirname: Path,
        slide_inputs_filename: Path,
        mode: str,
        prepare_path: Path | None,
        has_inline_source: bool,
) -> PrepareStaticContext:
    if mode != "static":
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
                document, per_source_meta, per_source_messages = _load_prepare_input(str(data_path), service)
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


def _load_prepare_source(path: Path) -> PrepareSourceDocument:
    try:
        return PrepareSourceDocument.parse_file(path)
    except FileNotFoundError as exc:
        raise PrepareCommandError(f"プレペア入力ファイルが見つかりません: {exc}", exit_code=2) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PrepareCommandError(f"プレペア入力の解析に失敗しました: {exc}", exit_code=2) from exc
    except UnicodeDecodeError as exc:
        raise PrepareCommandError(f"プレペア入力ファイルを UTF-8 として解釈できません: {exc}", exit_code=2) from exc


def _load_prepare_inputs(
    inputs: Sequence[str],
) -> tuple[PrepareSourceDocument | None, list[dict[str, Any]], list[str]]:
    if not inputs:
        return None, [], []

    service = ContentImportService()
    documents: list[PrepareSourceDocument] = []
    metadata: list[dict[str, Any]] = []
    messages: list[str] = []

    for raw in inputs:
        value = raw.strip()
        if not value:
            continue
        document, per_source_meta, per_source_messages = _load_prepare_input(value, service)
        documents.append(document)
        metadata.extend(per_source_meta)
        messages.extend(per_source_messages)

    if not documents:
        return None, metadata, messages

    combined_document = _combine_prepare_documents(documents)
    normalized_document = _normalize_import_chapter_ids(combined_document)
    return normalized_document, metadata, messages


def _load_prepare_input(
    value: str,
    service: ContentImportService,
) -> tuple[PrepareSourceDocument, list[dict[str, Any]], list[str]]:
    lower_value = value.lower()
    if lower_value.startswith("http://"):
        raise PrepareCommandError(
            "http:// は許可されていません。HTTPS を利用してください",
            exit_code=2,
        )
    is_url = lower_value.startswith("https://")
    is_data_uri = lower_value.startswith("data:")
    candidate_path = Path(value).expanduser()
    path_exists = candidate_path.exists() and candidate_path.is_file()

    if path_exists and candidate_path.suffix.lower() not in {".pdf", ".html", ".htm"}:
        try:
            document = PrepareSourceDocument.parse_file(candidate_path)
        except UnicodeDecodeError:
            document, imported_meta, import_messages = _import_via_service(service, str(candidate_path))
            messages = [f"インポートを完了しました: {candidate_path}", *import_messages]
            return document, imported_meta, messages
        except (json.JSONDecodeError, ValidationError) as exc:
            if candidate_path.suffix.lower() in {".json", ".jsonc"}:
                raise PrepareCommandError(f"プレペア入力の解析に失敗しました: {exc}", exit_code=2) from exc
            document, imported_meta, import_messages = _import_via_service(service, str(candidate_path))
            messages = [f"インポートを完了しました: {candidate_path}", *import_messages]
            return document, imported_meta, messages

        metadata = [_build_structured_source_meta(candidate_path, document)]
        messages = [f"プレペア入力を読み込みました: {candidate_path}"]
        return document, metadata, messages

    if is_url or is_data_uri or path_exists:
        document, imported_meta, import_messages = _import_via_service(service, value)
        messages = [f"インポートを完了しました: {value}", *import_messages]
        return document, imported_meta, messages

    raise PrepareCommandError(f"プレペア入力を解釈できません: {value}", exit_code=2)


def _import_via_service(
    service: ContentImportService,
    source: str,
) -> tuple[PrepareSourceDocument, list[dict[str, Any]], list[str]]:
    try:
        result = service.import_sources([source])
    except ContentImportError as exc:
        raise PrepareCommandError(f"入力ソースの取り込みに失敗しました: {exc}", exit_code=2) from exc

    document = _convert_import_result_to_prepare_source(result, source)
    metadata: list[dict[str, Any]] = []
    sources_meta = result.meta.get("sources") if isinstance(result.meta, dict) else None
    if isinstance(sources_meta, list):
        for entry in sources_meta:
            if isinstance(entry, dict):
                copied = dict(entry)
                copied.setdefault("via", "content_import")
                metadata.append(copied)
    if not metadata:
        metadata.append(
            {
                "source": source,
                "kind": "import",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "via": "content_import",
            }
        )

    warning_messages = [f"警告: {warning}" for warning in result.warnings]
    return document, metadata, warning_messages


def _convert_import_result_to_prepare_source(
    result: ContentImportResult,
    source_label: str,
) -> PrepareSourceDocument:
    summary = (
        result.document.meta.summary
        if result.document.meta and result.document.meta.summary
        else source_label
    )
    meta = PrepareSourceMeta(
        title=summary[:120] if summary else "Imported Source",
        prepare_id=None,
        objective=None,
    )

    chapters: list[PrepareSourceChapter] = []
    raw_lines: list[str] = []

    for index, slide in enumerate(result.document.slides, start=1):
        title = slide.elements.title or f"{summary or 'Import'} {index:02d}"
        body_lines = [line.strip() for line in (slide.elements.body or []) if line.strip()]
        message = body_lines[0] if body_lines else title
        supporting_points = [
            PrepareSourceSupportingPoint(statement=line)
            for line in body_lines[1:]
        ]
        chapter = PrepareSourceChapter(
            id=f"import-{index:02d}",
            title=title[:120],
            message=message,
            details=body_lines,
            supporting_points=supporting_points,
            story_hint=None,
            intent_tags=["imported"],
        )
        chapters.append(chapter)
        raw_lines.append(title)
        raw_lines.extend(body_lines)
        if slide.elements.note:
            raw_lines.append(slide.elements.note.strip())

    raw_text = "\n".join(raw_lines).strip() or None
    return PrepareSourceDocument(meta=meta, chapters=chapters, raw_text=raw_text)


def _combine_prepare_documents(documents: Sequence[PrepareSourceDocument]) -> PrepareSourceDocument:
    if not documents:
        raise ValueError("documents must not be empty")
    if len(documents) == 1:
        single = documents[0]
        return PrepareSourceDocument(
            meta=single.meta.model_copy(deep=True),
            chapters=[chapter.model_copy(deep=True) for chapter in single.chapters],
            raw_text=single.raw_text,
        )

    base_meta = documents[0].meta.model_copy(deep=True)
    chapters: list[PrepareSourceChapter] = []
    raw_texts: list[str] = []
    objectives: list[str] = []

    for doc in documents:
        chapters.extend(chapter.model_copy(deep=True) for chapter in doc.chapters)
        if doc.raw_text:
            raw_texts.append(doc.raw_text)
        if doc.meta.objective:
            objectives.append(doc.meta.objective)

    if objectives:
        base_meta.objective = "\n\n".join(objectives)

    raw_text = "\n\n".join(text for text in raw_texts if text.strip()) or None

    return PrepareSourceDocument(meta=base_meta, chapters=chapters, raw_text=raw_text)


def _normalize_import_chapter_ids(document: PrepareSourceDocument) -> PrepareSourceDocument:
    next_index = 1
    seen_ids: set[str] = set()
    normalized_chapters: list[PrepareSourceChapter] = []
    changed = False

    for chapter in document.chapters:
        new_id = chapter.id
        if new_id.startswith("import-"):
            new_id = f"import-{next_index:02d}"
            next_index += 1
            while new_id in seen_ids:
                new_id = f"import-{next_index:02d}"
                next_index += 1
            if new_id != chapter.id:
                changed = True
        elif new_id in seen_ids:
            # structured ドキュメントの重複 ID はそのまま保持する
            pass

        seen_ids.add(new_id)
        if new_id == chapter.id:
            normalized_chapters.append(chapter)
            continue
        normalized_chapters.append(chapter.model_copy(update={"id": new_id}))

    if not changed:
        return document

    return PrepareSourceDocument(
        meta=document.meta.model_copy(deep=True),
        chapters=[chapter.model_copy(deep=True) for chapter in normalized_chapters],
        raw_text=document.raw_text,
    )


def _build_structured_source_meta(
    path: Path,
    document: PrepareSourceDocument,
) -> dict[str, Any]:
    try:
        raw_bytes = path.read_bytes()
    except OSError:
        raw_bytes = b""
    hash_value = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None
    metadata = {
        "source": str(path),
        "kind": "file",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "hash": f"sha256:{hash_value}" if hash_value else None,
        "chapters": len(document.chapters),
        "content_type": _guess_structured_content_type(path.suffix.lower()),
        "via": "structured",
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _guess_structured_content_type(suffix: str) -> str:
    mapping = {
        ".json": "application/json",
        ".jsonc": "application/json",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
    }
    return mapping.get(suffix, "text/plain")


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


def load_prompt_overrides(
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


_load_prompt_overrides = load_prompt_overrides


_resolve_static_context = resolve_static_context


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
        return card.role.story_phase or card.card_id or "unlabeled"

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
