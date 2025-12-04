"""外部フック設定のロードと実行ユーティリティ。"""

from .manager import (
    EXTERNAL_ROOT,
    KNOWN_STAGES,
    STAGE_COMPOSE,
    STAGE_GEN,
    STAGE_MAPPING,
    STAGE_PREPARE,
    STAGE_TEMPLATE,
    ExternalHookManager,
    load_hooks_for_template_id,
    SlideContext,
)
from .template_id import (
    derive_template_id_from_template_path,
    extract_template_id_from_json_file,
)
from .slides import (
    build_slide_key,
    slide_contexts_from_blueprint,
    slide_contexts_from_generate_ready,
)
from .scaffold import ensure_hook_skeleton

__all__ = [
    "ExternalHookManager",
    "load_hooks_for_template_id",
    "SlideContext",
    "derive_template_id_from_template_path",
    "extract_template_id_from_json_file",
    "STAGE_TEMPLATE",
    "STAGE_PREPARE",
    "STAGE_COMPOSE",
    "STAGE_MAPPING",
    "STAGE_GEN",
    "KNOWN_STAGES",
    "EXTERNAL_ROOT",
    "build_slide_key",
    "slide_contexts_from_blueprint",
    "slide_contexts_from_generate_ready",
    "ensure_hook_skeleton",
]
