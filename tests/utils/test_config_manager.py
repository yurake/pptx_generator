from pptx_generator.config_manager import ConfigManager


def test_config_manager_prefers_higher_priority() -> None:
    manager = ConfigManager()
    manager.add_source("defaults", {"template_path": "default.pptx"})
    manager.add_source("template_config", {"template_path": "spec.pptx"})
    manager.add_source("env_variables", {"template_path": "env.pptx"})
    manager.add_source("cli_options", {"template_path": "cli.pptx", "output_dir": "/tmp/out"})

    value, source = manager.resolve_with_source("template_path")
    assert value == "cli.pptx"
    assert source == "cli_options"

    manager.record("template_path", "/abs/cli.pptx", source)
    snapshot = manager.snapshot()
    assert snapshot.values["template_path"] == "/abs/cli.pptx"
    assert snapshot.sources["template_path"] == "cli_options"
    assert snapshot.priority_order[0] == "cli_options"


def test_config_manager_falls_back_to_defaults() -> None:
    manager = ConfigManager()
    manager.add_source("defaults", {"layouts_path": "layouts.jsonl"})

    value, source = manager.resolve_with_source("layouts_path")
    assert value == "layouts.jsonl"
    assert source == "defaults"

    snapshot = manager.snapshot(keys=["layouts_path", "missing"])
    assert snapshot.values["layouts_path"] == "layouts.jsonl"
    assert snapshot.sources["layouts_path"] == "defaults"
