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


def _schema_example(shape):
    if shape is str:
        return ""
    if shape is bool:
        return False
    if shape is int:
        return 0
    if isinstance(shape, list):
        return [_schema_example(shape[0])] if shape else []
    if isinstance(shape, dict):
        return {key: _schema_example(value) for key, value in shape.items()}
    return None


def invoke_with_json_repair(llm, prompt, agent_name, response_schema, invoke):
    """Invoke once, then make one constrained repair call for malformed output."""
    reply = invoke(llm, prompt, agent_name)
    text = getattr(reply, "text", None)
    result = parse_json_response(text, response_schema)
    if result is not None or not isinstance(text, str) or not text.strip():
        return result

    repair_prompt = (
        "Repair the previous model response into valid JSON matching this schema. "
        "This is a formatting and extraction task, not a new analysis. Preserve "
        "supported content from the original request and response. Do not invent "
        "facts or add unsupported claims. If a required string cannot be filled "
        "from the supplied context, use an empty string; if a list has no "
        "supported items, use an empty list. Return only JSON.\n\n"
        "Required JSON shape:\n"
        + json.dumps(_schema_example(response_schema), ensure_ascii=True)
        + "\n\nOriginal request and evidence:\n"
        + prompt[:24000]
        + "\n\nUnusable response to repair:\n"
        + text[:12000]
    )
    print("{}: response did not match its JSON contract; requesting one repair".format(agent_name))
    repaired = invoke(llm, repair_prompt, agent_name + " JSON repair")
    return parse_json_response(getattr(repaired, "text", None), response_schema)
