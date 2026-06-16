"""Fake pipelines used across tests — no real LLM calls."""
from typing import Any


def echo_pipeline(input_data: Any) -> dict:
    """Returns the input as-is (wrapped in a dict)."""
    if not isinstance(input_data, dict):
        raise ValueError("Expected dict input")
    return input_data


def none_on_missing_field(input_data: dict) -> dict | None:
    """Silently returns None when 'name' field is missing."""
    if "name" not in input_data:
        return None
    return {"result": input_data["name"]}


def always_confident_wrong(question: str) -> str:
    """Always returns 'Paris' regardless of the question — confident but wrong."""
    return "The answer is definitely Paris."


def hedging_pipeline(question: str) -> str:
    return "I'm not sure, but I think it might be around 42."


def truncating_pipeline(input_text: str) -> str:
    """Returns only the first 100 chars of input, simulating truncation."""
    return input_text[:100]


def schema_compliant_pipeline(input_data: Any) -> dict:
    return {"name": "Alice", "value": 1.5, "category": "test"}


def invented_key_pipeline(input_data: Any) -> dict:
    return {"name": "Alice", "value": 1.5, "category": "test", "confidence_score": 0.99}


def missing_key_pipeline(input_data: Any) -> dict:
    return {"name": "Alice"}
