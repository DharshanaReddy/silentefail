import pytest
from pydantic import BaseModel

from silentefail import Auditor, AuditReport, FailureClass
from tests.fixtures.sample_chains import (
    none_on_missing_field,
    invented_key_pipeline,
    always_confident_wrong,
)
from tests.fixtures.sample_schemas import SimpleInput, ExtractedData


def test_auditor_runs_schema_drift():
    auditor = Auditor(pipeline=none_on_missing_field, input_schema=SimpleInput)
    report = auditor.run([FailureClass.SCHEMA_DRIFT])
    assert isinstance(report, AuditReport)
    assert report.total_tests > 0
    assert "SCHEMA_DRIFT" in report.failures_by_class


def test_auditor_runs_hallucinated_structure():
    auditor = Auditor(
        pipeline=invented_key_pipeline,
        output_schema=ExtractedData,
        test_inputs=[{"x": 1}],
    )
    report = auditor.run([FailureClass.HALLUCINATED_STRUCTURE])
    assert report.total_failures > 0


def test_auditor_runs_confident_wrong():
    golden = [("What is 2+2?", "4", ["4", "four"])]
    auditor = Auditor(pipeline=always_confident_wrong, golden_dataset=golden)
    report = auditor.run([FailureClass.CONFIDENT_WRONG])
    assert report.total_tests == 1


def test_auditor_skips_class_without_required_args(capsys):
    auditor = Auditor(pipeline=lambda x: x)
    report = auditor.run([FailureClass.SCHEMA_DRIFT])
    assert report.total_tests == 0


def test_auditor_default_runs_all_classes():
    auditor = Auditor(
        pipeline=none_on_missing_field,
        input_schema=SimpleInput,
    )
    report = auditor.run()
    assert report.total_tests > 0


def test_audit_report_to_dict():
    auditor = Auditor(pipeline=none_on_missing_field, input_schema=SimpleInput)
    report = auditor.run([FailureClass.SCHEMA_DRIFT])
    d = report.to_dict()
    assert "total_tests" in d
    assert "total_failures" in d
    assert "pass_rate" in d
    assert "failures" in d


def test_audit_report_export(tmp_path):
    auditor = Auditor(
        pipeline=invented_key_pipeline,
        output_schema=ExtractedData,
        test_inputs=[{"x": 1}],
    )
    report = auditor.run([FailureClass.HALLUCINATED_STRUCTURE])
    out = tmp_path / "report.html"
    report.export(str(out))
    assert out.exists()
    content = out.read_text()
    assert "SilentFail" in content
    assert "Hallucinated Structure" in content or "HALLUCINATED_STRUCTURE" in content or "INVENTED_KEYS" in content


def test_pass_rate_100_on_no_failures():
    def perfect_pipeline(data: dict) -> dict:
        return {"name": "Alice", "value": 1.5, "category": "test"}

    auditor = Auditor(
        pipeline=perfect_pipeline,
        output_schema=ExtractedData,
        test_inputs=[{"x": 1}],
    )
    report = auditor.run([FailureClass.HALLUCINATED_STRUCTURE])
    assert report.pass_rate == 100.0
    assert report.total_failures == 0
