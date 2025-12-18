"""Utility helpers to locate configuration assets.

リポジトリ直下の `config/` だけでなく、パッケージに同梱された設定
ファイルを解決するためのユーティリティ。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_CONFIG_ROOT = _PACKAGE_ROOT / "config"
_DEFAULT_OUTPUT_ROOT = Path(".pptx")


def _iter_candidates(path: Path, *, base_dir: Path | None) -> Iterable[Path]:
    if path.is_absolute():
        yield path
        return

    if base_dir is not None:
        yield base_dir / path

    yield Path.cwd() / path

    if path.parts and path.parts[0] == "config":
        relative = Path(*path.parts[1:]) if len(path.parts) > 1 else Path()
        yield _PACKAGE_CONFIG_ROOT / relative


@lru_cache(maxsize=None)
def find_config_path(path: str | Path, *, base_dir: Path | None = None) -> Path | None:
    """指定されたパスをローカルもしくはパッケージ同梱ディレクトリから解決する。"""

    candidate = Path(path).expanduser()
    for option in _iter_candidates(candidate, base_dir=base_dir):
        resolved = option.expanduser().resolve()
        if resolved.exists():
            return resolved
    return None


def get_default_config_path(filename: str) -> Path:
    """既定設定ファイルの実パスを取得する。"""

    candidate = Path("config") / filename
    resolved = find_config_path(candidate)
    if resolved is None:
        raise FileNotFoundError(f"デフォルト設定ファイルが見つかりません: {candidate}")
    return resolved


def get_output_root() -> Path:
    """出力ルートディレクトリを解決する。

    - `PPTX_OUTPUT_ROOT` が指定されていればそのパスを利用
    - 未指定の場合は `.pptx` を既定とする
    """

    env_root = os.getenv("PPTX_OUTPUT_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    return _DEFAULT_OUTPUT_ROOT


def build_output_dir(
    stage: str,
    *,
    transaction_id: str | None = None,
    job_id: str | None = None,
    root: Path | None = None,
) -> Path:
    """ステージ別の出力ディレクトリを組み立てる。

    tx/job が渡された場合は `<root>/<tx>/<stage>/<job>/`、
    それ以外は `<root>/<stage>/` を返す。
    """

    base = root or get_output_root()
    segments = [base]
    if transaction_id:
        segments.append(Path(transaction_id))
    segments.append(Path(stage))
    if job_id:
        segments.append(Path(job_id))
    return Path().joinpath(*segments)


__all__ = ["find_config_path", "get_default_config_path", "get_output_root", "build_output_dir"]
