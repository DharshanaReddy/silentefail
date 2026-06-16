import pytest

from silentefail.failure_classes.silent_truncation import SilentTruncationDetector, FILL_PERCENTAGES


def test_generates_correct_number_of_sizes():
    detector = SilentTruncationDetector(lambda x: x, context_window=1000)
    sized = detector.generate_sized_inputs("hello ")
    assert len(sized) == len(FILL_PERCENTAGES)


def test_detects_output_length_drop():
    call_count = [0]

    def shrinking(text: str) -> str:
        # First call (50% fill) → big output; subsequent calls → tiny output
        call_count[0] += 1
        if call_count[0] == 1:
            return "x" * 500
        return "x" * 10  # drastically shorter at higher fill levels

    detector = SilentTruncationDetector(shrinking, context_window=500)
    results = detector.run(base_input="Summarise: ")
    types = [r.failure_type for r in results]
    assert "OUTPUT_LENGTH_DROP" in types


def test_no_failure_proportional_output():
    def proportional(text: str) -> str:
        # Returns 10% of input length — consistently proportional
        return "x" * max(1, len(text) // 10)

    detector = SilentTruncationDetector(proportional, context_window=500)
    results = detector.run()
    # No OUTPUT_LENGTH_DROP because the ratio is consistent
    assert not any(r.failure_type == "OUTPUT_LENGTH_DROP" for r in results)


def test_detects_mid_sentence_cutoff():
    call_count = [0]

    def sometimes_cutoff(text: str) -> str:
        call_count[0] += 1
        if call_count[0] >= 4:  # High fill levels
            return "The quick brown fox jumps"  # no terminal punctuation
        return "The quick brown fox jumps over the lazy dog."

    detector = SilentTruncationDetector(sometimes_cutoff, context_window=200)
    results = detector.run()
    assert any(r.failure_type == "MID_SENTENCE_CUTOFF" for r in results)


def test_all_results_have_required_fields():
    detector = SilentTruncationDetector(lambda x: "x" * 10, context_window=100)
    results = detector.run()
    for r in results:
        assert r.failure_class == "SILENT_TRUNCATION"
        assert r.severity in ("HIGH", "MEDIUM", "LOW")
