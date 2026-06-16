import pytest
from pydantic import BaseModel

from silentefail.failure_classes.hallucinated_structure import HallucinatedStructureDetector
from tests.fixtures.sample_chains import (
    schema_compliant_pipeline,
    invented_key_pipeline,
    missing_key_pipeline,
)
from tests.fixtures.sample_schemas import ExtractedData

INPUTS = [{"text": "Revenue was $1.2M", "context": "Q3"}]


def test_no_failure_on_compliant_output():
    detector = HallucinatedStructureDetector(schema_compliant_pipeline, ExtractedData, INPUTS)
    results = detector.run()
    assert len(results) == 0


def test_detects_invented_keys():
    detector = HallucinatedStructureDetector(invented_key_pipeline, ExtractedData, INPUTS)
    results = detector.run()
    types = [r.failure_type for r in results]
    assert "INVENTED_KEYS" in types


def test_detects_missing_required_keys():
    detector = HallucinatedStructureDetector(missing_key_pipeline, ExtractedData, INPUTS)
    results = detector.run()
    types = [r.failure_type for r in results]
    assert "MISSING_REQUIRED_KEYS" in types


def test_detects_type_mismatch():
    def wrong_types(_) -> dict:
        return {"name": 123, "value": "not_a_float", "category": True}

    detector = HallucinatedStructureDetector(wrong_types, ExtractedData, INPUTS)
    results = detector.run()
    types = [r.failure_type for r in results]
    assert "TYPE_MISMATCH" in types


def test_non_dict_output_flagged():
    def returns_string(_) -> str:
        return "hello"

    detector = HallucinatedStructureDetector(returns_string, ExtractedData, INPUTS)
    results = detector.run()
    assert any(r.failure_type == "NON_DICT_OUTPUT" for r in results)


def test_json_string_output_parsed():
    import json

    def json_string_pipeline(_) -> str:
        return json.dumps({"name": "Alice", "value": 1.5, "category": "test"})

    detector = HallucinatedStructureDetector(json_string_pipeline, ExtractedData, INPUTS)
    results = detector.run()
    assert len(results) == 0


def test_all_results_have_required_fields():
    detector = HallucinatedStructureDetector(invented_key_pipeline, ExtractedData, INPUTS)
    results = detector.run()
    for r in results:
        assert r.failure_class == "HALLUCINATED_STRUCTURE"
        assert r.severity in ("HIGH", "MEDIUM", "LOW")
        assert r.description
        assert r.recommendation
