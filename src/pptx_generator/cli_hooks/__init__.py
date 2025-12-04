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
)
from .template_id import (
    derive_template_id_from_template_path,
    extract_template_id_from_json_file,
)

__all__ = [
    "ExternalHookManager",
    "load_hooks_for_template_id",
    "derive_template_id_from_template_path",
    "extract_template_id_from_json_file",
    "STAGE_TEMPLATE",
    "STAGE_PREPARE",
    "STAGE_COMPOSE",
    "STAGE_MAPPING",
    "STAGE_GEN",
    "KNOWN_STAGES",
    "EXTERNAL_ROOT",
]
