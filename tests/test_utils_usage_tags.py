from pptx_generator.utils.usage_tags import (
    normalize_usage_tag_value,
    normalize_usage_tags,
    normalize_usage_tags_with_unknown,
)


def test_normalize_usage_tags_removes_duplicates_and_maps_synonyms():
    tags = ["Title", "content", "cover", "Title"]
    actual = normalize_usage_tags(tags)
    assert actual == ("title", "content")


def test_normalize_usage_tags_with_unknown_reports_unknown_values():
    tags = ["Title", "new-tag"]
    actual, unknown = normalize_usage_tags_with_unknown(tags)
    assert actual == ("title",)
    assert unknown == {"new-tag"}


def test_normalize_usage_tag_value_maps_single_value():
    assert normalize_usage_tag_value("Cover") == "title"
    assert normalize_usage_tag_value("agenda") == "agenda"
    assert normalize_usage_tag_value("mystery") is None
