from pptx_generator.utils.layout_metadata import (
    _compose_element_description,
    _compose_overview_text,
    _extract_flags,
    _feature_labels_from_counts,
    _normalize_size_keyword,
    _rounded_area_ratio,
    derive_usage_tags,
    generate_layout_description,
)


def test_derive_usage_tags_detects_basic_placeholder_types() -> None:
    placeholders = [
        {"type": "title", "name": "Main Title"},
        {"type": "body", "name": "Content Area"},
        {"type": "chart", "name": "Chart Zone"},
        {"type": "table", "name": "Table Zone"},
        {"type": "image", "name": "Hero Visual"},
    ]

    result = derive_usage_tags("Generic Layout", placeholders)

    assert result.has_title_placeholder is True
    assert result.has_body_placeholder is True
    assert result.title_from_name is False
    assert result.tags == {"title", "content", "chart", "table", "visual"}
    assert result.reasons == [
        "placeholder:type=chart",
        "placeholder:type=body",
        "placeholder:type=table",
        "placeholder:type=title",
        "placeholder:type=image",
    ]


def test_derive_usage_tags_handles_object_and_media_placeholders() -> None:
    placeholders = [
        {"type": "object", "name": "Logo Holder"},
        {"type": "media", "name": "KPI Graph"},
        {"type": "unknown", "name": "Table Section"},
    ]

    result = derive_usage_tags("Quarterly Overview", placeholders)

    assert result.tags == {"visual", "chart", "table", "overview"}
    assert result.reasons == [
        "placeholder:type=media(chart)",
        "name:contains=overview",
        "placeholder:name~table",
        "placeholder:type=object(visual)",
    ]


def test_derive_usage_tags_applies_title_name_pattern() -> None:
    result = derive_usage_tags("セクション表紙", [])

    assert result.tags == {"title"}
    assert result.title_from_name is True
    assert result.has_title_placeholder is False
    assert result.reasons == ["name:pattern=title"]


def test_generate_layout_description_builds_overview_and_elements() -> None:
    placeholders = [
        {
            "type": "title",
            "name": "MainTitle",
            "bbox": {"x": 0, "y": 0, "width": 4000000, "height": 800000},
        },
        {
            "type": "body",
            "name": "BodyArea",
            "bbox": {"x": 0, "y": 900000, "width": 7000000, "height": 4000000},
        },
        {
            "type": "table",
            "name": "DataTable",
            "bbox": {"x": 2000000, "y": 1200000, "width": 3000000, "height": 2000000},
        },
    ]

    description = generate_layout_description("Sales Summary", placeholders, (9144000, 6858000))

    assert description["overview"] == "Sales Summary レイアウトは タイトル、本文、表 を配置できる 3 個のプレースホルダー構成です。"
    assert len(description["elements"]) == 3
    head = description["elements"][0]
    assert head["role"] in {"本文枠", "タイトル枠"}
    assert head["description"].startswith(("中央に", "上部中央に"))


def test_generate_layout_description_limits_elements_to_twenty() -> None:
    placeholders = [
        {
            "type": "body",
            "name": f"Body{i}",
            "bbox": {"x": i * 10000, "y": 0, "width": 10000, "height": 10000},
        }
        for i in range(30)
    ]

    description = generate_layout_description("Many Items", placeholders, (9144000, 6858000))

    assert len(description["elements"]) == 20


def test_feature_labels_and_overview_helpers_cover_all_categories() -> None:
    counts = {
        "title": 1,
        "subtitle": 1,
        "body": 2,
        "table": 1,
        "chart": 1,
        "image": 1,
        "media": 1,
        "object": 1,
        "footer": 1,
        "notes": 1,
    }

    labels = _feature_labels_from_counts(counts)
    assert labels == ["タイトル", "本文", "表", "チャート", "ビジュアル", "フッター", "ノート"]
    overview = _compose_overview_text("Layout", 3, labels)
    assert overview.startswith("Layout レイアウトは タイトル、本文、表、チャート、ビジュアル、フッター、ノート")
    assert _compose_overview_text("Layout", 3, []) == "Layout レイアウトは 3 個のプレースホルダーを備えています。"


def test_element_description_and_helpers_variations() -> None:
    description = _compose_element_description(
        position_label="中央",
        size_label="大きめの",
        role_label="本文枠",
        name="Body Main",
        expects_text=False,
    )
    assert "Body Main" in description
    assert "テキスト入力非想定" in description

    assert _normalize_size_keyword("大きめの") == "大きめ"
    assert _normalize_size_keyword(None) is None
    assert _rounded_area_ratio(0.1234) == 0.123
    assert _rounded_area_ratio(None) is None


def test_extract_flags_discards_non_list_and_none_entries() -> None:
    assert _extract_flags(["A", None, "B"]) == ["A", "B"]
    assert _extract_flags("not-a-list") == []
