"""Open XML Polisher を呼び出すステップ。"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .base import PipelineContext

logger = logging.getLogger(__name__)


class PolisherError(RuntimeError):
    """Polisher 実行失敗時に送出される例外。"""


@dataclass(slots=True)
class PolisherOptions:
    """Polisher 呼び出しに関する設定。"""

    enabled: bool = False
    executable: Path | None = None
    rules_path: Path | None = None
    timeout_sec: int = 90
    arguments: tuple[str, ...] = ()
    working_dir: Path | None = None


class PolisherStep:
    """Open XML SDK ベースの仕上げ処理を呼び出すステップ。"""

    name = "polisher"

    def __init__(self, options: PolisherOptions | None = None) -> None:
        self.options = options or PolisherOptions()

    def run(self, context: PipelineContext) -> None:
        if not self.options.enabled:
            logger.debug("Polisher は無効化されています")
            context.add_artifact(
                "polisher_metadata",
                {
                    "status": "disabled",
                    "enabled": False,
                },
            )
            return

        pptx_reference = context.require_artifact("pptx_path")
        pptx_path = Path(str(pptx_reference))
        if not pptx_path.exists():  # pragma: no cover - 異常系
            msg = f"PPTX ファイルが存在しません: {pptx_path}"
            raise PolisherError(msg)

        command = self._build_command(pptx_path)
        cwd = str(self.options.working_dir) if self.options.working_dir else None

        logger.info("Polisher を実行します: %s", " ".join(command))
        start = time.perf_counter()
        try:
            completed = subprocess.run(  # noqa: S603, S607
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.options.timeout_sec,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - 異常系
            raise PolisherError("Polisher の実行がタイムアウトしました") from exc
        except subprocess.CalledProcessError as exc:  # pragma: no cover - 異常系
            stdout = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            msg = (
                f"Polisher の実行に失敗しました (exit={exc.returncode}).\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )
            raise PolisherError(msg) from exc
        finally:
            elapsed = time.perf_counter() - start

        metadata: dict[str, Any] = {
            "status": "success",
            "enabled": True,
            "command": command,
            "elapsed_sec": elapsed,
            "returncode": completed.returncode,
        }

        stdout_text = completed.stdout.decode("utf-8", errors="replace") if completed.stdout else ""
        stderr_text = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""

        if stdout_text:
            metadata["stdout"] = stdout_text
            summary = self._extract_summary(stdout_text)
            if summary is not None:
                metadata["summary"] = summary
        if stderr_text:
            metadata["stderr"] = stderr_text
        if self.options.rules_path:
            metadata["rules_path"] = str(self.options.rules_path)

        context.add_artifact("polisher_metadata", metadata)

    def _build_command(self, pptx_path: Path) -> list[str]:
        executable = self._resolve_executable()
        args = self._prepare_arguments(pptx_path)
        return [str(token) for token in executable] + list(args)

    def _resolve_executable(self) -> list[str]:
        candidate = self.options.executable
        if candidate is None:
            env_value = os.environ.get("POLISHER_EXECUTABLE") or os.environ.get("POLISHER_PATH")
            if env_value:
                candidate = Path(env_value)
        if candidate is None:
            msg = "Polisher の実行ファイルが指定されていません (--polisher-path または設定ファイルを確認してください)"
            raise PolisherError(msg)

        if isinstance(candidate, Path):
            path_candidate = candidate
        else:
            path_candidate = Path(str(candidate))

        if path_candidate.exists():
            if path_candidate.suffix.lower() == ".dll":
                return ["dotnet", str(path_candidate)]
            return [str(path_candidate)]

        resolved = shutil.which(str(path_candidate))
        if resolved:
            return [resolved]

        msg = f"Polisher の実行ファイルが見つかりません: {path_candidate}"
        raise PolisherError(msg)

    def _prepare_arguments(self, pptx_path: Path) -> Iterable[str]:
        rules_path = self.options.rules_path
        args = list(self.options.arguments)

        def _contains_placeholder(values: Iterable[str], placeholder: str) -> bool:
            return any(placeholder in value for value in values)

        if not _contains_placeholder(args, "{pptx}"):
            args.extend(["--input", "{pptx}"])
        if rules_path and not _contains_placeholder(args, "{rules}"):
            args.extend(["--rules", "{rules}"])

        template = {"pptx": str(pptx_path)}
        if rules_path:
            template["rules"] = str(rules_path)

        formatted: list[str] = []
        for item in args:
            try:
                formatted_item = item.format(**template)
            except KeyError as exc:
                msg = f"Polisher 引数テンプレートのプレースホルダー解決に失敗しました: {item}"
                raise PolisherError(msg) from exc
            if formatted_item:
                formatted.append(formatted_item)
        return formatted

    @staticmethod
    def _extract_summary(stdout_text: str) -> dict[str, Any] | None:
        try:
            data = json.loads(stdout_text)
        except json.JSONDecodeError:
            return None

        if isinstance(data, dict):
            return data
        return None
