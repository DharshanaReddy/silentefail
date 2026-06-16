"""Example: testing a pipeline with a custom nested schema."""
from typing import Optional
from pydantic import BaseModel
from silentefail import Auditor, FailureClass


class Address(BaseModel):
    street: str
    city: str
    country: str


class PersonRecord(BaseModel):
    full_name: str
    age: int
    email: str
    address: Optional[Address] = None


class RawInput(BaseModel):
    document_text: str
    language: str


def extraction_pipeline(input_data: dict) -> dict:
    # Simulated extraction — drops 'age' sometimes
    text = input_data.get("document_text", "")
    return {
        "full_name": "John Doe",
        "email": "john@example.com",
        # 'age' intentionally missing — SilentFail will catch this
        "invented_field": "unexpected",
    }


auditor = Auditor(
    pipeline=extraction_pipeline,
    input_schema=RawInput,
    output_schema=PersonRecord,
    test_inputs=[
        {"document_text": "John Doe, age 30, john@example.com", "language": "en"},
        {"document_text": "Jane Smith, 25, jane@example.com", "language": "en"},
    ],
)

report = auditor.run([FailureClass.SCHEMA_DRIFT, FailureClass.HALLUCINATED_STRUCTURE])
report.summary()
report.export("custom_schema_report.html")
