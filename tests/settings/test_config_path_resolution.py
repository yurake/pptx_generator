from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.cli_handlers.rendering import resolve_config_path
from pptx_generator.settings.loader import load_rules_config
from pptx_generator.settings.paths import find_config_path, get_default_config_path


def test_get_default_config_path_uses_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    path = get_default_config_path("pipeline_rules.json")
    assert path.exists()
    assert "config" in path.parts


def test_find_config_path_prefers_local_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local_dir = tmp_path / "config"
    local_dir.mkdir()
    local_file = local_dir / "pipeline_rules.json"
    local_file.write_text("{}", encoding="utf-8")

    find_config_path.cache_clear()
    resolved = find_config_path(Path("config/pipeline_rules.json"))
    assert resolved == local_file.resolve()


def test_find_config_path_prefers_base_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_dir = tmp_path / "env"
    base_dir.mkdir()
    target = base_dir / "custom.json"
    target.write_text("{}", encoding="utf-8")

    find_config_path.cache_clear()
    resolved = find_config_path("custom.json", base_dir=base_dir)
    assert resolved == target.resolve()


def test_find_config_path_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    assert find_config_path("config/unknown.json") is None


def test_load_rules_config_falls_back_to_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    load_rules_config.cache_clear()
    config = load_rules_config("config/pipeline_rules.json")
    assert config.analyzer.min_font_size == 18.0


def test_load_rules_config_supports_legacy_filename(tmp_path, monkeypatch):
    """旧ファイル名(rules.json)指定でもパッケージ同梱にフォールバックする。"""

    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    load_rules_config.cache_clear()
    config = load_rules_config("config/rules.json")
    assert config.analyzer.min_font_size == 18.0


def test_load_rules_config_raises_when_missing(monkeypatch):
    load_rules_config.cache_clear()
    monkeypatch.setattr(
        "pptx_generator.settings.loader.find_config_path",
        lambda path, base_dir=None: None,
    )
    with pytest.raises(FileNotFoundError):
        load_rules_config("config/nonexistent.json")
    load_rules_config.cache_clear()


def test_resolve_config_path_falls_back_to_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    path = resolve_config_path("config/rules.json")
    assert path.exists()


def test_load_rules_config_prefers_legacy_when_pipeline_missing(monkeypatch):
    """パッケージ同梱 pipeline_rules.json が無い場合、legacy rules.json を読む。"""

    original_exists = Path.exists
    sentinel = Path("/tmp/legacy_rules.json")

    def fake_exists(self: Path) -> bool:
        if str(self).endswith("pipeline_rules.json"):
            return False
        if str(self).endswith("rules.json"):
            return True
        return original_exists(self)

    monkeypatch.setattr("pptx_generator.settings.loader.Path.exists", fake_exists)
    monkeypatch.setattr("pptx_generator.settings.loader.RulesConfig.load", lambda p: f"loaded:{p}")
    load_rules_config.cache_clear()

    result = load_rules_config("config/pipeline_rules.json")
    assert isinstance(result, str)
    assert result.endswith("rules.json")


def test_resolve_config_path_fallback_from_new_to_legacy(monkeypatch):
    """config/pipeline_rules.json 指定で見つからない場合、legacy rules.json を解決する。"""

    def fake_find(path: str | Path, *, base_dir: Path | None = None) -> Path | None:
        if str(path).endswith("rules.json"):
            return Path("/tmp/legacy_rules.json")
        return None

    monkeypatch.setattr("pptx_generator.cli_handlers.rendering.find_config_path", fake_find)
    path = resolve_config_path("custom/pipeline_rules.json")
    assert str(path).endswith("legacy_rules.json")


def test_load_rules_config_fallback_from_pipeline_to_legacy(monkeypatch):
    """config/pipeline_rules.json の解決に失敗した場合、legacy rules.json をロードする。"""

    def fake_find(path: str | Path, *, base_dir: Path | None = None) -> Path | None:
        if str(path).endswith("rules.json"):
            return Path("/tmp/legacy_rules.json")
        return None

    monkeypatch.setattr("pptx_generator.settings.loader.find_config_path", fake_find)
    monkeypatch.setattr("pptx_generator.settings.loader.RulesConfig.load", lambda p: f"loaded:{p}")
    load_rules_config.cache_clear()

    result = load_rules_config("custom/pipeline_rules.json")
    assert isinstance(result, str)
    assert result.endswith("legacy_rules.json")


def test_load_rules_config_fallback_from_legacy_to_pipeline(monkeypatch):
    """config/rules.json の解決に失敗した場合、新名称へフォールバックする。"""

    def fake_find(path: str | Path, *, base_dir: Path | None = None) -> Path | None:
        if str(path).endswith("pipeline_rules.json"):
            return Path("/tmp/pipeline_rules.json")
        return None

    monkeypatch.setattr("pptx_generator.settings.loader.find_config_path", fake_find)
    monkeypatch.setattr("pptx_generator.settings.loader.RulesConfig.load", lambda p: f"loaded:{p}")
    load_rules_config.cache_clear()

    result = load_rules_config("custom/rules.json")
    assert isinstance(result, str)
    assert result.endswith("pipeline_rules.json")


def test_resolve_config_path_uses_base_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_dir = tmp_path / "cfg"
    base_dir.mkdir()
    config_path = base_dir / "custom-config.json"
    config_path.write_text("{}", encoding="utf-8")

    find_config_path.cache_clear()
    resolved = resolve_config_path("custom-config.json", base_dir=base_dir)
    assert resolved == config_path.resolve()
