"""外部フックスクリプトのロードと実行を担うモジュール。"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

HOOKS_FILENAME = "hooks.json"
EXTERNAL_ROOT = Path("external")

STAGE_TEMPLATE = "template"
STAGE_PREPARE = "prepare"
STAGE_COMPOSE = "compose"
STAGE_MAPPING = "mapping"
STAGE_GEN = "gen"

KNOWN_STAGES = {
    STAGE_TEMPLATE,
    STAGE_PREPARE,
    STAGE_COMPOSE,
    STAGE_MAPPING,
    STAGE_GEN,
}


@dataclass(slots=True)
class HookCommandConfig:
    """外部コマンド実行の設定。"""

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    shell: bool = False
    continue_default: bool = True

    def run(self, *, cwd: Path, extra_env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """コマンドを実行する。"""
        env = os.environ.copy()
        for key, value in (extra_env or {}).items():
            env[key] = str(value)
        for key, value in self.env.items():
            env[key] = str(value)

        if self.shell:
            logger.info("外部フックを shell コマンドとして実行: %s", self.command)
            proc = subprocess.run(  # noqa: PLW1510
                self.command,
                check=True,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
            )
        else:
            command_list = [self.command, *self.args]
            logger.info("外部フックを実行: %s", " ".join(command_list))
            proc = subprocess.run(  # noqa: PLW1510
                command_list,
                check=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
            )
        _log_subprocess_output("hook", proc.stdout, proc.stderr)
        return proc


@dataclass(slots=True)
class SlideHookConfig:
    """スライド単位のフック設定。"""

    stage_hooks: dict[str, HookCommandConfig] = field(default_factory=dict)


@dataclass(slots=True)
class HookConfig:
    stage_hooks: dict[str, HookCommandConfig] = field(default_factory=dict)
    slide_hooks: dict[str, SlideHookConfig] = field(default_factory=dict)


@dataclass(slots=True)
class SlideContext:
    key: str
    index: int
    slide_id: str | None = None
    layout: str | None = None
    extra_env: dict[str, str] = field(default_factory=dict)


class ExternalHookManager:
    """テンプレート単位の外部フック設定を管理する。"""

    def __init__(self, *, template_id: str, base_dir: Path, config: HookConfig) -> None:
        self.template_id = template_id
        self.base_dir = base_dir
        self.config = config
        self._synced_once = False

    @property
    def has_hooks(self) -> bool:
        return bool(self.config.stage_hooks)

    def run_stage_hook(
        self,
        stage: str,
        *,
        env: Mapping[str, str],
    ) -> tuple[bool, bool]:
        """指定ステージのフックを実行する。

        Returns:
            (executed, continue_default)
        """
        hook = self.config.stage_hooks.get(stage)
        if not hook:
            return False, False

        logger.debug(
            "テンプレート %s に対しステージ %s の外部フックを呼び出します",
            self.template_id,
            stage,
        )
        self._sync_project_if_needed(force=False)
        self._execute_hook(hook, env)
        return True, hook.continue_default

    def get_slide_hooks(self, slide_key: str) -> SlideHookConfig | None:
        return self.config.slide_hooks.get(slide_key)

    def run_slide_hooks(
        self,
        stage: str,
        *,
        slides: list[SlideContext],
        env: Mapping[str, str],
        continue_default_filter: bool | None = None,
        allow_fallback_context: bool = False,
    ) -> bool:
        """スライド単位のフックを実行する。

        Args:
            stage: ステージ名。
            slides: スライドコンテキストのリスト。
            env: 共通環境変数。
            continue_default_filter: True/False を指定すると、該当する continue_default のフックのみ実行する。
            allow_fallback_context: True のとき、slides が空でも hooks.json のスライドキーから疑似コンテキストを生成する。

        Returns:
            何らかのフックが実行されたかどうか。
        """

        contexts = list(slides)
        if not contexts and allow_fallback_context and self.config.slide_hooks:
            contexts = [
                SlideContext(key=key, index=idx)
                for idx, key in enumerate(self.config.slide_hooks.keys(), start=1)
            ]

        executed_any = False
        sync_done = False
        for slide in contexts:
            hook_config = self.get_slide_hooks(slide.key)
            if not hook_config:
                continue
            hook = hook_config.stage_hooks.get(stage)
            if not hook:
                continue
            if continue_default_filter is not None and hook.continue_default != continue_default_filter:
                continue
            if not sync_done:
                self._sync_project_if_needed(force=False)
                sync_done = True
            slide_env = dict(env)
            slide_env.update(
                {
                    "PPTX_SLIDE_KEY": slide.key,
                    "PPTX_SLIDE_INDEX": str(slide.index),
                    "PPTX_SLIDE_ID": slide.slide_id or "",
                    "PPTX_SLIDE_LAYOUT": slide.layout or "",
                }
            )
            for key, value in slide.extra_env.items():
                slide_env[key] = value
            self._execute_hook(hook, slide_env)
            executed_any = True
        return executed_any

    def _sync_project_if_needed(self, *, force: bool) -> None:
        project_root = self.base_dir
        has_project_files = any(
            (project_root / candidate).exists() for candidate in ("pyproject.toml", "uv.lock")
        )
        if has_project_files and (not self._synced_once or force):
            logger.info("フック実行前に `uv sync` を実行します: %s", project_root)
            subprocess.run(  # noqa: PLW1510
                ["uv", "sync", "--frozen"],
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True,
            )
            self._synced_once = True

    def _execute_hook(self, hook: HookCommandConfig, env: Mapping[str, str]) -> None:
        try:
            hook.run(cwd=self.base_dir, extra_env=env)
        except subprocess.CalledProcessError as exc:  # noqa: PERF203
            msg = f"フックの実行に失敗しました: {exc}\nstdout: {exc.stdout}\nstderr: {exc.stderr}"
            raise RuntimeError(msg) from exc

    def _load_hook(self, hook_path: Path) -> HookConfig:
        if not hook_path.exists():
            msg = f"外部フック設定が見つかりません: {hook_path}"
            raise FileNotFoundError(msg)

        with hook_path.open(encoding="utf-8") as f:
            obj = json.load(f)

        stage_hooks = {key: _build_command_config(value) for key, value in obj.get("stage", {}).items()}

        slide_hooks = {}
        for slide_key, slide_config in obj.get("slides", {}).items():
            stage_config = slide_config.get("stage", slide_config)
            slide_hooks[slide_key] = SlideHookConfig(
                stage_hooks={
                    stage: _build_command_config(command) for stage, command in stage_config.items()
                }
            )

        return HookConfig(stage_hooks=stage_hooks, slide_hooks=slide_hooks)

    def _ensure_project_dir(self) -> None:
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class LoadedHookConfig:
    template_id: str
    base_dir: Path
    hook_config: HookConfig


def _build_command_config(obj: dict) -> HookCommandConfig:
    command = str(obj["command"])
    args = [str(arg) for arg in obj.get("args", [])]
    env = {str(key): str(value) for key, value in obj.get("env", {}).items()}
    shell = bool(obj.get("shell"))
    continue_default = bool(obj.get("continue_default", True))
    return HookCommandConfig(
        command=command,
        args=args,
        env=env,
        shell=shell,
        continue_default=continue_default,
    )


def load_hooks_for_template_id(template_id: str) -> ExternalHookManager | None:
    hooks_path = EXTERNAL_ROOT / template_id / HOOKS_FILENAME
    base_dir = hooks_path.parent
    if not hooks_path.exists():
        return None

    hook_manager = ExternalHookManager(
        template_id=template_id,
        base_dir=base_dir,
        config=ExternalHookManager._load_hook(ExternalHookManager, hooks_path),
    )
    hook_manager._ensure_project_dir()
    return hook_manager


def derive_template_id_from_template_path(template_path: Path) -> str:
    return template_id_from_path(template_path)


def _log_subprocess_output(prefix: str, stdout: str | None, stderr: str | None) -> None:
    if stdout:
        logger.info("%s stdout:\n%s", prefix, stdout)
    if stderr:
        logger.info("%s stderr:\n%s", prefix, stderr)
