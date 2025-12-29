"""ドラフト構成インテリジェンス関連のユーティリティ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .models import (DraftAnalyzerSummary, DraftLayoutScoreDetail,
                     DraftTemplateMismatch)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChapterTemplateSection:
    section_id: str
    title: str | None = None
    min_slides: int = 0
    max_slides: int | None = None


@dataclass(slots=True)
class ChapterTemplate:
    template_id: str
    name: str
    structure_pattern: str
    required_sections: tuple[ChapterTemplateSection, ...]
    optional_sections: tuple[ChapterTemplateSection, ...]
    max_main_pages: int | None = None
    appendix_policy: str = "overflow"
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class ChapterTemplateEvaluation:
    match_score: float
    section_scores: dict[str, float]
    mismatches: list[DraftTemplateMismatch]


@dataclass(slots=True)
class ReturnReasonTemplate:
    code: str
    label: str
    description: str | None
    severity: str
    default_actions: tuple[str, ...]
    related_analyzer_tags: tuple[str, ...]


DEFAULT_RETURN_REASONS: tuple[ReturnReasonTemplate, ...] = (
    ReturnReasonTemplate(
        code="STRUCTURE_GAP",
        label="章構成の不足",
        description="章テンプレで必須となっているセクションが不足しています。",
        severity="blocker",
        default_actions=(
            "Add required section",
            "Escalate to story lead",
        ),
        related_analyzer_tags=("missing_section",),
    ),
    ReturnReasonTemplate(
        code="ANALYZER_BLOCKER",
        label="Analyzer 指摘（重大）",
        description="重大度 High の Analyzer 指摘が解消されていません。",
        severity="blocker",
        default_actions=("Resolve analyzer issues",),
        related_analyzer_tags=(
            "layout_consistency",
            "contrast_low",
        ),
    ),
    ReturnReasonTemplate(
        code="CAPACITY_WARN",
        label="枚数超過",
        description="テンプレで想定した枚数を超過しています。付録送りなどで調整してください。",
        severity="warn",
        default_actions=(
            "Move slides to appendix",
            "Consolidate content",
        ),
        related_analyzer_tags=(),
    ),
)


def _load_json(path: Path) -> object:
    logger.info("Loading JSON from %s", path.resolve())
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_template_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists():
        return ()
    for path in base_dir.rglob("*.json"):
        if path.is_file():
            yield path


def find_chapter_template_path(base_dir: Path, template_id: str) -> Path | None:
    template_id_lower = template_id.lower()
    for path in _iter_template_files(base_dir):
        if path.stem.lower() == template_id_lower:
            return path
    return None


def find_template_by_structure(base_dir: Path, structure_pattern: str) -> ChapterTemplate | None:
    pattern_lower = structure_pattern.lower()
    for path in _iter_template_files(base_dir):
        payload = _load_json(path)
        if not isinstance(payload, dict):
            continue
        pattern = str(payload.get("structure_pattern") or "").lower()
        if pattern == pattern_lower:
            template_id = str(payload.get("template_id") or path.stem)
            return load_chapter_template(base_dir, template_id)
    return None


def load_chapter_template(base_dir: Path, template_id: str) -> ChapterTemplate | None:
    template_path = find_chapter_template_path(base_dir, template_id)
    if not template_path:
        return None
    payload = _load_json(template_path)
    if not isinstance(payload, dict):
        raise ValueError(f"テンプレートファイルの形式が不正です: {template_path}")

    required_items = payload.get("required_sections") or []
    optional_items = payload.get("optional_sections") or []
    if not isinstance(required_items, list) or not isinstance(optional_items, list):
        raise ValueError(f"テンプレートのセクション定義が不正です: {template_path}")

    max_main_pages, appendix_policy, tags = _parse_template_constraints(payload.get("constraints"))

    template = ChapterTemplate(
        template_id=str(payload.get("template_id") or template_path.stem),
        name=str(payload.get("name") or template_path.stem),
        structure_pattern=str(payload.get("structure_pattern") or "custom"),
        required_sections=tuple(_load_sections(required_items)),
        optional_sections=tuple(_load_sections(optional_items)),
        max_main_pages=max_main_pages,
        appendix_policy=appendix_policy,
        tags=tags,
    )
    return template


def evaluate_chapter_template(
    template: ChapterTemplate,
    section_counts: Mapping[str, int],
    total_main_pages: int,
) -> ChapterTemplateEvaluation:
    mismatches: list[DraftTemplateMismatch] = []
    section_scores: dict[str, float] = {}

    required_total = len(template.required_sections)
    matched_required = 0

    normalized_counts = {key.lower(): count for key, count in section_counts.items()}

    for section in template.required_sections:
        count = normalized_counts.get(section.section_id.lower(), 0)
        score, section_mismatches, matched = _score_required_section(section, count)
        mismatches.extend(section_mismatches)
        matched_required += matched
        section_scores[section.section_id] = score

    for section in template.optional_sections:
        count = normalized_counts.get(section.section_id.lower(), 0)
        score, section_mismatches = _score_optional_section(section, count)
        mismatches.extend(section_mismatches)
        section_scores[section.section_id] = score

    capacity_mismatch = _capacity_mismatch(template, total_main_pages)
    if capacity_mismatch:
        mismatches.append(capacity_mismatch)

    match_score = _calculate_match_score(required_total, matched_required)

    return ChapterTemplateEvaluation(
        match_score=match_score,
        section_scores=section_scores,
        mismatches=mismatches,
    )


def load_return_reasons(path: Path | None = None) -> tuple[ReturnReasonTemplate, ...]:
    return DEFAULT_RETURN_REASONS


def load_analysis_summary(path: Path) -> dict[str, DraftAnalyzerSummary]:
    if path is None or not path.exists():
        return {}
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"analysis_summary.json の形式が不正です: {path}")

    slides = payload.get("slides")
    if not isinstance(slides, list):
        return {}

    summary: dict[str, DraftAnalyzerSummary] = {}
    for item in slides:
        parsed = _parse_slide_summary(item)
        if parsed is None:
            continue
        slide_uid, analyzer_summary = parsed
        summary[slide_uid] = analyzer_summary
    return summary


def summarize_analyzer_counts(entries: Iterable[DraftAnalyzerSummary]) -> dict[str, int]:
    total_high = 0
    total_medium = 0
    total_low = 0
    for entry in entries:
        total_high += entry.severity_high
        total_medium += entry.severity_medium
        total_low += entry.severity_low
    return {
        "high": total_high,
        "medium": total_medium,
        "low": total_low,
    }


def compute_analyzer_support(summary: DraftAnalyzerSummary | None) -> float:
    if summary is None:
        return 0.0
    if summary.severity_high > 0:
        return -0.2
    if summary.severity_medium > 0:
        return -0.1
    return 0.1


def clamp_score_detail(detail: DraftLayoutScoreDetail) -> DraftLayoutScoreDetail:
    total = detail.total
    if total > 1.0:
        scale = 1.0 / total
        detail.uses_tag = round(detail.uses_tag * scale, 3)
        detail.content_capacity = round(detail.content_capacity * scale, 3)
        detail.diversity = round(detail.diversity * scale, 3)
        detail.analyzer_support = round(detail.analyzer_support * scale, 3)
        detail.ai_recommendation = round(detail.ai_recommendation * scale, 3)
    if detail.total < 0.0:
        detail.uses_tag = round(max(0.0, detail.uses_tag), 3)
        detail.content_capacity = round(max(0.0, detail.content_capacity), 3)
        detail.diversity = round(max(0.0, detail.diversity), 3)
        detail.analyzer_support = round(max(-0.5, detail.analyzer_support), 3)
        detail.ai_recommendation = round(max(0.0, detail.ai_recommendation), 3)
    return detail


def _parse_template_constraints(constraints: object) -> tuple[int | None, str, tuple[str, ...]]:
    max_main_pages = None
    appendix_policy = "overflow"
    tags: tuple[str, ...] = ()
    if not isinstance(constraints, dict):
        return max_main_pages, appendix_policy, tags

    max_value = constraints.get("max_main_pages")
    if isinstance(max_value, (int, float)) and max_value > 0:
        max_main_pages = int(max_value)

    appendix_policy_value = constraints.get("appendix_policy")
    if isinstance(appendix_policy_value, str) and appendix_policy_value:
        appendix_policy = appendix_policy_value

    tags_value = constraints.get("tags")
    if isinstance(tags_value, list):
        tags = tuple(str(tag) for tag in tags_value if str(tag).strip())

    return max_main_pages, appendix_policy, tags


def _load_sections(items: Iterable[Mapping[str, object]]) -> list[ChapterTemplateSection]:
    sections: list[ChapterTemplateSection] = []
    for item in items:
        section_id = str(item.get("id", "")).strip()
        if not section_id:
            continue
        title = str(item.get("title", "")).strip() or None
        min_slides = int(item.get("min_slides", 0) or 0)
        max_value = item.get("max_slides")
        max_slides: int | None = None
        if isinstance(max_value, (int, float)):
            max_slides = int(max_value)
        sections.append(
            ChapterTemplateSection(
                section_id=section_id,
                title=title,
                min_slides=min_slides,
                max_slides=max_slides,
            )
        )
    return sections


def _score_required_section(
    section: ChapterTemplateSection, count: int
) -> tuple[float, list[DraftTemplateMismatch], int]:
    mismatches: list[DraftTemplateMismatch] = []
    if count == 0:
        mismatches.append(
            DraftTemplateMismatch(
                section_id=section.section_id,
                issue="missing",
                severity="blocker",
                detail="必須章が不足しています",
            )
        )
        return 0.0, mismatches, 0

    if section.max_slides is not None and count > section.max_slides:
        mismatches.append(
            DraftTemplateMismatch(
                section_id=section.section_id,
                issue="excess",
                severity="warn",
                detail=f"許容枚数 {section.max_slides} を超過 (actual={count})",
            )
        )
        return round(min(1.0, section.max_slides / count), 3), mismatches, 0

    if count < max(1, section.min_slides):
        mismatches.append(
            DraftTemplateMismatch(
                section_id=section.section_id,
                issue="insufficient",
                severity="blocker",
                detail=f"必要枚数 {section.min_slides} 未満 (actual={count})",
            )
        )
        score = count / max(1, section.min_slides)
        return round(max(0.0, min(1.0, score)), 3), mismatches, 0

    return 1.0, mismatches, 1


def _score_optional_section(
    section: ChapterTemplateSection, count: int
) -> tuple[float, list[DraftTemplateMismatch]]:
    if count == 0:
        return 0.0, []

    if section.max_slides is not None and count > section.max_slides:
        mismatch = DraftTemplateMismatch(
            section_id=section.section_id,
            issue="excess",
            severity="warn",
            detail=f"任意章が許容枚数 {section.max_slides} を超過 (actual={count})",
        )
        return round(min(1.0, section.max_slides / count), 3), [mismatch]

    return 1.0, []


def _capacity_mismatch(
    template: ChapterTemplate, total_main_pages: int
) -> DraftTemplateMismatch | None:
    if template.max_main_pages is None or total_main_pages <= template.max_main_pages:
        return None
    severity = "blocker" if template.appendix_policy == "block" else "warn"
    return DraftTemplateMismatch(
        section_id="__capacity__",
        issue="capacity",
        severity=severity,
        detail=f"許容枚数 {template.max_main_pages} を超過 (actual={total_main_pages})",
    )


def _calculate_match_score(required_total: int, matched_required: int) -> float:
    if not required_total:
        return 1.0
    return round(max(0.0, min(1.0, matched_required / required_total)), 3)


def _parse_slide_summary(item: object) -> tuple[str, DraftAnalyzerSummary] | None:
    if not isinstance(item, dict):
        return None

    slide_uid = str(item.get("slide_uid", "")).strip()
    if not slide_uid:
        return None

    severity_counts = item.get("severity_counts") or {}
    high = int(severity_counts.get("high", 0) or 0)
    medium = int(severity_counts.get("medium", 0) or 0)
    low = int(severity_counts.get("low", 0) or 0)

    layout_consistency = _normalize_layout_consistency(item.get("layout_consistency"))
    blocking_tags = _normalize_blocking_tags(item.get("blocking_tags"))

    analyzer_summary = DraftAnalyzerSummary(
        severity_high=high,
        severity_medium=medium,
        severity_low=low,
        layout_consistency=layout_consistency,
        blocking_tags=blocking_tags,
    )
    return slide_uid, analyzer_summary


def _normalize_layout_consistency(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower()
    if normalized in {"ok", "warn", "error"}:
        return normalized
    return None


def _normalize_blocking_tags(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(tag) for tag in value if str(tag).strip())
