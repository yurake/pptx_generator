"""レイアウト検証スイートで使用する JSON スキーマ。"""

from __future__ import annotations

from jsonschema import Draft202012Validator


LAYOUT_RECORD_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": [
        "template_id",
        "layout_id",
        "layout_name",
        "placeholders",
        "usage_tags",
        "text_hint",
        "media_hint",
        "version",
    ],
    "properties": {
        "template_id": {"type": "string", "minLength": 1},
        "layout_id": {"type": "string", "minLength": 1},
        "layout_name": {"type": "string", "minLength": 1},
        "placeholders": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type", "bbox"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1},
                    "bbox": {
                        "type": "object",
                        "required": ["x", "y", "width", "height"],
                        "properties": {
                            "x": {"type": "integer", "minimum": 0},
                            "y": {"type": "integer", "minimum": 0},
                            "width": {"type": "integer", "minimum": 0},
                            "height": {"type": "integer", "minimum": 0},
                        },
                        "additionalProperties": False,
                    },
                    "style_hint": {
                        "type": "object",
                        "properties": {
                            "font": {"type": "string"},
                            "alignment": {"type": "string"},
                            "line_spacing": {"type": "number", "minimum": 0},
                        },
                        "additionalProperties": True,
                    },
                    "flags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
        },
        "usage_tags": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "text_hint": {
            "type": "object",
            "required": ["max_chars", "max_lines"],
            "properties": {
                "max_chars": {"type": "integer", "minimum": 0},
                "max_lines": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "media_hint": {
            "type": "object",
            "required": ["allow_table", "allow_chart", "allow_image"],
            "properties": {
                "allow_table": {"type": "boolean"},
                "allow_chart": {"type": "boolean"},
                "allow_image": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "version": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}


DIAGNOSTICS_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["template_id", "warnings", "errors", "stats"],
    "properties": {
        "template_id": {"type": "string", "minLength": 1},
        "warnings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "layout_id", "name"],
                "properties": {
                    "code": {"type": "string", "minLength": 1},
                    "layout_id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "detail": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "layout_id", "name"],
                "properties": {
                    "code": {"type": "string", "minLength": 1},
                    "layout_id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "detail": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "stats": {
            "type": "object",
            "required": [
                "layouts_total",
                "placeholders_total",
                "extraction_time_ms",
            ],
            "properties": {
                "layouts_total": {"type": "integer", "minimum": 0},
                "placeholders_total": {"type": "integer", "minimum": 0},
                "extraction_time_ms": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


DIFF_REPORT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": [
        "baseline_template_id",
        "target_template_id",
        "layouts_added",
        "layouts_removed",
        "placeholders_changed",
        "issues",
    ],
    "properties": {
        "baseline_template_id": {"type": "string"},
        "target_template_id": {"type": "string"},
        "layouts_added": {
            "type": "array",
            "items": {"type": "string"},
        },
        "layouts_removed": {
            "type": "array",
            "items": {"type": "string"},
        },
        "placeholders_changed": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["layout_id", "name", "field"],
                "properties": {
                    "layout_id": {"type": "string"},
                    "name": {"type": "string"},
                    "field": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "layout_id"],
                "properties": {
                    "code": {"type": "string"},
                    "layout_id": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
    },
    "additionalProperties": False,
}


LAYOUT_RECORD_VALIDATOR = Draft202012Validator(LAYOUT_RECORD_SCHEMA)
DIAGNOSTICS_VALIDATOR = Draft202012Validator(DIAGNOSTICS_SCHEMA)
DIFF_REPORT_VALIDATOR = Draft202012Validator(DIFF_REPORT_SCHEMA)
