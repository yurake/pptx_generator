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
    continue_default: bool = False

    def run(self, *, cwd: Path, extra_env: Mapping[str, str] | None = None) -> None:
        """コマンドを実行する。"""
        env = os.environ.copy()
        for key, value in (extra_env or {}).items():
            env[key] = str(value)
        for key, value in self.env.items():
            env[key] = str(value)

        if self.shell:
            logger.info("外部フックを shell コマンドとして実行: %s", self.command)
            subprocess.run(  # noqa: PLW1510
                self.command,
                check=True,
                shell=True,
                cwd=cwd,
                env=env,
            )
            return

        command_list = [self.command, *self.args]
        logger.info("外部フックを実行: %s", " ".join(command_list))
        subprocess.run(  # noqa: PLW1510
            command_list,
            check=True,
            cwd=cwd,
            env=env,
        )


@dataclass(slots=True)
class SlideHookConfig:
    """スライド単位のフック設定。"""

    stage_hooks: dict[str, HookCommandConfig] = field(default_factory=dict)


@dataclass(slots=True)
class HookConfig:
    stage_hooks: dict[str, HookCommandConfig] = field(default_factory=dict)
    slide_hooks: dict[str, SlideHookConfig] = field(default_factory=dict)


class ExternalHookManager:
    """テンプレート単位の外部フック設定を管理する。"""

    def __init__(self, *, template_id: str, base_dir: Path, config: HookConfig) -> None:
        self.template_id = template_id
        self.base_dir = base_dir
        self.config = config

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
        hook.run(cwd=self.base_dir, extra_env=env)
        return True, hook.continue_default

    def get_slide_hooks(self, slide_key: str) -> SlideHookConfig | None:
        return self.config.slide_hooks.get(slide_key)


def load_hooks_for_template_id(template_id: str) -> ExternalHookManager | None:
    """template_id に対応する外部フック設定を読み込む。"""
    base_dir = EXTERNAL_ROOT / template_id
    config_path = base_dir / HOOKS_FILENAME
    if not config_path.exists():
        logger.debug("外部フック設定が見つかりません: %s", config_path)
        return None

    try:
        text = config_path.read_text(encoding="utf-8")
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("外部フック設定の解析に失敗しました: %s (%s)", config_path, exc)
        return None
    except OSError as exc:
        logger.error("外部フック設定の読み込みに失敗しました: %s (%s)", config_path, exc)
        return None

    config = _parse_hook_payload(payload)
    if not config.stage_hooks and not config.slide_hooks:
        logger.debug("外部フック設定に有効なエントリがありません: %s", config_path)
        return None

    return ExternalHookManager(template_id=template_id, base_dir=base_dir, config=config)


def _parse_hook_payload(payload: Any) -> HookConfig:
    config = HookConfig()
    if not isinstance(payload, dict):
        return config

    stage_section = payload.get("stage") or payload.get("stages")
    if isinstance(stage_section, dict):
        for raw_stage, raw_config in stage_section.items():
            stage = str(raw_stage).strip().lower()
            if stage not in KNOWN_STAGES:
                logger.debug("未知のステージフックをスキップしました: %s", raw_stage)
                continue
            hook = _parse_stage_hook(raw_config)
            if hook:
                config.stage_hooks[stage] = hook

    slides_section = payload.get("slides")
    if isinstance(slides_section, dict):
        for slide_key, slide_payload in slides_section.items():
            parsed = _parse_slide_hooks(slide_payload)
            if parsed.stage_hooks:
                config.slide_hooks[str(slide_key)] = parsed

    return config


def _parse_stage_hook(obj: Any) -> HookCommandConfig | None:
    if not isinstance(obj, dict):
        return None
    command = obj.get("command")
    if not isinstance(command, str) or not command.strip():
        return None

    args_raw = obj.get("args")
    args: list[str] = []
    if isinstance(args_raw, list):
        args = [str(item) for item in args_raw]

    env_raw = obj.get("env")
    env: dict[str, str] = {}
    if isinstance(env_raw, dict):
        env = {str(k): str(v) for k, v in env_raw.items()}

    shell = bool(obj.get("shell", False))
    continue_default = bool(obj.get("continue_default", False))

    return HookCommandConfig(
        command=command.strip(),
        args=args,
        env=env,
        shell=shell,
        continue_default=continue_default,
    )


def _parse_slide_hooks(obj: Any) -> SlideHookConfig:
    stage_hooks: dict[str, HookCommandConfig] = {}
    if isinstance(obj, dict):
        for stage_key, stage_payload in obj.items():
            stage = str(stage_key).strip().lower()
            hook = _parse_stage_hook(stage_payload)
            if hook:
                stage_hooks[stage] = hook
    return SlideHookConfig(stage_hooks=stage_hooks)
