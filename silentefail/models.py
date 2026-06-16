"""Core data models shared across all failure detectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FailureResult:
    failure_class: str          # SCHEMA_DRIFT | CONFIDENT_WRONG | SILENT_TRUNCATION | HALLUCINATED_STRUCTURE
    failure_type: str           # Sub-type within the class
    severity: str               # HIGH | MEDIUM | LOW
    input: Any
    output: Any
    description: str
    recommendation: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "failure_class": self.failure_class,
            "failure_type": self.failure_type,
            "severity": self.severity,
            "input": _serializable(self.input),
            "output": _serializable(self.output),
            "description": self.description,
            "recommendation": self.recommendation,
            "error": self.error,
        }


@dataclass
class GoldenSample:
    question: str
    expected_answer: str
    expected_keywords: list[str]

    @classmethod
    def from_tuple(cls, t: tuple) -> "GoldenSample":
        question, expected_answer, expected_keywords = t
        return cls(question=question, expected_answer=expected_answer,
                   expected_keywords=expected_keywords)


def _serializable(obj: Any) -> Any:
    """Best-effort conversion to a JSON-safe type."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializable(v) for v in obj]
    try:
        # Pydantic models
        return obj.model_dump()
    except AttributeError:
        return str(obj)
