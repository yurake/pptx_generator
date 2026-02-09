"""Click command wrappers for pptx_generator CLI."""

from .compose import create_compose_command
from .prepare import build_prepare_config, create_prepare_command
from .template import create_template_command
from .gen import create_gen_command

__all__ = [
    "build_prepare_config",
    "create_compose_command",
    "create_prepare_command",
    "create_gen_command",
    "create_template_command",
]
