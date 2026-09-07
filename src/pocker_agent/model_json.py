"""Strict application-side JSON contract independent of gateway JSON-mode support."""

import json
import re


def parse_object(raw):
    if not isinstance(raw, str):
        raise RuntimeError("model_output_not_text")
    text = raw.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
    )
    if fenced:
        text = fenced.group(1)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError("model_output_invalid_json") from error
    if not isinstance(value, dict):
        raise RuntimeError("model_output_not_object")
    return value
