from __future__ import annotations

from typing import Any, Type, get_args, get_origin
import types


def check_type(value: Any, annotation: Any) -> bool:
    """Best-effort runtime type check against a type annotation."""
    origin = get_origin(annotation)

    if origin is types.UnionType or origin is getattr(__builtins__, "Union", None):
        return any(check_type(value, arg) for arg in get_args(annotation))

    if annotation is Any:
        return True

    if origin is list:
        if not isinstance(value, list):
            return False
        args = get_args(annotation)
        if args:
            return all(check_type(item, args[0]) for item in value)
        return True

    if origin is dict:
        if not isinstance(value, dict):
            return False
        args = get_args(annotation)
        if len(args) == 2:
            return all(
                check_type(k, args[0]) and check_type(v, args[1])
                for k, v in value.items()
            )
        return True

    if isinstance(annotation, type):
        return isinstance(value, annotation)

    return True  # Unknown annotation — pass through
