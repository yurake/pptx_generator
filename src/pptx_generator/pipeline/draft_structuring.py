"""工程4 ドラフト構成設計ステップ。"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..brief.models import BriefCard, BriefDocument, BriefGenerationMeta
from ..models import (
    ContentApprovalDocument,
    ContentSlide,
    DraftAnalyzerSummary,
    DraftDocument,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    DraftLayoutCandidate,
    GenerateReadyDocument,
    GenerateReadyMeta,
    GenerateReadySlide,
    JobAuth,
    JobMeta,
    JobSpec,
    MappingSlideMeta,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateBlueprintSlot,
    Slide,
    TemplateSpec,
)
from ..draft_recommender import (
    CardLayoutRecommender,
    CardLayoutRecommenderConfig,
    LayoutProfile,
)
from ..utils.usage_tags import normalize_usage_tags
from ..api.draft_store import DraftStore, BoardAlreadyExistsError
from ..draft_intel import (
    ChapterTemplate,
    ChapterTemplateEvaluation,
    evaluate_chapter_template,
    find_template_by_structure,
    load_analysis_summary,
    load_chapter_template,
    summarize_analyzer_counts,
)
from .base import PipelineContext
from .slide_alignment import SlideIdAligner, SlideIdAlignerOptions

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DraftStructuringOptions:
    """ドラフト構成ステップの設定。"""

    layouts_path: Path | None = None
    output_dir: Path | None = None
    spec_source_path: Path | None = None
    draft_filename: str = "draft_draft.json"
    approved_filename: str = "draft_approved.json"
    log_filename: str = "draft_review_log.json"
    generate_ready_filename: str = "generate_ready.json"
    generate_ready_meta_filename: str = "generate_ready_meta.json"
    mapping_log_filename: str = "draft_mapping_log.json"
    target_length: int | None = None
    structure_pattern: str | None = None
    appendix_limit: int = 5
    chapter_templates_dir: Path | None = None
    chapter_template_id: str | None = None
    analysis_summary_path: Path | None = None
    enable_ai_recommender: bool = True
    ai_weight: float = 0.25
    diversity_weight: float = 0.05
    max_layout_candidates: int = 5
    layout_ai_policy_path: Path | None = Path("config/layout_ai_policies.json")
    layout_ai_policy_id: str | None = "layout-default"
    enable_ai_simulation: bool = True
    enable_slide_alignment: bool = True
    slide_alignment_threshold: float = 0.6
    slide_alignment_max_candidates: int = 12
    layout_ai_policy_path: Path | None = Path("config/layout_ai_policies.json")
    layout_ai_policy_id: str | None = "layout-default"
    enable_ai_simulation: bool = True


@dataclass(slots=True)
class StaticArtifacts:
    draft: DraftDocument
    generate_ready: GenerateReadyDocument
    mapping_log: dict[str, Any]
    ai_summary: dict[str, Any]
    slot_summary: dict[str, int]


class DraftStructuringError(RuntimeError):
    """ドラフト構成処理の失敗を表す。"""


class DraftStructuringStep:
    """content_approved と layouts.jsonl から Draft ドキュメントを生成する。"""

    name = "draft_structuring"

    def __init__(self, options: DraftStructuringOptions | None = None) -> None:
        self.options = options or DraftStructuringOptions()
        self._recommender: CardLayoutRecommender | None = None
        self._alignment_records: list | None = None
        self._layout_name_lookup: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def run(self, context: PipelineContext) -> None:
        artifact = context.artifacts.get("content_approved")
        if artifact is None:
            logger.info("content_approved が存在しないため draft_structuring をスキップします")
            return
        if not isinstance(artifact, ContentApprovalDocument):
            msg = "content_approved artifact の型が不正です"
            raise DraftStructuringError(msg)
        document = artifact

        brief_generation_meta = context.artifacts.get("brief_generation_meta")
        if isinstance(brief_generation_meta, BriefGenerationMeta) and (brief_generation_meta.mode or "dynamic") == "static":
            self._run_static_mode(
                context=context,
                content_document=document,
                brief_meta=brief_generation_meta,
            )
            return

        self._alignment_records = None
        alignment_records = []
        if self.options.enable_slide_alignment:
            aligner = SlideIdAligner(
                SlideIdAlignerOptions(
                    confidence_threshold=self.options.slide_alignment_threshold,
                    max_candidates=self.options.slide_alignment_max_candidates,
                )
            )
            brief_document = context.artifacts.get("brief_document")
            alignment = aligner.align(
                spec=context.spec,
                brief_document=brief_document if isinstance(brief_document, BriefDocument) else None,
                content_document=document,
            )
            document = alignment.document
            alignment_records = alignment.records
            context.add_artifact("content_alignment_meta", alignment.meta)
            context.add_artifact(
                "content_alignment_records",
                [asdict(record) for record in alignment.records],
            )
            context.add_artifact("content_approved", document)
        pending_cards = [record.card_id for record in alignment_records if record.status == "pending"]
        if pending_cards:
            logger.error("Slide alignment 未確定カード: %s", ", ".join(sorted(set(pending_cards))))
            msg = "Slide alignment に失敗したカードがあります: " + ", ".join(sorted(set(pending_cards)))
            raise DraftStructuringError(msg)

        layouts = self._load_layouts(self.options.layouts_path)
        self._layout_name_lookup = {profile.layout_id: profile.layout_name for profile in layouts}
        analyzer_map = load_analysis_summary(self.options.analysis_summary_path) if self.options.analysis_summary_path else {}
        template: ChapterTemplate | None = None
        if self.options.chapter_templates_dir:
            if self.options.chapter_template_id:
                template = load_chapter_template(self.options.chapter_templates_dir, self.options.chapter_template_id)
            elif self.options.structure_pattern:
                template = find_template_by_structure(self.options.chapter_templates_dir, self.options.structure_pattern)
        recommender = self._resolve_recommender()
        draft, mapping_logs, ai_summary = self._build_document(
            spec=context.spec,
            document=document,
            layouts=layouts,
            analyzer_map=analyzer_map,
            chapter_template=template,
            recommender=recommender,
        )

        output_dir = self.options.output_dir or context.workdir
        output_dir.mkdir(parents=True, exist_ok=True)

        draft_path = output_dir / self.options.draft_filename
        approved_path = output_dir / self.options.approved_filename
        log_path = output_dir / self.options.log_filename
        mapping_log_path = output_dir / self.options.mapping_log_filename

        self._write_document(draft_path, draft)
        self._write_document(approved_path, draft)
        self._write_log(log_path, [])
        self._write_json(mapping_log_path, mapping_logs)

        generate_ready = self._build_generate_ready_document(
            spec=context.spec,
            draft=draft,
            content_document=document,
        )
        ready_path = output_dir / self.options.generate_ready_filename
        self._write_json(ready_path, generate_ready.model_dump(mode="json"))
        context.add_artifact("generate_ready", generate_ready)
        context.add_artifact("generate_ready_path", str(ready_path))

        ready_meta_payload = self._build_generate_ready_meta_payload(
            draft=draft,
            generate_ready=generate_ready,
            ai_summary=ai_summary,
        )
        ready_meta_path = output_dir / self.options.generate_ready_meta_filename
        self._write_json(ready_meta_path, ready_meta_payload)
        context.add_artifact("generate_ready_meta_path", str(ready_meta_path))

        context.add_artifact("draft_document", draft)
        context.add_artifact("draft_document_path", str(approved_path))
        context.add_artifact("draft_review_log_path", str(log_path))
        context.add_artifact("draft_mapping_log_path", str(mapping_log_path))

        spec_id = self._spec_id_from_title(getattr(context.spec.meta, "title", None))
        context.add_artifact("draft_spec_id", spec_id)

        store = DraftStore()
        try:
            store.create_board(spec_id, draft)
        except BoardAlreadyExistsError:
            store.overwrite_board(spec_id, draft)

        logger.info(
            "Draft ドキュメントを生成しました: sections=%d",
            len(draft.sections),
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _resolve_recommender(self) -> CardLayoutRecommender:
        config = CardLayoutRecommenderConfig(
            enable_ai=self.options.enable_ai_recommender,
            ai_weight=self.options.ai_weight,
            diversity_weight=self.options.diversity_weight,
            max_candidates=self.options.max_layout_candidates,
            policy_path=self.options.layout_ai_policy_path,
            policy_id=self.options.layout_ai_policy_id,
            enable_simulated_ai=self.options.enable_ai_simulation,
        )
        self._recommender = CardLayoutRecommender(config)
        return self._recommender

    def _load_layouts(self, path: Path | None) -> list[LayoutProfile]:
        if path is None:
            source_hint = (
                str(self.options.spec_source_path)
                if self.options.spec_source_path is not None
                else "in-memory JobSpec"
            )
            logger.info(
                "layouts.jsonl が指定されていないため、JobSpec (%s) の layout を基準にしたヒューリスティック候補を使用します",
                source_hint,
            )
            return []

        records: list[LayoutProfile] = []
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"layouts.jsonl を読み込めません: {path}"
            raise DraftStructuringError(msg) from exc

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"layouts.jsonl の解析に失敗しました: {path}"
                raise DraftStructuringError(msg) from exc

            layout_id = payload.get("layout_id")
            if not layout_id:
                logger.debug("layout_id が存在しないレコードをスキップ: %s", payload)
                continue

            text_hint = payload.get("text_hint") or {}
            media_hint = payload.get("media_hint") or {}
            if not isinstance(text_hint, dict):
                text_hint = {}
            if not isinstance(media_hint, dict):
                media_hint = {}

            record = LayoutProfile(
                layout_id=layout_id,
                layout_name=payload.get("layout_name") or layout_id,
                usage_tags=normalize_usage_tags(payload.get("usage_tags", [])),
                text_hint=text_hint,
                media_hint=media_hint,
            )
            records.append(record)
        return records

    def _build_document(
        self,
        *,
        spec: JobSpec,
        document: ContentApprovalDocument,
        layouts: Sequence[LayoutProfile],
        analyzer_map: dict[str, DraftAnalyzerSummary],
        chapter_template: ChapterTemplate | None,
        recommender: CardLayoutRecommender,
    ) -> tuple[DraftDocument, list[dict[str, Any]], dict[str, Any]]:
        slides_by_id = {slide.id: slide for slide in document.slides}

        sections: list[DraftSection] = []
        section_map: dict[str, DraftSection] = {}
        mapping_logs: list[dict[str, Any]] = []
        ai_summary: dict[str, Any] = {
            "invoked": 0,
            "used": 0,
            "simulated": 0,
            "models": {},
        }

        for index, spec_slide in enumerate(spec.slides, start=1):
            content_slide = slides_by_id.get(spec_slide.id)
            if content_slide is None:
                logger.debug("content_approved に存在しないスライドをスキップ: %s", spec_slide.id)
                continue

            section_key, section_name = self._resolve_section(content_slide, spec_slide)
            section = section_map.get(section_key)
            if section is None:
                section = DraftSection(
                    name=section_name,
                    order=len(section_map) + 1,
                    status="draft",
                )
                section_map[section_key] = section
                sections.append(section)

            card_order = len(section.slides) + 1
            analyzer_summary = analyzer_map.get(content_slide.id)
            recommendation, card = self._build_card(
                content_slide,
                spec_slide.layout,
                layouts,
                order=card_order,
                analyzer_summary=analyzer_summary,
                recommender=recommender,
            )
            section.slides.append(card)

            ai_scores = recommendation.ai_scores
            selected_layout = card.layout_hint
            ai_used = selected_layout in ai_scores and ai_scores[selected_layout] > 0.0
            if ai_used:
                ai_summary["used"] += 1

            if recommendation.ai_response is not None:
                ai_summary["invoked"] += 1
                model = recommendation.ai_response.model or "unknown"
                model_counts = ai_summary["models"]
                model_counts[model] = model_counts.get(model, 0) + 1
            elif (
                self.options.enable_ai_recommender
                and self.options.enable_ai_simulation
                and self.options.ai_weight > 0
                and not ai_scores
                and any(detail.ai_recommendation > 0.0 for _, detail in recommendation.candidates)
            ):
                ai_summary["simulated"] += 1

            candidate_logs: list[dict[str, Any]] = []
            for candidate, detail in recommendation.candidates:
                candidate_logs.append(
                    {
                        "layout_id": candidate.layout_id,
                        "score": candidate.score,
                        "ai_score": ai_scores.get(candidate.layout_id, 0.0),
                        "detail": {
                            "uses_tag": detail.uses_tag,
                            "content_capacity": detail.content_capacity,
                            "diversity": detail.diversity,
                            "analyzer_support": detail.analyzer_support,
                            "ai_recommendation": detail.ai_recommendation,
                        },
                    }
                )

            ai_response_payload: dict[str, Any] | None = None
            if recommendation.ai_response is not None:
                ai_response_payload = {
                    "model": recommendation.ai_response.model,
                    "recommended": recommendation.ai_response.recommended,
                    "reasons": recommendation.ai_response.reasons,
                }
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "layout AI response: slide_id=%s model=%s recommended=%s reasons=%s",
                        content_slide.id,
                        recommendation.ai_response.model,
                        recommendation.ai_response.recommended,
                        recommendation.ai_response.reasons,
                    )
            elif (
                self.options.enable_ai_recommender
                and self.options.enable_ai_simulation
                and self.options.ai_weight > 0
                and not ai_scores
                and any(detail.ai_recommendation > 0.0 for _, detail in recommendation.candidates)
            ):
                ai_summary["simulated"] += 1
                if logger.isEnabledFor(logging.INFO):
                    logger.info(
                        "layout AI simulated: slide_id=%s preferred=%s",
                        content_slide.id,
                        spec_slide.layout,
                    )

            mapping_logs.append(
                {
                    "slide_id": content_slide.id,
                    "preferred_layout": spec_slide.layout,
                    "selected_layout": selected_layout,
                    "ai_recommendation_used": ai_used,
                    "candidates": candidate_logs,
                    "ai_response": ai_response_payload,
                }
            )

        meta = DraftMeta(
            target_length=self.options.target_length or sum(len(section.slides) for section in sections),
            structure_pattern=self.options.structure_pattern or "custom",
            appendix_limit=self.options.appendix_limit,
        )

        if analyzer_map:
            meta.analyzer_summary = summarize_analyzer_counts(analyzer_map.values())

        if chapter_template:
            section_counts = {section.name: len(section.slides) for section in sections}
            evaluation = self._evaluate_chapter_template(
                template=chapter_template,
                section_counts=section_counts,
                total_main_pages=sum(section_counts.values()),
            )
            meta.template_id = chapter_template.template_id
            meta.template_match_score = evaluation.match_score
            meta.template_mismatch = evaluation.mismatches
            for section in sections:
                key = section.name.lower()
                score = evaluation.section_scores.get(key)
                section.chapter_template_id = chapter_template.template_id
                if score is not None:
                    section.template_match_score = score

        draft_document = DraftDocument(sections=sections, meta=meta)
        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "layout recommendation summary: invoked=%d used=%d simulated=%d",
                ai_summary["invoked"],
                ai_summary["used"],
                ai_summary["simulated"],
            )
        return draft_document, mapping_logs, ai_summary

    def _resolve_section(self, content_slide: ContentSlide, spec_slide) -> tuple[str, str]:
        story = getattr(content_slide, "story", None)
        if story:
            chapter_id = story.get("chapter_id") if isinstance(story, dict) else story.chapter_id
            phase = story.get("phase") if isinstance(story, dict) else story.phase
            if chapter_id:
                return str(chapter_id), str(chapter_id)
            if phase:
                return str(phase), str(phase)

        if content_slide.intent:
            return content_slide.intent, content_slide.intent
        return spec_slide.layout, spec_slide.layout

    def _build_card(
        self,
        content_slide: ContentSlide,
        default_layout: str,
        layouts: Sequence[LayoutProfile],
        *,
        order: int,
        analyzer_summary: DraftAnalyzerSummary | None,
        recommender: CardLayoutRecommender,
    ) -> tuple[RecommendationResult, DraftSlideCard]:
        recommendation = recommender.recommend(
            slide=content_slide,
            preferred_layout=default_layout,
            layouts=layouts,
            analyzer_summary=analyzer_summary,
        )
        candidates = recommendation.candidates
        layout_hint = candidates[0][0].layout_id if candidates else default_layout
        layout_detail = candidates[0][1] if candidates else None

        card = DraftSlideCard(
            ref_id=content_slide.id,
            order=order,
            layout_hint=layout_hint,
            locked=False,
            status="draft",
            layout_candidates=[candidate for candidate, _ in candidates[:5]],
            appendix=False,
            layout_score_detail=layout_detail,
            analyzer_summary=analyzer_summary,
        )
        return recommendation, card

    @staticmethod
    def _write_document(path: Path, document: DraftDocument) -> None:
        payload = document.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_log(path: Path, entries: Iterable[dict[str, object]]) -> None:
        payload = list(entries)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _spec_id_from_title(title: str | None) -> str:
        if not title:
            return "default"
        normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in title)
        normalized = normalized.strip("-") or "default"
        return normalized[:64]

    def _build_generate_ready_document(
        self,
        *,
        spec: JobSpec,
        draft: DraftDocument,
        content_document: ContentApprovalDocument | None,
    ) -> GenerateReadyDocument:
        section_lookup: dict[str, str] = {}
        cards_in_order: list[DraftSlideCard] = []
        for section in draft.sections:
            for card in section.slides:
                section_lookup[card.ref_id] = section.name
                cards_in_order.append(card)

            spec_lookup = {slide.id: slide for slide in spec.slides}
        content_lookup: dict[str, ContentSlide] = {}
        content_hash: str | None = None
        if content_document is not None:
            content_lookup = {slide.id: slide for slide in content_document.slides}
            try:
                payload = content_document.model_dump(mode="json")
                digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                content_hash = hashlib.sha256(digest.encode("utf-8")).hexdigest()
            except (TypeError, ValueError) as exc:
                logger.debug("content_approved のハッシュ化に失敗しました: %s", exc)

        slides: list[GenerateReadySlide] = []
        if not cards_in_order:
            for index, spec_slide in enumerate(spec.slides, start=1):
                layout_name = self._layout_name_lookup.get(spec_slide.layout, spec_slide.layout)
                auto_draw_payload = [
                    {
                        "anchor": anchor,
                        "left_in": box.left_in,
                        "top_in": box.top_in,
                        "width_in": box.width_in,
                        "height_in": box.height_in,
                    }
                    for anchor, box in spec_slide.auto_draw_boxes.items()
                ]
                slides.append(
                    GenerateReadySlide(
                        layout_id=spec_slide.layout,
                        layout_name=layout_name,
                        elements=self._convert_slide_elements(spec_slide),
                        meta=MappingSlideMeta(
                            section=None,
                            page_no=index,
                            sources=[spec_slide.id],
                            fallback="none",
                            auto_draw=auto_draw_payload,
                        ),
                    )
                )
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            meta = GenerateReadyMeta(
                template_version=draft.meta.template_id,
                template_path=None,
                content_hash=content_hash,
                generated_at=timestamp,
                job_meta=spec.meta if isinstance(spec.meta, JobMeta) else JobMeta.model_validate(spec.meta.model_dump()),
                job_auth=spec.auth if isinstance(spec.auth, JobAuth) else JobAuth.model_validate(spec.auth.model_dump()),
            )
            return GenerateReadyDocument(slides=slides, meta=meta)

        for index, card in enumerate(cards_in_order, start=1):
            spec_slide = spec_lookup.get(card.ref_id)
            section_name = section_lookup.get(card.ref_id)
            content_slide = content_lookup.get(card.ref_id)
            layout_id = card.layout_hint
            if not layout_id and spec_slide is not None:
                layout_id = spec_slide.layout
            layout_id = layout_id or "title"
            layout_name = self._layout_name_lookup.get(layout_id)
            if layout_name is None and spec_slide is not None and spec_slide.layout == layout_id:
                layout_name = spec_slide.layout
            if layout_name is None:
                layout_name = layout_id
            elements = self._merge_slide_elements(spec_slide, content_slide)
            sources = [spec_slide.id] if spec_slide is not None else [card.ref_id]
            auto_draw_payload = []
            if spec_slide is not None:
                auto_draw_payload = [
                    {
                        "anchor": anchor,
                        "left_in": box.left_in,
                        "top_in": box.top_in,
                        "width_in": box.width_in,
                        "height_in": box.height_in,
                    }
                    for anchor, box in spec_slide.auto_draw_boxes.items()
                ]
            slides.append(
                GenerateReadySlide(
                    layout_id=layout_id,
                    layout_name=layout_name,
                    elements=elements,
                    meta=MappingSlideMeta(
                        section=section_name,
                        page_no=index,
                        sources=sources,
                        fallback="none",
                        auto_draw=auto_draw_payload,
                    ),
                )
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta = GenerateReadyMeta(
            template_version=draft.meta.template_id,
            template_path=None,
            content_hash=content_hash,
            generated_at=timestamp,
            job_meta=spec.meta if isinstance(spec.meta, JobMeta) else JobMeta.model_validate(spec.meta.model_dump()),
            job_auth=spec.auth if isinstance(spec.auth, JobAuth) else JobAuth.model_validate(spec.auth.model_dump()),
        )
        return GenerateReadyDocument(slides=slides, meta=meta)

    def _build_generate_ready_meta_payload(
        self,
        *,
        draft: DraftDocument,
        generate_ready: GenerateReadyDocument,
        ai_summary: dict[str, Any],
    ) -> dict[str, Any]:
        sections_payload: list[dict[str, Any]] = []
        main_slides_total = 0
        appendix_slides_total = 0

        for section in draft.sections:
            main_count = sum(1 for card in section.slides if not card.appendix)
            appendix_count = sum(1 for card in section.slides if card.appendix)
            main_slides_total += main_count
            appendix_slides_total += appendix_count
            sections_payload.append(
                {
                    "name": section.name,
                    "order": section.order,
                    "status": section.status,
                    "slides": len(section.slides),
                    "main_slides": main_count,
                    "appendix_slides": appendix_count,
                    "locked": any(card.locked for card in section.slides),
                }
            )

        template_info = {
            "template_id": draft.meta.template_id,
            "structure_pattern": draft.meta.structure_pattern,
            "target_length": draft.meta.target_length,
            "appendix_limit": draft.meta.appendix_limit,
            "match_score": draft.meta.template_match_score,
            "mismatch": [item.model_dump(mode="json") for item in draft.meta.template_mismatch],
        }

        payload = {
            "generated_at": generate_ready.meta.generated_at,
            "sections": sections_payload,
            "statistics": {
                "total_slides": len(generate_ready.slides),
                "main_slides": main_slides_total,
                "appendix_slides": appendix_slides_total,
            },
            "template": template_info,
            "analyzer_summary": draft.meta.analyzer_summary,
            "return_reason_stats": draft.meta.return_reason_stats,
            "ai_recommendation": {
                "invoked": ai_summary.get("invoked", 0),
                "used": ai_summary.get("used", 0),
                "simulated": ai_summary.get("simulated", 0),
                "models": ai_summary.get("models", {}),
            },
        }
        payload["statistics"]["ai_recommendation_used"] = ai_summary.get("used", 0)
        payload["mode"] = generate_ready.meta.layout_mode
        if generate_ready.meta.slot_summary:
            payload["slot_summary"] = generate_ready.meta.slot_summary
        if generate_ready.meta.blueprint_path:
            payload["blueprint_path"] = generate_ready.meta.blueprint_path
        if generate_ready.meta.blueprint_hash:
            payload["blueprint_hash"] = generate_ready.meta.blueprint_hash
        return payload

    def _merge_slide_elements(
        self,
        spec_slide: Slide | None,
        content_slide: ContentSlide | None,
    ) -> dict[str, Any]:
        base = self._convert_slide_elements(spec_slide) if spec_slide is not None else {}
        if content_slide is None or content_slide.elements is None:
            return base

        elements: dict[str, Any] = {}
        title = content_slide.elements.title
        if title:
            elements["title"] = title

        if content_slide.elements.body:
            elements["body"] = list(content_slide.elements.body)
        elif "body" in base:
            elements["body"] = base["body"]

        if content_slide.elements.note:
            elements["note"] = content_slide.elements.note
        elif "note" in base:
            elements["note"] = base["note"]

        if content_slide.elements.table_data is not None:
            elements["table"] = {
                "headers": list(content_slide.elements.table_data.headers),
                "rows": [list(row) for row in content_slide.elements.table_data.rows],
            }

        if spec_slide is not None:
            if spec_slide.subtitle and "subtitle" not in elements:
                elements["subtitle"] = spec_slide.subtitle
            for key, value in base.items():
                if key in {"title", "body", "note", "subtitle"}:
                    continue
                elements.setdefault(key, value)
            for anchor in spec_slide.auto_draw_anchors:
                elements.pop(anchor, None)

        return elements

    @staticmethod
    def _convert_slide_elements(slide: Slide | None) -> dict[str, Any]:
        if slide is None:
            return {}
        elements: dict[str, Any] = {}
        if slide.title:
            elements["title"] = slide.title
        if slide.subtitle:
            elements["subtitle"] = slide.subtitle
        if slide.notes:
            elements["note"] = slide.notes

        body_lines: list[str] = []
        for group in slide.bullets:
            texts = [bullet.text for bullet in group.items]
            if not texts:
                continue
            if group.anchor:
                elements[group.anchor] = texts
            else:
                body_lines.extend(texts)
        if body_lines:
            elements["body"] = body_lines

        for index, table in enumerate(slide.tables, start=1):
            key = table.anchor or f"table_{index}"
            elements[key] = {
                "headers": table.columns,
                "rows": table.rows,
            }

        for index, image in enumerate(slide.images, start=1):
            key = image.anchor or f"image_{index}"
            elements[key] = {
                "source": str(image.source),
                "sizing": image.sizing,
            }

        for index, chart in enumerate(slide.charts, start=1):
            key = chart.anchor or f"chart_{index}"
            elements[key] = {
                "type": chart.type,
                "categories": chart.categories,
                "series": [series.model_dump(mode="json") for series in chart.series],
                "options": chart.options.model_dump(mode="json") if chart.options else None,
            }

        for index, textbox in enumerate(slide.textboxes, start=1):
            key = textbox.anchor or f"textbox_{index}"
            elements[key] = {"text": textbox.text}

        for anchor in slide.auto_draw_anchors:
            elements.pop(anchor, None)

        return elements

    def _evaluate_chapter_template(
        self,
        template: ChapterTemplate,
        section_counts: dict[str, int],
        total_main_pages: int,
    ) -> ChapterTemplateEvaluation:
        evaluation = evaluate_chapter_template(
            template=template,
            section_counts=section_counts,
            total_main_pages=total_main_pages,
        )

        normalized_scores: dict[str, float] = {}
        for section_id, score in evaluation.section_scores.items():
            normalized_scores[section_id.lower()] = score

        evaluation.section_scores = normalized_scores
        return evaluation

    def _run_static_mode(
        self,
        *,
        context: PipelineContext,
        content_document: ContentApprovalDocument,
        brief_meta: BriefGenerationMeta,
    ) -> None:
        brief_document = context.artifacts.get("brief_document")
        if not isinstance(brief_document, BriefDocument):
            msg = "static モードでは brief_document が必要です"
            raise DraftStructuringError(msg)

        spec_source_path = Path(self.options.spec_source_path) if self.options.spec_source_path else None
        template_spec_candidate: Path | None = None

        template_spec_meta = getattr(context.spec.meta, "template_spec_path", None)
        if template_spec_meta:
            candidate = Path(template_spec_meta)
            if not candidate.is_absolute() and spec_source_path is not None:
                candidate = (spec_source_path.parent / candidate).resolve()
            elif not candidate.is_absolute():
                candidate = candidate.resolve()
            template_spec_candidate = candidate

        if template_spec_candidate is None:
            blueprint_path_str = brief_meta.blueprint_path
            if blueprint_path_str:
                candidate = Path(blueprint_path_str)
                if not candidate.is_absolute():
                    candidate = candidate.resolve()
                template_spec_candidate = candidate

        if template_spec_candidate is None:
            msg = "template_spec のパスを jobspec または ai_generation_meta から取得できませんでした"
            raise DraftStructuringError(msg)

        if not template_spec_candidate.exists():
            msg = f"template_spec が見つかりません: {template_spec_candidate}"
            raise DraftStructuringError(msg)

        template_spec = self._load_template_spec(template_spec_candidate)
        if template_spec.layout_mode != "static" or template_spec.blueprint is None:
            msg = "template_spec が static Blueprint を含んでいません"
            raise DraftStructuringError(msg)

        if brief_meta.blueprint_hash:
            computed_hash = self._compute_blueprint_hash(template_spec.blueprint)
            if brief_meta.blueprint_hash != computed_hash:
                msg = "Blueprint ハッシュが ai_generation_meta と一致しません"
                raise DraftStructuringError(msg)

        self._layout_name_lookup = {layout.name: layout.name for layout in template_spec.layouts}

        artifacts = self._build_static_artifacts(
            spec=context.spec,
            brief_document=brief_document,
            content_document=content_document,
            template_spec=template_spec,
            brief_meta=brief_meta,
        )

        output_dir = self.options.output_dir or context.workdir
        output_dir.mkdir(parents=True, exist_ok=True)

        draft_path = output_dir / self.options.draft_filename
        approved_path = output_dir / self.options.approved_filename
        log_path = output_dir / self.options.log_filename
        mapping_log_path = output_dir / self.options.mapping_log_filename

        self._write_document(draft_path, artifacts.draft)
        self._write_document(approved_path, artifacts.draft)
        self._write_log(log_path, [])
        self._write_json(mapping_log_path, artifacts.mapping_log)

        ready_path = output_dir / self.options.generate_ready_filename
        self._write_json(ready_path, artifacts.generate_ready.model_dump(mode="json", exclude_none=True))
        context.add_artifact("generate_ready", artifacts.generate_ready)
        context.add_artifact("generate_ready_path", str(ready_path))

        ready_meta_payload = self._build_generate_ready_meta_payload(
            draft=artifacts.draft,
            generate_ready=artifacts.generate_ready,
            ai_summary=artifacts.ai_summary,
        )
        ready_meta_path = output_dir / self.options.generate_ready_meta_filename
        self._write_json(ready_meta_path, ready_meta_payload)
        context.add_artifact("generate_ready_meta_path", str(ready_meta_path))

        context.add_artifact("draft_document", artifacts.draft)
        context.add_artifact("draft_document_path", str(approved_path))
        context.add_artifact("draft_review_log_path", str(log_path))
        context.add_artifact("draft_mapping_log_path", str(mapping_log_path))

        spec_id = self._spec_id_from_title(getattr(context.spec.meta, "title", None))
        context.add_artifact("draft_spec_id", spec_id)

        store = DraftStore()
        try:
            store.create_board(spec_id, artifacts.draft)
        except BoardAlreadyExistsError:
            store.overwrite_board(spec_id, artifacts.draft)

        logger.info(
            "Static テンプレート向け Draft ドキュメントを生成しました: slides=%d",
            sum(len(section.slides) for section in artifacts.draft.sections),
        )

    def _build_static_artifacts(
        self,
        *,
        spec: JobSpec,
        brief_document: BriefDocument,
        content_document: ContentApprovalDocument,
        template_spec: TemplateSpec,
        brief_meta: BriefGenerationMeta,
    ) -> StaticArtifacts:
        blueprint: TemplateBlueprint = template_spec.blueprint  # type: ignore[assignment]

        cards_by_slot = {card.slot_id: card for card in brief_document.cards if card.slot_id}
        spec_lookup = {slide.id: slide for slide in spec.slides}

        total_slots = 0
        required_total = 0
        required_fulfilled = 0
        optional_used = 0
        unused_slots: list[str] = []
        blueprint_slot_ids: set[str] = set()

        for blueprint_slide in blueprint.slides:
            for slot in blueprint_slide.slots:
                blueprint_slot_ids.add(slot.slot_id)
                total_slots += 1
                card = cards_by_slot.get(slot.slot_id)
                if slot.required:
                    required_total += 1
                    if card is not None and card.slot_fulfilled:
                        required_fulfilled += 1
                else:
                    if card is not None and card.slot_fulfilled:
                        optional_used += 1
                    else:
                        unused_slots.append(slot.slot_id)

        if required_fulfilled < required_total:
            missing = required_total - required_fulfilled
            msg = f"必須 slot に対応するカードが不足しています: missing={missing}"
            raise DraftStructuringError(msg)

        slot_summary = {
            "required_total": required_total,
            "required_fulfilled": required_fulfilled,
            "optional_total": total_slots - required_total,
            "optional_used": optional_used,
        }

        orphan_cards = [card.slot_id for card in brief_document.cards if card.slot_id and card.slot_id not in blueprint_slot_ids]

        section = DraftSection(name="Static Template", order=1, status="draft", slides=[])
        draft_sections = [section]

        generate_ready_slides: list[GenerateReadySlide] = []
        mapping_entries: list[dict[str, Any]] = []

        layout_lookup = self._layout_name_lookup

        for page_no, blueprint_slide in enumerate(blueprint.slides, start=1):
            spec_slide = spec_lookup.get(blueprint_slide.slide_id)
            layout_id = spec_slide.layout if spec_slide else blueprint_slide.layout
            layout_name = layout_lookup.get(layout_id, layout_id)

            slide_card = DraftSlideCard(
                ref_id=spec_slide.id if spec_slide else blueprint_slide.slide_id,
                order=page_no,
                layout_hint=layout_id,
                locked=False,
                status="draft",
                layout_candidates=[DraftLayoutCandidate(layout_id=layout_id, score=1.0)],
                appendix=False,
            )
            section.slides.append(slide_card)

            elements: dict[str, Any] = {}
            slot_records: list[dict[str, Any]] = []

            for slot in blueprint_slide.slots:
                card = cards_by_slot.get(slot.slot_id)
                fulfilled = bool(card and card.slot_fulfilled)
                slot_records.append(
                    {
                        "slot_id": slot.slot_id,
                        "anchor": slot.anchor,
                        "required": slot.required,
                        "card_id": card.card_id if card else None,
                        "fulfilled": fulfilled,
                    }
                )
                if card is None:
                    continue
                lines = self._card_to_lines(card)
                self._assign_slot_to_elements(elements, slot, card, lines)

            sources: list[str] = []
            if spec_slide is not None:
                sources.append(spec_slide.id)
            else:
                sources.append(blueprint_slide.slide_id)

            slide_meta = MappingSlideMeta(
                section="Static Template",
                page_no=page_no,
                sources=sources,
                fallback="none",
                layout_mode="static",
                blueprint_slide_id=blueprint_slide.slide_id,
                blueprint_slots=slot_records,
            )

            generate_ready_slides.append(
                GenerateReadySlide(
                    layout_id=layout_id,
                    layout_name=layout_name,
                    elements=elements,
                    meta=slide_meta,
                )
            )

            mapping_entries.append(
                {
                    "mode": "static",
                    "slide_id": blueprint_slide.slide_id,
                    "layout": layout_id,
                    "slots": slot_records,
                }
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content_hash = self._compute_content_hash(content_document)

        generate_ready = GenerateReadyDocument(
            slides=generate_ready_slides,
            meta=GenerateReadyMeta(
                template_version=None,
                template_path=None,
                content_hash=content_hash,
                generated_at=timestamp,
                job_meta=spec.meta if isinstance(spec.meta, JobMeta) else JobMeta.model_validate(spec.meta.model_dump()),
                job_auth=spec.auth if isinstance(spec.auth, JobAuth) else JobAuth.model_validate(spec.auth.model_dump()),
                layout_mode="static",
                blueprint_path=brief_meta.blueprint_path,
                blueprint_hash=brief_meta.blueprint_hash,
                slot_summary=slot_summary,
            ),
        )

        draft_meta = DraftMeta(
            target_length=len(blueprint.slides),
            structure_pattern="static",
            appendix_limit=self.options.appendix_limit,
            template_id=template_spec.template_path,
            template_match_score=1.0,
            template_mismatch=[],
            return_reason_stats={},
            analyzer_summary={},
        )
        draft = DraftDocument(sections=draft_sections, meta=draft_meta)

        blueprint_path_value = brief_meta.blueprint_path or getattr(spec.meta, "template_spec_path", None)

        mapping_log = {
            "mode": "static",
            "slides": mapping_entries,
            "slot_summary": slot_summary,
            "static_slot_checks": {
                "unused_slots": unused_slots,
                "orphan_cards": orphan_cards,
            },
            "blueprint_path": blueprint_path_value,
        }

        ai_summary = {
            "mode": "static",
            "invoked": 0,
            "used": 0,
            "simulated": 0,
            "models": {},
        }

        return StaticArtifacts(
            draft=draft,
            generate_ready=generate_ready,
            mapping_log=mapping_log,
            ai_summary=ai_summary,
            slot_summary=slot_summary,
        )

    def _load_template_spec(self, path: Path) -> TemplateSpec:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"template_spec を読み込めません: {path}"
            raise DraftStructuringError(msg) from exc

        try:
            if path.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                payload = yaml.safe_load(text)
                return TemplateSpec.model_validate(payload)
            return TemplateSpec.model_validate_json(text)
        except ValueError as exc:
            msg = f"template_spec の解析に失敗しました: {path}"
            raise DraftStructuringError(msg) from exc

    @staticmethod
    def _compute_blueprint_hash(blueprint: TemplateBlueprint) -> str:
        payload = blueprint.model_dump(mode="json")
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return f"sha256:{hashlib.sha256(digest.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _compute_content_hash(document: ContentApprovalDocument | None) -> str | None:
        if document is None:
            return None
        try:
            payload = document.model_dump(mode="json")
            digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            return hashlib.sha256(digest.encode("utf-8")).hexdigest()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _card_to_lines(card: BriefCard) -> list[str]:
        lines: list[str] = []
        if card.narrative:
            lines.extend(card.narrative)
        elif card.message:
            lines.append(card.message)
        if card.supporting_points:
            lines.extend(point.statement for point in card.supporting_points)
        return [line for line in lines if line]

    @staticmethod
    def _assign_slot_to_elements(
        elements: dict[str, Any],
        slot: TemplateBlueprintSlot,
        card: BriefCard,
        lines: list[str],
    ) -> None:
        anchor = slot.anchor or slot.slot_id
        if not anchor:
            return
        anchor_lower = anchor.lower()
        if anchor_lower in {"title", "main message"}:
            if card.message:
                elements["title"] = card.message
            return
        if "subtitle" in anchor_lower:
            if card.message:
                elements["subtitle"] = card.message
            return
        if anchor_lower in {"body", "content"}:
            if lines:
                elements["body"] = lines
            elif card.message:
                elements["body"] = [card.message]
            return
        if lines:
            elements[anchor] = lines
