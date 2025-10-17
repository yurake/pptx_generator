"""Analyzer 出力を Review Engine 向けに変換するアダプタ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..models import (AIReviewIssue, AutoFixProposal, JsonPatchOperation, JobSpec,
                      Slide, SlideBullet, SlideBulletGroup)


@dataclass(slots=True)
class AnalyzerReviewEngineConfig:
    """アダプタ動作設定。"""

    schema_version: str = "1.0.0"
    severity_grade_map: dict[str, str] = field(
        default_factory=lambda: {"critical": "C", "warning": "B", "info": "A"}
    )
    default_grade: str = "A"


class AnalyzerReviewEngineAdapter:
    """analysis.json の issues / fixes を Review Engine 形式へ変換する。"""

    def __init__(self, config: AnalyzerReviewEngineConfig | None = None) -> None:
        self.config = config or AnalyzerReviewEngineConfig()

    def build_payload(self, analysis: dict[str, Any], spec: JobSpec) -> dict[str, Any]:
        """Analyzer 結果を Review Engine 連携用のペイロードへ変換する。"""
        slides_in_spec = {slide.id: slide for slide in spec.slides}
        slide_indices = {slide.id: index for index, slide in enumerate(spec.slides)}
        bullet_lookup = self._build_bullet_lookup(spec.slides)

        slide_state: dict[str, dict[str, Any]] = {
            slide.id: {
                "issues": [],
                "severities": [],
                "autofix": [],
                "unsupported_fix_types": set(),
            }
            for slide in spec.slides
        }

        for issue in analysis.get("issues", []):
            target = issue.get("target") or {}
            slide_id = target.get("slide_id")
            if slide_id not in slide_state:
                continue
            normalized_severity = self._normalize_severity(issue.get("severity"))
            ai_issue = AIReviewIssue(
                code=str(issue.get("type", "")),
                message=str(issue.get("message", "")),
                severity=normalized_severity,
            )
            slide_state[slide_id]["issues"].append(ai_issue)
            if normalized_severity is not None:
                slide_state[slide_id]["severities"].append(normalized_severity)

        existing_fix_ids: set[str] = set()
        for fix in analysis.get("fixes", []):
            fix_id = str(fix.get("id", ""))
            if not fix_id or fix_id in existing_fix_ids:
                continue
            existing_fix_ids.add(fix_id)

            target = fix.get("target") or {}
            slide_id = target.get("slide_id")
            if slide_id not in slide_state:
                continue

            patch = self._convert_fix_to_patch(
                fix, slides_in_spec.get(slide_id), slide_indices, bullet_lookup
            )
            if patch is None:
                slide_state[slide_id]["unsupported_fix_types"].add(str(fix.get("type")))
                continue

            proposal = AutoFixProposal(
                patch_id=fix_id,
                description=patch["description"],
                patch=patch["operations"],
            )
            slide_state[slide_id]["autofix"].append(proposal)

        slides_payload: list[dict[str, Any]] = []
        generated_at = datetime.now(timezone.utc).isoformat()

        for slide in spec.slides:
            state = slide_state[slide.id]
            grade = self._calculate_grade(state["severities"])
            issues_dump = [
                issue.model_dump(mode="json") for issue in state["issues"]
            ]
            autofix_dump = [
                proposal.model_dump(mode="json", by_alias=True)
                for proposal in state["autofix"]
            ]
            slide_payload: dict[str, Any] = {
                "slide_id": slide.id,
                "grade": grade,
                "issues": issues_dump,
            }
            if autofix_dump:
                slide_payload["autofix_proposals"] = autofix_dump
            if state["unsupported_fix_types"]:
                slide_payload["notes"] = {
                    "unsupported_fix_types": sorted(state["unsupported_fix_types"])
                }
            slides_payload.append(slide_payload)

        return {
            "schema_version": self.config.schema_version,
            "generated_at": generated_at,
            "slides": slides_payload,
        }

    def _calculate_grade(self, severities: list[str]) -> str:
        if not severities:
            return self.config.default_grade
        priority = 0
        grade = self.config.default_grade
        for severity in severities:
            mapped = self.config.severity_grade_map.get(severity.lower())
            if not mapped:
                continue
            current_priority = self._grade_priority(mapped)
            if current_priority > priority:
                priority = current_priority
                grade = mapped
        return grade

    @staticmethod
    def _grade_priority(grade: str) -> int:
        match grade.upper():
            case "C":
                return 3
            case "B":
                return 2
            case "A":
                return 1
            case _:
                return 0

    @staticmethod
    def _normalize_severity(severity: Any) -> str | None:
        if severity is None:
            return None
        value = str(severity).lower()
        if value == "error":
            return "critical"
        if value in {"info", "warning", "critical"}:
            return value
        return None

    @staticmethod
    def _build_bullet_lookup(slides: list[Slide]) -> dict[str, dict[str, tuple[int, int]]]:
        lookup: dict[str, dict[str, tuple[int, int]]] = {}
        for slide_index, slide in enumerate(slides):
            slide_map: dict[str, tuple[int, int]] = {}
            for group_index, group in enumerate(slide.bullets):
                for bullet_index, bullet in enumerate(group.items):
                    slide_map[bullet.id] = (group_index, bullet_index)
            lookup[slide.id] = slide_map
        return lookup

    def _convert_fix_to_patch(
        self,
        fix: dict[str, Any],
        slide: Slide | None,
        slide_indices: dict[str, int],
        bullet_lookup: dict[str, dict[str, tuple[int, int]]],
    ) -> dict[str, Any] | None:
        if slide is None:
            return None
        target = fix.get("target") or {}
        slide_id = target.get("slide_id")
        element_id = target.get("element_id")
        if slide_id is None or element_id is None:
            return None
        fix_type = str(fix.get("type", ""))
        payload = fix.get("payload") or {}

        slide_index = slide_indices.get(slide_id)
        if slide_index is None:
            return None
        if fix_type in {"bullet_reindent", "bullet_cap", "font_raise", "color_adjust"}:
            return self._convert_bullet_fix(
                slide, slide_id, slide_index, element_id, fix_type, payload, bullet_lookup
            )
        return None

    def _convert_bullet_fix(
        self,
        slide: Slide,
        slide_id: str,
        slide_index: int,
        element_id: str,
        fix_type: str,
        payload: dict[str, Any],
        bullet_lookup: dict[str, dict[str, tuple[int, int]]],
    ) -> dict[str, Any] | None:
        indices = bullet_lookup.get(slide_id, {}).get(element_id)
        if indices is None:
            return None
        group_index, bullet_index = indices
        bullet = self._get_bullet(slide, group_index, bullet_index)
        if bullet is None:
            return None

        base_path = f"/slides/{slide_index}/bullets/{group_index}/items/{bullet_index}"
        operations: list[JsonPatchOperation] = []
        description: str | None = None

        if fix_type in {"bullet_reindent", "bullet_cap"}:
            level = payload.get("level")
            if not isinstance(level, int):
                return None
            operations.append(
                JsonPatchOperation(op="replace", path=f"{base_path}/level", value=level)
            )
            description = f"箇条書きレベルを {level} に調整"
        elif fix_type == "font_raise":
            size = payload.get("size_pt")
            if size is None:
                size = payload.get("size")
            if not isinstance(size, (int, float)):
                return None
            if bullet.font is None:
                return None
            operations.append(
                JsonPatchOperation(
                    op="replace", path=f"{base_path}/font/size_pt", value=float(size)
                )
            )
            description = f"フォントサイズを {float(size):.1f}pt に引き上げ"
        elif fix_type == "color_adjust":
            color = payload.get("color_hex") or payload.get("color")
            if not isinstance(color, str):
                return None
            if bullet.font is None:
                return None
            operations.append(
                JsonPatchOperation(
                    op="replace",
                    path=f"{base_path}/font/color_hex",
                    value=self._normalize_hex(color),
                )
            )
            description = f"文字色を {self._normalize_hex(color)} に変更"

        if not operations or description is None:
            return None

        return {"description": description, "operations": operations}

    @staticmethod
    def _get_bullet(
        slide: Slide, group_index: int, bullet_index: int
    ) -> SlideBullet | None:
        if group_index >= len(slide.bullets):
            return None
        group: SlideBulletGroup = slide.bullets[group_index]
        if bullet_index >= len(group.items):
            return None
        return group.items[bullet_index]

    @staticmethod
    def _normalize_hex(value: str) -> str:
        return value if value.startswith("#") else f"#{value}"
