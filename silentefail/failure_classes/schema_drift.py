"""Class 1 — Schema Drift: pipeline silent failures on malformed inputs."""
from __future__ import annotations

from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError

from silentefail.models import FailureResult
from silentefail.utils.logger import get_logger

logger = get_logger("schema_drift")

_SENTINEL = object()


class SchemaDriftDetector:
    def __init__(self, schema: Type[BaseModel], pipeline: Callable):
        self.schema = schema
        self.pipeline = pipeline

    # ------------------------------------------------------------------
    # Adversarial input generation
    # ------------------------------------------------------------------

    def generate_adversarial_inputs(self) -> list[tuple[dict, str]]:
        """Return (input_dict, variant_description) pairs."""
        fields = self.schema.model_fields
        valid_base = _build_valid_base(fields)
        variants: list[tuple[dict, str]] = []

        # Missing each required field
        for fname, finfo in fields.items():
            if finfo.is_required():
                v = {k: val for k, val in valid_base.items() if k != fname}
                variants.append((v, f"missing_required_field:{fname}"))

        # None for every field
        for fname in fields:
            v = {**valid_base, fname: None}
            variants.append((v, f"none_value:{fname}"))

        # Empty string for string fields
        for fname, finfo in fields.items():
            ann = finfo.annotation
            if ann is str or (hasattr(ann, "__origin__") is False and ann is not None and
                               str(ann) in ("str", "<class 'str'>")):
                v = {**valid_base, fname: ""}
                variants.append((v, f"empty_string:{fname}"))

        # Wrong type — swap str<->int
        for fname, finfo in fields.items():
            ann = finfo.annotation
            wrong: Any = _wrong_type_value(ann)
            if wrong is not _SENTINEL:
                v = {**valid_base, fname: wrong}
                variants.append((v, f"wrong_type:{fname}"))

        # Extra unexpected field
        v = {**valid_base, "__unexpected_key__": "injected"}
        variants.append((v, "extra_unexpected_field"))

        # Deeply nested malformed (wrap entire dict in a list)
        variants.append(([valid_base], "nested_list_instead_of_dict"))

        # Completely empty dict
        variants.append(({}, "empty_dict"))

        return variants

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> list[FailureResult]:
        results: list[FailureResult] = []
        for adversarial_input, variant_desc in self.generate_adversarial_inputs():
            try:
                output = self.pipeline(adversarial_input)
                if _is_empty_output(output):
                    results.append(FailureResult(
                        failure_class="SCHEMA_DRIFT",
                        failure_type="SILENT_NONE_RETURN",
                        severity="HIGH",
                        input=adversarial_input,
                        output=output,
                        description=(
                            f"Pipeline returned empty/None output for variant '{variant_desc}' "
                            "instead of raising a validation error."
                        ),
                        recommendation=(
                            "Validate inputs at the pipeline entry point using Pydantic. "
                            "Raise a clear ValidationError rather than returning None."
                        ),
                    ))
            except ValidationError:
                # This is the CORRECT behaviour — pipeline rejected bad input clearly.
                logger.debug("ValidationError on %s (expected)", variant_desc)
            except ValueError:
                logger.debug("ValueError on %s (acceptable)", variant_desc)
            except Exception as exc:
                results.append(FailureResult(
                    failure_class="SCHEMA_DRIFT",
                    failure_type="UNHANDLED_EXCEPTION",
                    severity="HIGH",
                    input=adversarial_input,
                    output=None,
                    description=(
                        f"Pipeline raised unhandled {type(exc).__name__} for variant "
                        f"'{variant_desc}': {exc}"
                    ),
                    recommendation=(
                        "Wrap pipeline entry points in try/except and convert unexpected "
                        "exceptions into clear ValidationError or a domain-specific error."
                    ),
                    error=str(exc),
                ))
        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_valid_base(fields: dict) -> dict:
    """Construct a minimal valid dict from field metadata."""
    base: dict = {}
    for fname, finfo in fields.items():
        ann = finfo.annotation
        if finfo.default is not finfo.__class__.__mro__[-1]:
            try:
                base[fname] = finfo.get_default(call_default_factory=True)
                continue
            except Exception:
                pass
        base[fname] = _example_value(ann)
    return base


def _example_value(annotation: Any) -> Any:
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        return []
    if origin is dict:
        return {}
    mapping = {
        str: "example",
        int: 1,
        float: 1.0,
        bool: True,
    }
    return mapping.get(annotation, "example")


def _wrong_type_value(annotation: Any) -> Any:
    if annotation is str:
        return 42
    if annotation is int:
        return "not_an_int"
    if annotation is float:
        return "not_a_float"
    if annotation is bool:
        return "not_a_bool"
    return _SENTINEL


def _is_empty_output(output: Any) -> bool:
    if output is None:
        return True
    if isinstance(output, dict) and len(output) == 0:
        return True
    if isinstance(output, list) and len(output) == 0:
        return True
    return False
