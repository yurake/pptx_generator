from __future__ import annotations

from pathlib import Path

from pptx_generator.cli_handlers.rendering import resolve_config_path
from pptx_generator.settings.loader import load_branding_config, load_rules_config
from pptx_generator.settings.paths import find_config_path, get_default_config_path


def test_get_default_config_path_uses_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    path = get_default_config_path("rules.json")
    assert path.exists()
    assert "config" in path.parts


def test_find_config_path_prefers_local_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local_dir = tmp_path / "config"
    local_dir.mkdir()
    local_file = local_dir / "rules.json"
    local_file.write_text("{}", encoding="utf-8")

    find_config_path.cache_clear()
    resolved = find_config_path(Path("config/rules.json"))
    assert resolved == local_file.resolve()


def test_load_rules_config_falls_back_to_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    load_rules_config.cache_clear()
    config = load_rules_config("config/rules.json")
    assert config.analyzer.min_font_size == 18.0


def test_load_branding_config_falls_back_to_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    load_branding_config.cache_clear()
    branding = load_branding_config("config/branding.json")
    assert branding.heading_font.name


def test_resolve_config_path_falls_back_to_packaged_resource(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find_config_path.cache_clear()
    path = resolve_config_path("config/polisher-rules.json")
    assert path.exists()
