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
        # Compatible gateways frequently prepend a short explanation despite
        # the JSON-only instruction. Recover only a complete object; validation
        # still happens on the resulting DSL afterwards.
        decoder = json.JSONDecoder()
        value = None
        for match in re.finditer(r"\{", text):
            try:
                candidate, end = decoder.raw_decode(text[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and text[match.start() + end :].strip().strip("`").strip() == "":
                value = candidate
                break
        if value is None:
            raise RuntimeError("model_output_invalid_json") from error
    if not isinstance(value, dict):
        raise RuntimeError("model_output_not_object")
    return value
