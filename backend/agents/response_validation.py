"""Strict JSON shape checks shared by the analysis agents."""

import json


def _matches(value, shape):
    if isinstance(shape, type):
        return isinstance(value, shape) and (
            shape is not int or not isinstance(value, bool)
        )
    if isinstance(shape, list):
        return isinstance(value, list) and (
            not shape or all(_matches(item, shape[0]) for item in value)
        )
    if isinstance(shape, dict):
        return isinstance(value, dict) and all(
            key in value and _matches(value[key], expected)
            for key, expected in shape.items()
        )
    return False


def parse_json_response(text, response_schema):
    """Parse JSON (including fenced JSON) and reject malformed or wrong-shaped data."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            return None
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if _matches(value, response_schema) else None
