import pytest

from silentefail.failure_classes.confident_wrong import ConfidentWrongDetector, UNCERTAINTY_SIGNALS
from tests.fixtures.sample_chains import always_confident_wrong, hedging_pipeline

GOLDEN = [
    ("What is 2+2?", "4", ["4", "four"]),
    ("Capital of France?", "Paris", ["Paris"]),
]


def test_detects_confident_wrong():
    detector = ConfidentWrongDetector(always_confident_wrong, GOLDEN)
    results = detector.run()
    types = [r.failure_type for r in results]
    # Question 1 ("2+2") — returns "Paris" with no hedging
    assert "CONFIDENTLY_WRONG" in types


def test_wrong_with_hedging_is_medium():
    detector = ConfidentWrongDetector(hedging_pipeline, GOLDEN)
    results = detector.run()
    medium = [r for r in results if r.severity == "MEDIUM"]
    assert len(medium) > 0


def test_correct_answer_produces_no_failure():
    def correct_pipeline(q: str) -> str:
        answers = {
            "What is 2+2?": "The answer is 4.",
            "Capital of France?": "The capital of France is Paris.",
        }
        return answers.get(q, "I don't know")

    detector = ConfidentWrongDetector(correct_pipeline, GOLDEN)
    results = detector.run()
    assert len(results) == 0


def test_is_confident_no_signals():
    detector = ConfidentWrongDetector(lambda q: q, [])
    assert detector.is_confident("The answer is Paris.") is True


def test_is_not_confident_with_signals():
    detector = ConfidentWrongDetector(lambda q: q, [])
    assert detector.is_confident("I think it might be Paris.") is False


def test_contains_expected_content():
    detector = ConfidentWrongDetector(lambda q: q, [])
    assert detector.contains_expected_content("The answer is 4.", ["4", "four"]) is True
    assert detector.contains_expected_content("The answer is Paris.", ["4", "four"]) is False


def test_pipeline_exception_flagged():
    def crashing(q: str) -> str:
        raise RuntimeError("fail")

    detector = ConfidentWrongDetector(crashing, GOLDEN)
    results = detector.run()
    assert any(r.failure_type == "PIPELINE_EXCEPTION" for r in results)
