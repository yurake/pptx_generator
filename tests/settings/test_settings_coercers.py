from __future__ import annotations

from pptx_generator.settings.coercers import (
    coerce_args,
    coerce_bool,
    coerce_float,
    coerce_hex,
    coerce_int,
    coerce_str,
    ensure_hex_prefix,
)


def test_ensure_hex_prefix_normalizes_case() -> None:
    assert ensure_hex_prefix("abc123") == "#ABC123"
    assert ensure_hex_prefix("#fff") == "#FFF"


def test_coerce_float_accepts_numbers_and_strings() -> None:
    assert coerce_float(10) == 10.0
    assert coerce_float("12.5") == 12.5
    assert coerce_float("invalid") is None


def test_coerce_int_accepts_numbers_and_strings() -> None:
    assert coerce_int(10) == 10
    assert coerce_int(3.0) == 3
    assert coerce_int("7") == 7
    assert coerce_int("oops") is None


def test_coerce_hex_returns_normalized_or_none() -> None:
    assert coerce_hex("aabbcc") == "#AABBCC"
    assert coerce_hex("") is None
    assert coerce_hex(123) is None


def test_coerce_bool_defaults_when_not_bool() -> None:
    assert coerce_bool(True, False) is True
    assert coerce_bool("yes", False) is False


def test_coerce_str_returns_stripped_or_none() -> None:
    assert coerce_str("  value  ") == "value"
    assert coerce_str("   ") is None
    assert coerce_str(None) is None


def test_coerce_args_normalizes_sequences() -> None:
    assert coerce_args(["foo", " bar ", "", 1]) == ("foo", "bar")
    assert coerce_args("single") == ("single",)
    assert coerce_args(123) == ()
