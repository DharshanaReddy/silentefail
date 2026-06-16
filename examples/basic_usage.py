"""Basic SilentFail usage — no LLM required."""
from pydantic import BaseModel
from silentefail import Auditor, FailureClass


class InputData(BaseModel):
    text: str
    context: str


class ExtractedData(BaseModel):
    name: str
    value: float
    category: str


# Simulated pipeline that silently fails on missing fields
def my_pipeline(input_data: dict) -> dict | None:
    if "text" not in input_data:
        return None  # <-- silent failure SilentFail will catch
    return {
        "name": input_data["text"].split()[0],
        "value": 1.0,
        "category": "general",
        "confidence_score": 0.95,  # <-- hallucinated key SilentFail will catch
    }


golden_dataset = [
    ("What is 2+2?", "4", ["4", "four"]),
    ("Capital of France?", "Paris", ["Paris"]),
    ("Who wrote Hamlet?", "Shakespeare", ["Shakespeare", "William"]),
]

auditor = Auditor(
    pipeline=my_pipeline,
    input_schema=InputData,
    output_schema=ExtractedData,
    golden_dataset=golden_dataset,
    context_window=4096,
    test_inputs=[
        {"text": "Revenue was $1.2M", "context": "Q3 report"},
        {"text": "Growth rate: 45%", "context": "Annual summary"},
    ],
)

report = auditor.run([
    FailureClass.SCHEMA_DRIFT,
    FailureClass.HALLUCINATED_STRUCTURE,
])

report.summary()
report.export("silentefail_report.html")
print("\nReport written to silentefail_report.html")
