"""Click command wrappers for pptx_generator CLI."""

from .compose import create_compose_command
from .layout_validate import create_layout_validate_command
from .mapping import create_mapping_command
from .outline import create_outline_command
from .prepare import build_prepare_config, create_prepare_command
from .template import create_template_command
from .tpl_extract import create_tpl_extract_command
from .tpl_release import create_tpl_release_command
from .gen import create_gen_command
from .edit import create_edit_apply_command

__all__ = [
    "build_prepare_config",
    "create_compose_command",
    "create_layout_validate_command",
    "create_mapping_command",
    "create_outline_command",
    "create_prepare_command",
    "create_gen_command",
    "create_edit_apply_command",
    "create_template_command",
    "create_tpl_extract_command",
    "create_tpl_release_command",
]
