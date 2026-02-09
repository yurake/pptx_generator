#!/usr/bin/env python3
"""Stage2 hook: Excel から静的テンプレ用の prepare_card を生成する。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.stage_shared import (  # noqa: E402
    CONTEXT_PATH,
    load_mapping_config,
    resolve_input_path,
)

KEEP_TEMPLATE_SENTINEL = "__KEEP_TEMPLATE__"
DEFAULT_MAPPING_CONFIG = Path(__file__).resolve().parent / "mapping_config.json"


def _load_excel_cell_value(sheet, cell_ref: str):
    try:
        return sheet[cell_ref].value
    except Exception:
        return None


def _convert_value(value: Any, fmt: str | None, conversions: dict[str, Any]) -> Any:
    if fmt is None:
        return value
    if fmt == "億円":
        factor = conversions.get("円_to_億円") or conversions.get("JPY_to_億円")
        try:
            return round(float(value) / float(factor), 3) if factor else value
        except Exception:
            return value
    if fmt == "年":
        return value
    return value


def extract_excel_data(excel_path: Path, mapping: dict[str, Any]) -> dict[str, Any]:
    import openpyxl

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    conversions = mapping.get("conversion") or {}
    excel_map = mapping.get("excel_to_pptx_mapping") or {}

    payload: dict[str, Any] = {"meta": {"source_excel": str(excel_path)}}

    # message_line
    message_map = excel_map.get("message_line") or {}
    message_line: dict[str, Any] = {}
    for key, conf in message_map.items():
        if not isinstance(conf, dict):
            continue
        sheet_name = conf.get("sheet")
        cell_ref = conf.get("cell")
        fmt = conf.get("format")
        if not (sheet_name and cell_ref):
            continue
        sheet = wb[sheet_name]
        raw = _load_excel_cell_value(sheet, cell_ref)
        converted = _convert_value(raw, fmt, conversions)
        message_line[key] = {"value": raw, "formatted_value": converted}
    payload["message_line"] = message_line

    # table
    table_map = excel_map.get("table") or {}
    table: dict[str, Any] = {}
    for key, conf in table_map.items():
        if not isinstance(conf, dict):
            continue
        sheet_name = conf.get("sheet")
        cell_ref = conf.get("cell")
        fmt = conf.get("format")
        target = conf.get("target")
        if not (sheet_name and cell_ref):
            continue
        sheet = wb[sheet_name]
        raw = _load_excel_cell_value(sheet, cell_ref)
        converted = _convert_value(raw, fmt, conversions)
        table[key] = {
            "source": key,
            "target": target,
            "value": raw,
            "formatted_value": converted,
        }
    payload["table"] = table

    payload["extracted_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def _extract_template_id_from_jobspec(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    meta = payload.get("meta")
    if isinstance(meta, dict):
        candidate = meta.get("template_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _load_json_or_none(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _resolve_template_spec_path(context: dict[str, Any], jobspec_path: Path | None) -> Path | None:
    if context.get("template_spec_path"):
        return Path(context["template_spec_path"]).expanduser().resolve()
    candidate: Path | None = None
    if jobspec_path and jobspec_path.exists():
        payload = _load_json_or_none(jobspec_path)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        template_spec_rel = meta.get("template_spec_path") if isinstance(meta, dict) else None
        if isinstance(template_spec_rel, str) and template_spec_rel.strip():
            rel_path = Path(template_spec_rel)
            candidate = (jobspec_path.parent / rel_path).resolve() if not rel_path.is_absolute() else rel_path
    if candidate and candidate.exists():
        context["template_spec_path"] = str(candidate)
        return candidate
    return None


def _load_context() -> dict[str, Any]:
    if CONTEXT_PATH.exists():
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    return {}


def _persist_context(context: dict[str, Any]) -> None:
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_path(candidate: str | None, fallback: Path) -> Path:
    if candidate:
        maybe = Path(candidate).expanduser()
        if not maybe.is_absolute():
            base = Path(__file__).resolve().parent
            maybe = (base / maybe).resolve()
        return maybe
    return (Path(__file__).resolve().parent / fallback).resolve()


def _determine_template_id(context: dict[str, Any], jobspec_path: Path | None) -> str:
    env_template_id = os.environ.get("PPTX_TEMPLATE_ID")
    if isinstance(env_template_id, str) and env_template_id.strip():
        template_id = env_template_id.strip()
        context["template_id"] = template_id
        return template_id

    if jobspec_path is not None and jobspec_path.exists():
        template_id = _extract_template_id_from_jobspec(jobspec_path)
        if template_id:
            context["template_id"] = template_id
            return template_id

    template_id = context.get("template_id")
    if isinstance(template_id, str) and template_id.strip():
        return template_id.strip()
    return ""


def _reset_context_for_template(context: dict[str, Any], template_id: str) -> None:
    previous = context.get("template_id")
    if previous and template_id and previous != template_id:
        for key in (
            "excel_source_path",
            "mapping_config_path",
            "template_path",
            "generate_ready_path",
            "prepare_card_path",
            "prepared_payload_path",
            "extract_summary",
            "prepare_log_path",
            "prepare_ai_log_path",
            "template_spec_path",
        ):
            context.pop(key, None)
    if template_id:
        context["template_id"] = template_id


def _resolve_template_path(context: dict[str, Any], jobspec_path: Path | None) -> Path | None:
    existing_path: Path | None = None
    if context.get("template_path"):
        candidate_existing = Path(context["template_path"]).expanduser().resolve()
        if candidate_existing.exists():
            existing_path = candidate_existing
        else:
            context.pop("template_path", None)
    candidate: Path | None = None
    env_value = os.environ.get("PPTX_TEMPLATE_PATH")
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
    elif jobspec_path and jobspec_path.exists():
        payload = _load_json_or_none(jobspec_path)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        template_rel = meta.get("template_path") if isinstance(meta, dict) else None
        if isinstance(template_rel, str) and template_rel.strip():
            rel_path = Path(template_rel)
            if rel_path.is_absolute():
                candidate = rel_path
            else:
                candidate = (jobspec_path.parent / rel_path).resolve()
                if not candidate.exists():
                    workspace = Path(__file__).resolve().parents[2]
                    candidate = (workspace / rel_path).resolve()
    if candidate and candidate.exists():
        context["template_path"] = str(candidate)
        return candidate
    return existing_path


def _load_blueprint(context: dict[str, Any], jobspec_path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    template_spec_path = _resolve_template_spec_path(context, jobspec_path)
    if template_spec_path is None:
        return None, None
    payload = _load_json_or_none(template_spec_path)
    if not isinstance(payload, dict):
        return None, None
    blueprint = payload.get("blueprint")
    template_source = payload.get("template_source")
    if isinstance(template_source, str):
        context["template_source"] = template_source
    if isinstance(blueprint, dict):
        return blueprint, template_source if isinstance(template_source, str) else None
    return None, template_source if isinstance(template_source, str) else None


def _build_prepare_document(
    *,
    template_id: str,
    blueprint: dict[str, Any] | None,
    excel_payload: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, int]]:
    slides = []
    if isinstance(blueprint, dict) and isinstance(blueprint.get("slides"), list):
        slides = [slide for slide in blueprint["slides"] if isinstance(slide, dict)]
    if not slides:
        slides = [
            {
                "slide_id": "static-slide-01",
                "layout": "Static",
                "slots": [
                    {
                        "slot_id": "static-slide-01.slot01",
                        "anchor": "body",
                        "content_type": "text",
                        "required": True,
                        "intent_tags": ["static"],
                    }
                ],
                "intent_tags": ["opening"],
            }
        ]

    message_lines = _build_message_lines(excel_payload)
    table_rows = _build_table_rows(excel_payload)
    summary_lines = _build_table_summaries(excel_payload)
    summary_iter = iter(summary_lines)
    table_map = {target: value for target, value in table_rows}

    cards: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    required_total = 0
    required_fulfilled = 0
    optional_used = 0

    card_order = 1
    for slide in slides:
        slide_cards: list[str] = []
        slots = slide.get("slots") if isinstance(slide.get("slots"), list) else []
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            card, fulfilled = _build_card_from_slot(
                slot=slot,
                slide=slide,
                order=card_order,
                template_id=template_id,
                message_lines=message_lines,
                table_rows=table_rows,
                table_map=table_map,
                summary_iter=summary_iter,
                summary_lines=summary_lines,
            )
            cards.append(card)
            slide_cards.append(card["card_id"])
            card_order += 1
            if slot.get("required"):
                required_total += 1
                if fulfilled:
                    required_fulfilled += 1
            else:
                if fulfilled:
                    optional_used += 1
        if slide_cards:
            chapters.append(
                {
                    "id": f"chapter-{len(chapters)+1}",
                    "title": slide.get("layout") or "Static Slide",
                    "cards": slide_cards,
                }
            )

    optional_total = max(len(cards) - required_total, 0)
    slot_summary = {
        "required_total": required_total,
        "required_fulfilled": required_fulfilled,
        "optional_total": optional_total,
        "optional_used": optional_used,
    }

    document = {
        "prepare_id": template_id or "static-template",
        "cards": cards,
        "story_context": {
            "chapters": chapters,
            "tone": None,
            "must_have_messages": [],
        },
        "meta": {
            "template_id": template_id,
            "source_excel": excel_payload["meta"].get("source_excel"),
            "prepare_log_path": str(output_dir / "prepare_log.json"),
            "prepare_ai_log_path": str(output_dir / "prepare_ai_log.json"),
            "ai_generation_meta_path": str(output_dir / "ai_generation_meta.json"),
            "prepare_story_outline_path": str(output_dir / "prepare_story_outline.json"),
        },
    }

    return document, slot_summary


def _build_card_from_slot(
    *,
    slot: dict[str, Any],
    slide: dict[str, Any],
    order: int,
    template_id: str,
    message_lines: list[str],
    table_rows: list[list[str]],
    table_map: dict[str, str],
    summary_iter: Iterator[str],
    summary_lines: list[str],
) -> tuple[dict[str, Any], bool]:
    slot_id = str(slot.get("slot_id") or f"slot-{order}")
    card_id = f"slot-{order:02d}"
    intent_tags = slot.get("intent_tags") if isinstance(slot.get("intent_tags"), list) else []
    if not intent_tags:
        slide_tags = slide.get("intent_tags") if isinstance(slide.get("intent_tags"), list) else []
        intent_tags = [tag for tag in slide_tags if isinstance(tag, str) and tag.strip()]
    if not intent_tags:
        intent_tags = [slot.get("content_type") or "static"]

    story_phase = _infer_story_phase(slide)
    anchor = str(slot.get("anchor") or "")
    slot_type = str(slot.get("content_type") or "text").lower()

    headline: str | None = None
    paragraphs: list[str] = []
    table_block: dict[str, Any] | None = None

    message_text = "\n".join(message_lines) if message_lines else ""
    default_texts = slot.get("default_text") if isinstance(slot.get("default_text"), list) else []
    keep_template = False
    if "タイトル" in anchor or anchor.lower() in {"title", "main title"}:
        headline = default_texts[0] if default_texts else "提示金額"
        paragraphs = [headline]
    elif anchor == "テキスト プレースホルダー 3":
        paragraphs = message_lines or ["提示金額情報が取得できませんでした"]
    elif anchor == "テキスト プレースホルダー 4":
        if default_texts:
            paragraphs = default_texts
        else:
            headline = KEEP_TEMPLATE_SENTINEL
            paragraphs = [KEEP_TEMPLATE_SENTINEL]
            keep_template = True
    elif anchor == "Rectangle 23":
        paragraphs = default_texts or ["営業秘密"]
    elif anchor == "テキスト プレースホルダー 2":
        paragraphs = default_texts or ["＜ご参考　SMBC直発注分＞"]
    elif slot_type in {"chart", "table"} or anchor.startswith("表"):
        if table_rows:
            if anchor == "表 10":
                table_block = _build_detail_table(table_map)
            else:
                table_block = {
                    "type": "table",
                    "headers": ["項目", "金額(億円)"],
                    "rows": table_rows,
                }
        else:
            paragraphs = [message_text or "金額表"]
    elif slot_type == "image":
        paragraphs = [f"{template_id} visual"]
    else:
        next_value = next(summary_iter, None)
        paragraphs = [next_value or anchor or slot_id]

    fulfilled = bool(headline or paragraphs or table_block)

    if headline is None:
        if paragraphs:
            headline = paragraphs[0]
        elif table_block and table_block.get("rows"):
            headline = f"{table_block['rows'][0][0]}"
        else:
            headline = anchor or slot_id

    content = {
        "headline": headline,
        "body": [{"type": "paragraph", "text": text} for text in paragraphs if text],
        "notes": [],
    }
    if table_block:
        content["body"].append(table_block)

    blueprint_meta = {
        "slot_id": slot_id,
        "anchor": anchor,
        "layout": slide.get("layout"),
        "slide_id": slide.get("slide_id"),
        "required": bool(slot.get("required")),
        "content_type": slot_type,
        "intent_tags": intent_tags,
        "fulfilled": fulfilled,
    }

    card = {
        "card_id": card_id,
        "order": order,
        "role": {
            "story_phase": story_phase,
            "intent_tags": intent_tags,
        },
        "content": content,
        "meta": {
            "blueprint": blueprint_meta,
            "source": {
                "anchor": anchor,
                "template_id": template_id,
            },
        },
    }

    if keep_template:
        card["meta"]["keep_template"] = True

    return card, fulfilled


def _infer_story_phase(slide: dict[str, Any]) -> str:
    tags = slide.get("intent_tags") if isinstance(slide.get("intent_tags"), list) else []
    lowered = {str(tag).lower() for tag in tags if isinstance(tag, str)}
    if "opening" in lowered:
        return "introduction"
    if "problem" in lowered:
        return "problem"
    if "solution" in lowered:
        return "solution"
    if "impact" in lowered:
        return "impact"
    if "next" in lowered:
        return "next"
    return "introduction"


def _build_message_lines(payload: dict[str, Any]) -> list[str]:
    message_line = payload.get("message_line") or {}
    initial = message_line.get("initial_amount", {}).get("formatted_value", "N/A")
    running_amount = message_line.get("running_amount", {}).get("formatted_value", "N/A")
    running_years = message_line.get("running_years", {}).get("formatted_value", "-")
    return [
        f"提示金額（初期）：{initial}億円",
        f"提示金額（ランニング）：{running_years} {running_amount}億円",
    ]


def _build_running_summary_text(message_lines: list[str], table_rows: list[list[str]]) -> str:
    summary = message_lines[1] if len(message_lines) > 1 else "ランニング情報"
    if table_rows:
        totals = ", ".join(f"{row[0]}={row[1]}" for row in table_rows[:3])
        return f"{summary}\n{totals}"
    return summary


def _build_table_rows(payload: dict[str, Any]) -> list[list[str]]:
    table = payload.get("table")
    if not isinstance(table, dict):
        return []
    rows: list[list[str]] = []
    for entry in table.values():
        if not isinstance(entry, dict):
            continue
        target = entry.get("target") or entry.get("source")
        formatted = entry.get("formatted_value")
        if target is None or formatted is None:
            continue
        rows.append([str(target), str(formatted)])
    return rows


def _build_table_summaries(payload: dict[str, Any]) -> list[str]:
    rows = _build_table_rows(payload)
    return [f"{target}: {value}億円" for target, value in rows]


def _build_detail_table(table_map: dict[str, str]) -> dict[str, Any]:
    si_value = table_map.get("SI")
    running_value = table_map.get("（２）ランニング 計")
    detail_parts: list[str] = []
    if si_value is not None:
        detail_parts.append(f"SI={si_value}")
    if running_value is not None:
        detail_parts.append(f"ランニング計={running_value}")
    detail_note = " / ".join(detail_parts) if detail_parts else "詳細は別紙参照"
    return {
        "type": "table",
        "rows": [
            ["システム・PP", "金額", "委託先", "算出根拠・対応内容　等"],
            ["システム構築", str(si_value or "N/A"), "SI", detail_note],
        ],
    }


def _build_generation_meta(
    *,
    template_id: str,
    excel_payload: dict[str, Any],
    cards: list[dict[str, Any]],
    slot_summary: dict[str, int],
    blueprint_path: str | None,
    template_source: str,
) -> dict[str, Any]:
    source_hash = hashlib.sha256(json.dumps(excel_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cards_meta = []
    for card in cards:
        cards_meta.append(
            {
                "card_id": card.get("card_id"),
                "story_phase": card.get("role", {}).get("story_phase"),
                "intent_tags": card.get("role", {}).get("intent_tags", []),
                "slot_id": card.get("meta", {}).get("blueprint", {}).get("slot_id"),
            }
        )
    return {
        "prepare_id": template_id or "static-template",
        "generated_at": excel_payload.get("extracted_at"),
        "policy_id": "external-static",
        "input_hash": source_hash,
        "cards": cards_meta,
        "statistics": {
            "cards_total": len(cards),
        },
        "mode": "static",
        "blueprint_path": blueprint_path,
        "slot_coverage": slot_summary,
        "prompt_templates": [],
        "slide_inputs": [],
        "template_source": template_source,
    }


def _build_story_outline(prepare_document: dict[str, Any]) -> dict[str, Any]:
    return {
        "prepare_id": prepare_document.get("prepare_id"),
        "chapters": prepare_document.get("story_context", {}).get("chapters", []),
        "narrative_theme": None,
        "summary": None,
    }


def _build_audit_log(
    *,
    cards_path: Path,
    log_path: Path,
    ai_log_path: Path,
    ai_meta_path: Path,
    story_outline_path: Path,
) -> dict[str, Any]:
    return {
        "prepare_normalization": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy_id": "external-static",
            "outputs": {
                "prepare_card": str(cards_path.resolve()),
                "prepare_log": str(log_path.resolve()),
                "prepare_ai_log": str(ai_log_path.resolve()),
                "ai_generation_meta": str(ai_meta_path.resolve()),
                "prepare_story_outline": str(story_outline_path.resolve()),
            },
            "statistics": {},
        }
    }


def main() -> int:
    layout_mode = os.environ.get("PPTX_MODE", "").lower()
    if layout_mode and layout_mode != "static":
        return 0

    context = _load_context()
    jobspec_path_env = os.environ.get("PPTX_JOBSPEC_PATH")
    jobspec_path = Path(jobspec_path_env).expanduser().resolve() if jobspec_path_env else None
    if jobspec_path and not jobspec_path.exists():
        jobspec_path = None

    template_id = _determine_template_id(context, jobspec_path)
    _reset_context_for_template(context, template_id)

    excel_path = resolve_input_path(env_var="JRI_EXCEL_SOURCE", inputs_key="excel_source_path", context=context)
    context["excel_source_path"] = str(excel_path)

    output_dir_env = os.environ.get("PPTX_PREPARE_OUTPUT_DIR")
    output_dir = Path(output_dir_env) if output_dir_env else Path(".pptx/prepare")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # mapping_config は固定パス（cost/mapping_config.json）。存在しなければエラー。
    mapping_path = DEFAULT_MAPPING_CONFIG
    if not mapping_path.exists():
        raise FileNotFoundError(f"mapping config not found: {mapping_path}")
    mapping = load_mapping_config(mapping_path)
    context["mapping_config_path"] = str(mapping_path)

    payload = extract_excel_data(excel_path, mapping)
    payload["meta"] = {
        "template_id": template_id,
        "source_excel": str(excel_path),
        "generated_by": "external_hook.stage02_prepare",
    }

    blueprint, template_source_meta = _load_blueprint(context, jobspec_path)
    _resolve_template_path(context, jobspec_path)
    prepare_document, slot_summary = _build_prepare_document(
        template_id=template_id,
        blueprint=blueprint,
        excel_payload=payload,
        output_dir=output_dir,
    )

    cards_path = output_dir / "prepare_card.json"
    cards_path.write_text(json.dumps(prepare_document, ensure_ascii=False, indent=2), encoding="utf-8")

    prepare_log_path = output_dir / "prepare_log.json"
    prepare_log_path.write_text("[]", encoding="utf-8")

    prepare_ai_log_path = output_dir / "prepare_ai_log.json"
    prepare_ai_log_path.write_text("[]", encoding="utf-8")

    ai_meta_path = output_dir / "ai_generation_meta.json"
    ai_meta_payload = _build_generation_meta(
        template_id=template_id,
        excel_payload=payload,
        cards=prepare_document["cards"],
        slot_summary=slot_summary,
        blueprint_path=context.get("template_spec_path"),
        template_source=template_source_meta or "slide",
    )
    ai_meta_path.write_text(json.dumps(ai_meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    story_outline_path = output_dir / "prepare_story_outline.json"
    story_outline = _build_story_outline(prepare_document)
    story_outline_path.write_text(json.dumps(story_outline, ensure_ascii=False, indent=2), encoding="utf-8")

    detail_rows: list[list[str]] | None = None
    for card in prepare_document["cards"]:
        blueprint = card.get("meta", {}).get("blueprint", {})
        if blueprint.get("anchor") == "表 10":
            for block in card.get("content", {}).get("body", []):
                if isinstance(block, dict) and block.get("type") == "table":
                    rows = block.get("rows")
                    if isinstance(rows, list):
                        detail_rows = rows
                    break
            break

    audit_log_path = output_dir / "audit_log.json"
    audit_log = _build_audit_log(
        cards_path=cards_path,
        log_path=prepare_log_path,
        ai_log_path=prepare_ai_log_path,
        ai_meta_path=ai_meta_path,
        story_outline_path=story_outline_path,
    )
    audit_log_path.write_text(json.dumps(audit_log, ensure_ascii=False, indent=2), encoding="utf-8")

    context.update(
        {
            "template_id": template_id or context.get("template_id", ""),
            "excel_source_path": str(excel_path),
            "mapping_config_path": str(mapping_path),
            "prepare_card_path": str(cards_path),
            "prepared_payload_path": context.get("prepared_payload_path") or str(cards_path),
            "extract_summary": payload,
            "prepare_log_path": str(prepare_log_path),
            "prepare_ai_log_path": str(prepare_ai_log_path),
            "template_source": template_source_meta or "slide",
        }
    )
    if detail_rows:
        context["table_detail_rows"] = detail_rows
    _persist_context(context)

    print(f"[stage02_prepare] prepare_card.json generated -> {cards_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
