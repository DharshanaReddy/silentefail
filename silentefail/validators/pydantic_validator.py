from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, ValidationError


def validate_against_schema(data: Any, schema: Type[BaseModel]) -> tuple[bool, list[dict]]:
    """Return (is_valid, errors). errors is empty list when valid."""
    try:
        schema(**data) if isinstance(data, dict) else schema.model_validate(data)
        return True, []
    except ValidationError as e:
        return False, e.errors()
    except Exception as e:
        return False, [{"msg": str(e), "type": "general_error"}]
