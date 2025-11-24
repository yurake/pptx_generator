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
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer", "minimum": 0},
                            "height": {"type": "integer", "minimum": 0},
                        },
                        "additionalProperties": False,
                    },
                    "shape_type": {"type": "string"},
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
        "placeholder_summary": {
            "type": "object",
            "properties": {
                "counts": {
                    "type": "object",
                    "additionalProperties": {"type": "integer", "minimum": 0},
                },
                "area_ratio": {
                    "type": "object",
                    "additionalProperties": {"type": "number", "minimum": 0.0},
                },
                "details": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "type"],
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "shape_type": {"type": "string"},
                            "flags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "area_ratio": {"type": ["number", "null"]},
                        },
                        "additionalProperties": False,
                    },
                },
                "attributes": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer", "minimum": 0},
                        "has_title": {"type": "boolean"},
                        "has_body": {"type": "boolean"},
                        "has_table": {"type": "boolean"},
                        "has_chart": {"type": "boolean"},
                        "has_visual": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
            },
            "additionalProperties": False,
        },
        "heuristic": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "reasons": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "has_title_placeholder": {"type": "boolean"},
                "has_body_placeholder": {"type": "boolean"},
                "title_from_name": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
        "static_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "layout_name_pattern": {"type": ["string", "null"]},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
        },
        "blueprint": {
            "type": "object",
            "properties": {
                "layout": {"type": "string"},
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "blueprint_slide_id": {"type": "string"},
                            "required": {"type": "boolean"},
                            "intent_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "slots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["slot_id", "anchor"],
                        "properties": {
                            "slot_id": {"type": "string"},
                            "anchor": {"type": "string"},
                            "required": {"type": "boolean"},
                            "content_type": {"type": "string"},
                            "intent_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
        "meta": {
            "type": "object",
            "properties": {
                "heuristic_reason": {"type": "string"},
            },
            "additionalProperties": True,
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
                "template_ai_invoked": {"type": "integer", "minimum": 0},
                "template_ai_success": {"type": "integer", "minimum": 0},
                "template_ai_fallback": {"type": "integer", "minimum": 0},
                "template_ai_failed": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "template_ai": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "layout_id": {"type": ["string", "null"]},
                    "layout_name": {"type": ["string", "null"]},
                    "source": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "unknown_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "error": {"type": ["string", "null"]},
                },
                "additionalProperties": True,
            },
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
