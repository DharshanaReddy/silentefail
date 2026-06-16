"""Class 2 — Confident Wrong Answers: pipeline answers incorrectly without hedging."""
from __future__ import annotations

from typing import Callable

from silentefail.models import FailureResult, GoldenSample
from silentefail.utils.logger import get_logger

logger = get_logger("confident_wrong")

UNCERTAINTY_SIGNALS = [
    "i think",
    "i believe",
    "i'm not sure",
    "i am not sure",
    "approximately",
    "may ",
    "might ",
    "could be",
    "possibly",
    "uncertain",
    "i don't know",
    "i do not know",
    "unclear",
    "not certain",
    "not sure",
    "probably",
    "perhaps",
    "roughly",
    "around ",
]


class ConfidentWrongDetector:
    def __init__(self, pipeline: Callable, golden_dataset: list):
        self.pipeline = pipeline
        self.golden_dataset = [
            GoldenSample.from_tuple(s) if isinstance(s, tuple) else s
            for s in golden_dataset
        ]

    def run(self) -> list[FailureResult]:
        results: list[FailureResult] = []
        for sample in self.golden_dataset:
            try:
                raw_output = self.pipeline(sample.question)
            except Exception as exc:
                results.append(FailureResult(
                    failure_class="CONFIDENT_WRONG",
                    failure_type="PIPELINE_EXCEPTION",
                    severity="HIGH",
                    input=sample.question,
                    output=None,
                    description=f"Pipeline raised {type(exc).__name__} on golden sample: {exc}",
                    recommendation="Golden dataset inputs should never crash the pipeline.",
                    error=str(exc),
                ))
                continue

            response = _extract_text(raw_output)

            has_content = self.contains_expected_content(response, sample.expected_keywords)
            confident = self.is_confident(response)

            if not has_content and confident:
                results.append(FailureResult(
                    failure_class="CONFIDENT_WRONG",
                    failure_type="CONFIDENTLY_WRONG",
                    severity="HIGH",
                    input=sample.question,
                    output=response,
                    description=(
                        f"Pipeline answered confidently but missed all expected keywords "
                        f"{sample.expected_keywords!r}. Expected answer: '{sample.expected_answer}'."
                    ),
                    recommendation=(
                        "Add calibration to the prompt — instruct the model to express uncertainty "
                        "when it cannot verify the answer. Consider retrieval-augmented generation."
                    ),
                ))
            elif not has_content and not confident:
                results.append(FailureResult(
                    failure_class="CONFIDENT_WRONG",
                    failure_type="WRONG_WITH_HEDGING",
                    severity="MEDIUM",
                    input=sample.question,
                    output=response,
                    description=(
                        f"Pipeline answered incorrectly (missing keywords {sample.expected_keywords!r}) "
                        "but did hedge — calibration is working, factual accuracy needs improvement."
                    ),
                    recommendation=(
                        "Improve retrieval context or fine-tune on domain knowledge. "
                        "The uncertainty signalling is correct."
                    ),
                ))

        return results

    def is_confident(self, response: str) -> bool:
        lower = response.lower()
        return not any(signal in lower for signal in UNCERTAINTY_SIGNALS)

    def contains_expected_content(self, response: str, expected_keywords: list[str]) -> bool:
        lower = response.lower()
        return any(kw.lower() in lower for kw in expected_keywords)


def _extract_text(output: object) -> str:
    """Pull a plain string out of whatever the pipeline returned."""
    if isinstance(output, str):
        return output
    # LangChain AIMessage
    if hasattr(output, "content"):
        return str(output.content)
    # Dict with 'text' or 'answer' key
    if isinstance(output, dict):
        for key in ("text", "answer", "output", "result", "content"):
            if key in output:
                return str(output[key])
    return str(output)
