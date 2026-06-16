"""Class 4 — Hallucinated Structure: model invents or drops output schema keys."""
from __future__ import annotations

import json
from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError

from silentefail.models import FailureResult
from silentefail.utils.logger import get_logger

logger = get_logger("hallucinated_structure")


class HallucinatedStructureDetector:
    def __init__(
        self,
        pipeline: Callable,
        output_schema: Type[BaseModel],
        test_inputs: list[Any],
    ):
        self.pipeline = pipeline
        self.output_schema = output_schema
        self.test_inputs = test_inputs

    def run(self) -> list[FailureResult]:
        results: list[FailureResult] = []
        schema_fields = set(self.output_schema.model_fields.keys())
        required_fields = {
            k for k, v in self.output_schema.model_fields.items() if v.is_required()
        }

        for inp in self.test_inputs:
            try:
                raw_output = self.pipeline(inp)
            except Exception as exc:
                results.append(FailureResult(
                    failure_class="HALLUCINATED_STRUCTURE",
                    failure_type="PIPELINE_EXCEPTION",
                    severity="HIGH",
                    input=inp,
                    output=None,
                    description=f"Pipeline raised {type(exc).__name__} on test input: {exc}",
                    recommendation="Ensure pipeline handles all provided test inputs.",
                    error=str(exc),
                ))
                continue

            output_dict = _to_dict(raw_output)

            if output_dict is None:
                results.append(FailureResult(
                    failure_class="HALLUCINATED_STRUCTURE",
                    failure_type="NON_DICT_OUTPUT",
                    severity="HIGH",
                    input=inp,
                    output=raw_output,
                    description=(
                        f"Pipeline returned {type(raw_output).__name__} instead of a dict/object. "
                        "Cannot validate against output schema."
                    ),
                    recommendation=(
                        "Ensure the pipeline always returns a dict or a Pydantic model "
                        "matching the declared output schema."
                    ),
                ))
                continue

            output_keys = set(output_dict.keys())

            invented = output_keys - schema_fields
            missing = required_fields - output_keys

            if invented:
                results.append(FailureResult(
                    failure_class="HALLUCINATED_STRUCTURE",
                    failure_type="INVENTED_KEYS",
                    severity="MEDIUM",
                    input=inp,
                    output=output_dict,
                    description=(
                        f"Pipeline output contains keys not in schema: {sorted(invented)}. "
                        f"Schema fields: {sorted(schema_fields)}."
                    ),
                    recommendation=(
                        "Tighten your prompt to restrict the model to schema fields only. "
                        "Use Pydantic with `model_config = ConfigDict(extra='forbid')` to catch this at runtime."
                    ),
                ))

            if missing:
                results.append(FailureResult(
                    failure_class="HALLUCINATED_STRUCTURE",
                    failure_type="MISSING_REQUIRED_KEYS",
                    severity="HIGH",
                    input=inp,
                    output=output_dict,
                    description=(
                        f"Pipeline output is missing required schema keys: {sorted(missing)}."
                    ),
                    recommendation=(
                        "Add explicit field instructions to the prompt. "
                        "Consider using structured output / function calling to enforce the schema."
                    ),
                ))

            # Pydantic type validation
            try:
                self.output_schema(**output_dict)
            except ValidationError as ve:
                results.append(FailureResult(
                    failure_class="HALLUCINATED_STRUCTURE",
                    failure_type="TYPE_MISMATCH",
                    severity="HIGH",
                    input=inp,
                    output=output_dict,
                    description=(
                        f"Output keys match schema but values fail Pydantic validation: {ve.error_count()} error(s). "
                        f"First error: {ve.errors()[0]['msg']} on field '{ve.errors()[0]['loc']}'."
                    ),
                    recommendation=(
                        "Use structured output mode or coerce types explicitly before returning from the pipeline."
                    ),
                    error=str(ve),
                ))

        return results


def _to_dict(output: Any) -> dict | None:
    if isinstance(output, dict):
        return output
    # Pydantic model
    if hasattr(output, "model_dump"):
        return output.model_dump()
    # JSON string
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return None
