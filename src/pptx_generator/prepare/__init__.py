"""Prepare domain shim to maintain backward compatibility.

This module re-exports symbols from :mod:`pptx_generator.brief` so that
consumers can migrate to the new ``pptx_generator.prepare`` namespace in stages.
The underlying implementations still live in ``pptx_generator.brief`` and will
be renamed in later iterations.
"""

from ..brief import *  # noqa: F401,F403
from ..brief import __all__ as _BRIEF_ALL

__all__ = _BRIEF_ALL
