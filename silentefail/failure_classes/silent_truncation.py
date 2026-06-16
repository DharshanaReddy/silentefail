"""Class 3 — Silent Truncation: output degrades silently near context window limits."""
from __future__ import annotations

import re
from typing import Callable

from silentefail.models import FailureResult
from silentefail.utils.logger import get_logger

logger = get_logger("silent_truncation")

FILL_PERCENTAGES = [0.50, 0.75, 0.90, 0.95, 0.99]

# Patterns that suggest mid-sentence cut-off
_TRUNCATION_ENDINGS = re.compile(
    r"(\w,\s*$|\w\s*$|[a-z]\.$|…$|\.\.\.$)",
    re.MULTILINE,
)


class SilentTruncationDetector:
    def __init__(self, pipeline: Callable, context_window: int, model_name: str | None = None):
        self.pipeline = pipeline
        self.context_window = context_window
        self.model_name = model_name

    def generate_sized_inputs(self, base_input: str = "") -> list[tuple[str, float]]:
        """Return (padded_input, fill_pct) tuples at each fill level."""
        # Rough token→char ratio: 1 token ≈ 4 chars
        char_limit = self.context_window * 4
        filler_word = "data "  # 5 chars, neutral padding

        results = []
        for pct in FILL_PERCENTAGES:
            target_chars = int(char_limit * pct)
            if base_input:
                pad_chars = max(0, target_chars - len(base_input))
                padded = base_input + " " + filler_word * (pad_chars // len(filler_word))
            else:
                padded = filler_word * (target_chars // len(filler_word))
            results.append((padded, pct))
        return results

    def run(self, base_input: str = "Summarise the following text: ") -> list[FailureResult]:
        sized = self.generate_sized_inputs(base_input)
        outputs: list[tuple[str, float, str | None]] = []  # (input, pct, output_text)

        for inp, pct in sized:
            try:
                raw = self.pipeline(inp)
                text = _to_text(raw)
                outputs.append((inp, pct, text))
            except Exception as exc:
                outputs.append((inp, pct, None))
                logger.warning("Pipeline raised %s at %.0f%% fill: %s", type(exc).__name__, pct * 100, exc)

        return self._analyse(outputs)

    def _analyse(self, outputs: list[tuple[str, float, str | None]]) -> list[FailureResult]:
        results: list[FailureResult] = []

        valid = [(inp, pct, out) for inp, pct, out in outputs if out is not None]
        if len(valid) < 2:
            return results

        # Baseline: output length at 50% fill
        baseline_inp, _, baseline_out = valid[0]
        baseline_len = len(baseline_out)

        for inp, pct, out in valid[1:]:
            if pct < 0.89:
                continue  # Only flag high-fill levels

            out_len = len(out)
            # If output at ≥90% is less than half the baseline, flag it
            if baseline_len > 0 and out_len < baseline_len * 0.5:
                results.append(FailureResult(
                    failure_class="SILENT_TRUNCATION",
                    failure_type="OUTPUT_LENGTH_DROP",
                    severity="HIGH" if pct >= 0.95 else "MEDIUM",
                    input=inp[:200] + "…",
                    output=out[:200] + ("…" if len(out) > 200 else ""),
                    description=(
                        f"At {pct:.0%} context fill, output length dropped to {out_len} chars "
                        f"vs {baseline_len} chars at 50% fill — a {100*(1-out_len/baseline_len):.0f}% reduction."
                    ),
                    recommendation=(
                        "Add explicit output length instructions. Consider chunking large inputs. "
                        "Check if your LLM provider silently truncates prompts over the context limit."
                    ),
                ))

            # Mid-sentence ending
            if out and _looks_truncated(out):
                results.append(FailureResult(
                    failure_class="SILENT_TRUNCATION",
                    failure_type="MID_SENTENCE_CUTOFF",
                    severity="HIGH",
                    input=inp[:200] + "…",
                    output=out[-300:],
                    description=(
                        f"Output at {pct:.0%} context fill ends abruptly, suggesting truncation: "
                        f"'…{out[-80:]}'"
                    ),
                    recommendation=(
                        "Reduce input size or increase max_tokens. Add 'end your response with [END]' "
                        "to detect truncation programmatically."
                    ),
                ))

        return results


def _to_text(output: object) -> str:
    if isinstance(output, str):
        return output
    if hasattr(output, "content"):
        return str(output.content)
    if isinstance(output, dict):
        for k in ("text", "answer", "output", "result", "content"):
            if k in output:
                return str(output[k])
    return str(output)


def _looks_truncated(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    last_char = stripped[-1]
    # Ends without sentence-terminating punctuation
    return last_char not in ".!?\"'`)]}"
