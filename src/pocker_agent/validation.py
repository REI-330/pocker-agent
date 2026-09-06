from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .models import GameRuleDSL


def validate_dsl(payload: dict[str, Any]) -> tuple[GameRuleDSL | None, list[str]]:
    try:
        return GameRuleDSL.model_validate(payload), []
    except ValidationError as error:
        return None, [f"{'.'.join(str(item) for item in issue['loc'])}: {issue['msg']}" for issue in error.errors()]
