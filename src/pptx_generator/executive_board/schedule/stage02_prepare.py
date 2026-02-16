#!/usr/bin/env python3
"""Stage2 hook for schedule: generate prepare_card.json for static compose."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.stage_shared import load_context, persist_context, resolve_input_path, resolve_local_path  # noqa: E402


def _configure_sys_path() -> None:
    src_dir = Path(__file__).resolve().parents[3] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    schedule_dir = Path(__file__).resolve().parent
    if str(schedule_dir) not in sys.path:
        sys.path.insert(0, str(schedule_dir))


_configure_sys_path()

from schedule_parser import (  # noqa: E402
    parse_schedule_markdown,
    save_schedule_json,
)
from pptx_generator.prepare.models import (  # noqa: E402
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareChapterDefinition,
    PrepareDocument,
    PrepareStoryContext,
)


DEFAULT_MD = Path(__file__).resolve().parents[1] / "input/schedule.md"
DEFAULT_JOBSPEC = Path(__file__).resolve().parents[2] / "runtime/context.json"
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[3] / "templates/schedule.pptx"


def _load_json_or_none(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _determine_template_id(context: dict[str, Any], jobspec_path: Path | None) -> str:
    env_template_id = os.environ.get("PPTX_TEMPLATE_ID")
    if isinstance(env_template_id, str) and env_template_id.strip():
        context["template_id"] = env_template_id.strip()
        return env_template_id.strip()

    if jobspec_path and jobspec_path.exists():
        payload = _load_json_or_none(jobspec_path)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        candidate = meta.get("template_id") if isinstance(meta, dict) else None
        if isinstance(candidate, str) and candidate.strip():
            context["template_id"] = candidate.strip()
            return candidate.strip()

    existing = context.get("template_id")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()
    return "executive_board"


def _resolve_template_spec_path(context: dict[str, Any], jobspec_path: Path | None) -> Path | None:
    if context.get("template_spec_path"):
        candidate = Path(context["template_spec_path"]).expanduser().resolve()
        if candidate.exists():
            return candidate
        context.pop("template_spec_path", None)

    if jobspec_path and jobspec_path.exists():
        payload = _load_json_or_none(jobspec_path)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        spec_rel = meta.get("template_spec_path") if isinstance(meta, dict) else None
        if isinstance(spec_rel, str) and spec_rel.strip():
            rel_path = Path(spec_rel)
            resolved = (jobspec_path.parent / rel_path).resolve() if not rel_path.is_absolute() else rel_path
            if resolved.exists():
                context["template_spec_path"] = str(resolved)
                return resolved
    return None


def _resolve_template_path(context: dict[str, Any], jobspec_path: Path | None) -> Path:
    candidates: list[Path] = []
    env_template = os.environ.get("PPTX_TEMPLATE_PATH")
    if isinstance(env_template, str) and env_template.strip():
        candidates.append(Path(env_template).expanduser())

    if jobspec_path and jobspec_path.exists():
        payload = _load_json_or_none(jobspec_path)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        template_rel = meta.get("template_path") if isinstance(meta, dict) else None
        if isinstance(template_rel, str) and template_rel.strip():
            rel_path = Path(template_rel)
            if rel_path.is_absolute():
                candidates.append(rel_path)
            else:
                candidates.append(rel_path)
                candidates.append(jobspec_path.parent / rel_path)

    if context.get("template_path"):
        candidates.append(Path(context["template_path"]).expanduser())

    candidates.append(DEFAULT_TEMPLATE)

    anchor = Path(__file__).resolve().parent
    for candidate in candidates:
        resolved = resolve_local_path(str(candidate), anchor)
        if resolved.exists():
            context["template_path"] = str(resolved)
            return resolved
        # 追加: CWD 基準でも探索（jobspecの相対パスを素直に解決するため）
        cwd_resolved = Path(candidate).expanduser().resolve()
        if cwd_resolved.exists():
            context["template_path"] = str(cwd_resolved)
            return cwd_resolved

    fallback = Path(__file__).resolve().parents[1] / "input" / "executive_board.pptx"
    if fallback.exists():
        context["template_path"] = str(fallback)
        return fallback

    raise FileNotFoundError("Template PPTX not found. Provide PPTX_TEMPLATE_PATH or generate jobspec.")


def _resolve_jobspec_path() -> Path | None:
    env_jobspec = os.environ.get("PPTX_JOBSPEC_PATH")
    if isinstance(env_jobspec, str) and env_jobspec.strip():
        candidate = Path(env_jobspec).expanduser().resolve()
        if candidate.exists():
            return candidate
    # fallback to template extract under .pptx
    default = Path(".pptx/executive_board/extract/jobspec.json")
    if default.exists():
        return default
    return None


def _resolve_schedule_md(context: dict[str, Any]) -> Path:
    return resolve_input_path(
        env_var="PPTX_SCHEDULE_MD",
        inputs_key="schedule_md_path",
        context=context,
    )


def _normalize_card_id(slot_id: str) -> str:
    normalized = slot_id.replace(".", "-").replace("_", "-").lower()
    if not normalized[0].isalnum():
        normalized = f"slot-{normalized}"
    return normalized


def _build_prepare_cards(schedule) -> list[PrepareCard]:
    meta = schedule.meta
    headline = meta.title or "スケジュール"
    message = meta.message_line or ""

    def _text_block(text: str | None) -> list[PrepareBodyBlock]:
        return [PrepareBodyBlock(type="paragraph", text=text or "")]

    def _card(blueprint_slot_id: str, anchor: str, content_type: str, body: list[PrepareBodyBlock], order: int) -> PrepareCard:
        headline_value = headline if anchor == "タイトル 3" else None
        if headline_value is None:
            fallback = None
            if body:
                first = body[0]
                if first.text:
                    fallback = first.text
            headline_value = fallback or anchor or "schedule"

        content = PrepareCardContent(
            headline=headline_value,
            body=body,
            notes=[],
        )
        role = PrepareCardRole(
            story_phase="introduction",
            intent_tags=["schedule"],
        )
        return PrepareCard(
            card_id=_normalize_card_id(blueprint_slot_id).replace("id-", "slot-"),
            order=order,
            role=role,
            content=content,
            meta={
                "blueprint": {
                    "slot_id": blueprint_slot_id,
                    "anchor": anchor,
                    "layout": "system_layout-02",
                    "slide_id": "id_256-02",
                    "required": True,
                    "content_type": content_type,
                    "intent_tags": ["body"],
                    "fulfilled": True if body else False,
                }
            },
        )

    cards: list[PrepareCard] = []

    # slot01: message line
    cards.append(_card("id_256-02.slot01", "テキスト プレースホルダー 1", "text", _text_block(message or headline), 1))

    # slot02: summary
    summary_lines = [f"{p.name}: {t.start} 〜 {t.end}" for p in schedule.projects for t in p.tasks][:3]
    cards.append(
        _card(
            "id_256-02.slot02",
            "テキスト プレースホルダー 2",
            "text",
            _text_block("\n".join(summary_lines) if summary_lines else message),
            2,
        )
    )

    # slot03: タイトル
    cards.append(_card("id_256-02.slot03", "タイトル 3", "text", _text_block(headline), 3))

    # slot04: タスク一覧
    detail_blocks: list[PrepareBodyBlock] = []
    for project in schedule.projects:
        for task in project.tasks:
            detail_blocks.append(PrepareBodyBlock(type="bullets", text=f"{task.name}: {task.start} 〜 {task.end}"))
    cards.append(_card("id_256-02.slot04", "テキスト プレースホルダー 4", "text", detail_blocks, 4))

    # slot05: 画像占位
    cards.append(_card("id_256-02.slot05", "コンテンツ プレースホルダー 5", "image", _text_block(headline), 5))

    return cards


def _build_story_context(schedule) -> PrepareStoryContext:
    return PrepareStoryContext(
        chapters=[PrepareChapterDefinition(id="chapter-1", title=schedule.meta.title or "スケジュール")],
        tone=None,
        must_have_messages=[],
    )


def main(argv: list[str] | None = None) -> int:
    layout_mode = os.environ.get("PPTX_MODE", "").lower()
    if layout_mode and layout_mode != "static":
        return 0

    parser = argparse.ArgumentParser(description="schedule.md prepare hook for executive_board")
    parser.add_argument("--md", help="スケジュールMarkdownのパス (PPTX_SCHEDULE_MD より優先)")
    parser.add_argument("--output", help="出力ディレクトリ (PPTX_PREPARE_OUTPUT_DIR より優先)")
    parser.add_argument("--message", help="メッセージライン上書き (PPTX_SCHEDULE_MESSAGE より優先)")
    args = parser.parse_args(argv)

    context = load_context()

    jobspec_path = _resolve_jobspec_path()
    template_id = _determine_template_id(context, jobspec_path)
    _resolve_template_spec_path(context, jobspec_path)
    _resolve_template_path(context, jobspec_path)

    schedule_md = (
        Path(args.md).expanduser().resolve()
        if args.md
        else resolve_input_path(
            env_var="PPTX_SCHEDULE_MD",
            inputs_key="schedule_md_path",
            context=context,
        )
    )
    if not schedule_md.exists():
        raise FileNotFoundError(f"schedule markdown not found: {schedule_md}")

    output_dir_env = os.environ.get("PPTX_PREPARE_OUTPUT_DIR")
    output_dir = Path(args.output).expanduser() if args.output else Path(output_dir_env) if output_dir_env else Path(".pptx/prepare")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    message_override = args.message or os.environ.get("PPTX_SCHEDULE_MESSAGE")

    schedule = parse_schedule_markdown(schedule_md)
    if message_override:
        schedule.meta.message_line = message_override

    cards = _build_prepare_cards(schedule)
    story = _build_story_context(schedule)
    document = PrepareDocument(
        prepare_id=template_id or "executive_board",
        cards=cards,
        story_context=story,
        meta={
            "template_id": template_id,
            "schedule_source": str(schedule_md),
        },
    )

    cards_path = output_dir / "prepare_card.json"
    # 既存の prepare_card.json がある場合はカードとストーリーをマージする（スライド別フックを統合）
    if cards_path.exists():
        try:
            existing = json.loads(cards_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if isinstance(existing, dict):
            existing_cards = existing.get("cards") if isinstance(existing.get("cards"), list) else []
            merged_cards = existing_cards + document.model_dump(mode="json", exclude_none=True)["cards"]

            existing_story = existing.get("story_context") if isinstance(existing.get("story_context"), dict) else {}
            existing_chapters = existing_story.get("chapters") if isinstance(existing_story.get("chapters"), list) else []
            new_chapters = document.story_context.model_dump(mode="json", exclude_none=True).get("chapters", [])
            # 章は id でユニーク化
            chapter_by_id: dict[str, dict] = {}
            for ch in existing_chapters + new_chapters:
                if isinstance(ch, dict) and ch.get("id"):
                    chapter_by_id[ch["id"]] = ch
            merged_story = {
                "chapters": list(chapter_by_id.values()),
                "tone": existing_story.get("tone") or document.story_context.tone,
                "must_have_messages": existing_story.get("must_have_messages") or document.story_context.must_have_messages,
            }

            merged = {
                "prepare_id": existing.get("prepare_id") or document.prepare_id,
                "cards": merged_cards,
                "story_context": merged_story,
                "meta": existing.get("meta") or document.meta,
            }
            cards_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            cards_path.write_text(json.dumps(document.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        cards_path.write_text(json.dumps(document.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2), encoding="utf-8")

    schedule_json_path = output_dir / "schedule_data.json"
    save_schedule_json(schedule, schedule_json_path)

    context.update(
        {
            "template_id": template_id,
            "jobspec_path": str(jobspec_path) if jobspec_path else context.get("jobspec_path"),
            "schedule_md_path": str(schedule_md),
            "schedule_json_path": str(schedule_json_path),
            "prepare_card_path": str(cards_path),
            "generate_ready_path": str(cards_path),
        }
    )
    persist_context(context)

    print(f"[stage02_prepare] prepare_card.json -> {cards_path}")
    print(f"[stage02_prepare] schedule JSON -> {schedule_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
