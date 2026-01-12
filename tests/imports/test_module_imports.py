from importlib import import_module

import pytest


def test_new_template_imports() -> None:
    template = import_module("pptx_generator.template")

    assert hasattr(template, "load_jobspec_from_path")
    assert hasattr(template, "extract_branding_config")
    assert hasattr(template, "template_style_from_branding")

    # 直接モジュールからも import できることを確認
    branding = import_module("pptx_generator.template.branding_extractor")
    assert hasattr(branding, "BrandingExtractionError")

    spec_loader = import_module("pptx_generator.template.spec_loader")
    assert hasattr(spec_loader, "convert_scaffold_to_jobspec")


def test_new_draft_imports() -> None:
    draft = import_module("pptx_generator.draft")

    assert hasattr(draft, "CardLayoutRecommender")
    assert hasattr(draft, "LayoutProfile")
    assert hasattr(draft, "load_return_reasons")


@pytest.mark.parametrize(
    "module_name",
    [
        "pptx_generator.spec_loader",
        "pptx_generator.branding_extractor",
        "pptx_generator.draft_intel",
        "pptx_generator.draft_recommender",
    ],
)
def test_legacy_modules_removed(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        import_module(module_name)
