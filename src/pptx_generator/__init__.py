"""pptx_generator パッケージ。"""

from importlib import metadata

__all__ = ["__version__"]


def _load_version() -> str:
    try:
        return metadata.version("pptx-generator")
    except metadata.PackageNotFoundError:
        return "0.1.0"


__version__ = _load_version()
