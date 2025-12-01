from pptx_generator.utils.layout_metadata import derive_usage_tags, generate_layout_description


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
