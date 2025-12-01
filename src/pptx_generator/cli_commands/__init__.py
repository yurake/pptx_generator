"""Click command wrappers for pptx_generator CLI."""

from .prepare import build_prepare_config, create_prepare_command
from .template import create_template_command

__all__ = [
    "build_prepare_config",
    "create_prepare_command",
    "create_template_command",
]
