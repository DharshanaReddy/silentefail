import pytest
from pydantic import BaseModel

from silentefail.failure_classes.schema_drift import SchemaDriftDetector
from tests.fixtures.sample_chains import none_on_missing_field
from tests.fixtures.sample_schemas import SimpleInput


class RequiredFields(BaseModel):
    name: str
    value: float


def test_detects_silent_none_on_missing_field():
    detector = SchemaDriftDetector(RequiredFields, none_on_missing_field)
    results = detector.run()
    types = [r.failure_type for r in results]
    assert "SILENT_NONE_RETURN" in types


def test_generates_adversarial_variants():
    detector = SchemaDriftDetector(RequiredFields, none_on_missing_field)
    variants = detector.generate_adversarial_inputs()
    descriptions = [desc for _, desc in variants]
    assert any("missing_required_field" in d for d in descriptions)
    assert any("none_value" in d for d in descriptions)
    assert any("wrong_type" in d for d in descriptions)
    assert any("extra_unexpected_field" in d for d in descriptions)


def test_no_failure_on_validating_pipeline():
    from pydantic import ValidationError

    def strict_pipeline(data: dict) -> dict:
        RequiredFields(**data)  # raises ValidationError on bad input
        return {"ok": True}

    detector = SchemaDriftDetector(RequiredFields, strict_pipeline)
    results = detector.run()
    # ValidationError is accepted behaviour, should produce no failures
    assert all(r.failure_type != "SILENT_NONE_RETURN" for r in results)


def test_unhandled_exception_flagged():
    def crashing_pipeline(data: dict) -> dict:
        raise RuntimeError("boom")

    detector = SchemaDriftDetector(RequiredFields, crashing_pipeline)
    results = detector.run()
    assert any(r.failure_type == "UNHANDLED_EXCEPTION" for r in results)


def test_all_results_have_required_fields():
    detector = SchemaDriftDetector(SimpleInput, none_on_missing_field)
    results = detector.run()
    for r in results:
        assert r.failure_class == "SCHEMA_DRIFT"
        assert r.severity in ("HIGH", "MEDIUM", "LOW")
        assert r.description
        assert r.recommendation
