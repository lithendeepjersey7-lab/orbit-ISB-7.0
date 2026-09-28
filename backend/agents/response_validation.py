import json
import re


def _matches_schema(value, schema):
    if schema is str:
        return isinstance(value, str) and bool(value.strip())
    if schema is bool:
        return type(value) is bool
    if isinstance(schema, dict):
        return isinstance(value, dict) and all(
            key in value and _matches_schema(value[key], field_schema)
            for key, field_schema in schema.items()
        )
    if isinstance(schema, list):
        if not isinstance(value, list):
            return False
        return not schema or all(_matches_schema(item, schema[0]) for item in value)
    return isinstance(value, schema)


def parse_json_response(text, schema):
    """Parse JSON and reject replies that do not match the required structure."""
    if not isinstance(text, str):
        return None

    text = text.strip()
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
        if match is None:
            return None
        text = match.group(1).strip()

    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return result if _matches_schema(result, schema) else None