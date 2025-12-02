"""Setting value coercion helpers."""

from __future__ import annotations

__all__ = [
    "ensure_hex_prefix",
    "coerce_float",
    "coerce_int",
    "coerce_hex",
    "coerce_bool",
    "coerce_str",
    "coerce_args",
]


def ensure_hex_prefix(value: str) -> str:
    """Ensure the given hex string is prefixed with '#', returning upper-case."""

    normalized = value if value.startswith("#") else f"#{value}"
    return normalized.upper()


def coerce_float(value: object) -> float | None:
    """Convert a value to float if possible."""

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def coerce_int(value: object) -> int | None:
    """Convert a value to int if possible."""

    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def coerce_hex(value: object) -> str | None:
    """Return a normalized hex value or None."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return ensure_hex_prefix(stripped)


def coerce_bool(value: object, default: bool) -> bool:
    """Return a boolean when the input is explicitly boolean, otherwise default."""

    if isinstance(value, bool):
        return value
    return default


def coerce_str(value: object) -> str | None:
    """Return the stripped string value or None."""

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def coerce_args(value: object) -> tuple[str, ...]:
    """Normalize CLI-style arguments to a tuple of strings."""

    if isinstance(value, (list, tuple)):
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
        return tuple(normalized)
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()
