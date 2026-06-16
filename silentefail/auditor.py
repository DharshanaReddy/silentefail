"""Main Auditor class — entry point for SilentFail pipeline integrity testing."""
from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Any, Callable, List, Optional, Type

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from rich import box

from silentefail.models import FailureResult
from silentefail.report.generator import export_html

console = Console()


class FailureClass(str, Enum):
    SCHEMA_DRIFT = "schema_drift"
    CONFIDENT_WRONG = "confident_wrong"
    SILENT_TRUNCATION = "silent_truncation"
    HALLUCINATED_STRUCTURE = "hallucinated_structure"


_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_SEVERITY_COLOURS = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}


class AuditReport:
    def __init__(self, results: list[FailureResult], total_tests: int):
        self.results = results
        self.total_tests = total_tests
        self.total_failures = len(results)

        by_class: dict[str, list[FailureResult]] = defaultdict(list)
        for r in results:
            by_class[r.failure_class].append(r)
        self.failures_by_class: dict[str, list[FailureResult]] = dict(by_class)

        sev: dict[str, int] = defaultdict(int)
        for r in results:
            sev[r.severity] += 1
        self.severity_breakdown: dict[str, int] = dict(sev)

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return round(100 * (self.total_tests - self.total_failures) / self.total_tests, 1)

    def summary(self) -> None:
        console.print()
        console.print("[bold cyan]SilentFail Audit Report[/bold cyan]")
        console.print("[dim]" + "=" * 40 + "[/dim]")
        console.print(f"Tests run:         [bold]{self.total_tests}[/bold]")

        fail_colour = "red" if self.total_failures else "green"
        console.print(f"Failures detected: [bold {fail_colour}]{self.total_failures}[/bold {fail_colour}]")

        pr_colour = "green" if self.pass_rate == 100 else ("yellow" if self.pass_rate >= 75 else "red")
        console.print(f"Pass rate:         [bold {pr_colour}]{self.pass_rate}%[/bold {pr_colour}]")
        console.print()

        if not self.results:
            console.print("[green]No failures detected. Pipeline integrity looks good.[/green]")
            return

        for sev in ("HIGH", "MEDIUM", "LOW"):
            count = self.severity_breakdown.get(sev, 0)
            if count == 0:
                continue
            colour = _SEVERITY_COLOURS[sev]
            console.print(f"[bold {colour}]{sev} severity: {count}[/bold {colour}]")
            for r in sorted(self.results, key=lambda x: _SEVERITY_ORDER.get(x.severity, 9)):
                if r.severity == sev:
                    console.print(f"  [{colour}]•[/{colour}] {r.failure_class}: {r.description[:100]}")

        console.print()

    def export(self, path: str) -> None:
        export_html(self, path)
        console.print(f"[dim]Report exported to {path}[/dim]")

    def to_dict(self) -> dict:
        return {
            "total_tests": self.total_tests,
            "total_failures": self.total_failures,
            "pass_rate": self.pass_rate,
            "severity_breakdown": self.severity_breakdown,
            "failures": [r.to_dict() for r in self.results],
        }


class Auditor:
    """
    Wrap any LLM pipeline and run it through SilentFail's adversarial test batteries.

    Parameters
    ----------
    pipeline:
        Any callable that accepts a single input and returns an output.
        Use ``LangChainRunner(chain)`` for LangChain chains.
    input_schema:
        Pydantic model describing the pipeline's expected input.
        Required for ``FailureClass.SCHEMA_DRIFT``.
    output_schema:
        Pydantic model describing the pipeline's expected output.
        Required for ``FailureClass.HALLUCINATED_STRUCTURE``.
    golden_dataset:
        List of ``(question, expected_answer, [keywords])`` tuples.
        Required for ``FailureClass.CONFIDENT_WRONG``.
    context_window:
        Token limit of the underlying model.
        Required for ``FailureClass.SILENT_TRUNCATION``.
    test_inputs:
        Real inputs to run through the pipeline for structural checks.
        Required for ``FailureClass.HALLUCINATED_STRUCTURE``.
    """

    def __init__(
        self,
        pipeline: Callable,
        input_schema: Optional[Type[BaseModel]] = None,
        output_schema: Optional[Type[BaseModel]] = None,
        golden_dataset: Optional[List] = None,
        context_window: Optional[int] = None,
        test_inputs: Optional[List[Any]] = None,
    ):
        self.pipeline = pipeline
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.golden_dataset = golden_dataset
        self.context_window = context_window
        self.test_inputs = test_inputs

    def run(
        self,
        failure_classes: Optional[List[FailureClass]] = None,
    ) -> AuditReport:
        if failure_classes is None:
            failure_classes = list(FailureClass)

        all_results: list[FailureResult] = []
        total_tests = 0

        if FailureClass.SCHEMA_DRIFT in failure_classes:
            if self.input_schema is None:
                console.print("[yellow]⚠ SCHEMA_DRIFT skipped: no input_schema provided.[/yellow]")
            else:
                from silentefail.failure_classes.schema_drift import SchemaDriftDetector
                detector = SchemaDriftDetector(self.input_schema, self.pipeline)
                variants = detector.generate_adversarial_inputs()
                total_tests += len(variants)
                all_results.extend(detector.run())

        if FailureClass.CONFIDENT_WRONG in failure_classes:
            if self.golden_dataset is None:
                console.print("[yellow]⚠ CONFIDENT_WRONG skipped: no golden_dataset provided.[/yellow]")
            else:
                from silentefail.failure_classes.confident_wrong import ConfidentWrongDetector
                detector = ConfidentWrongDetector(self.pipeline, self.golden_dataset)
                total_tests += len(detector.golden_dataset)
                all_results.extend(detector.run())

        if FailureClass.SILENT_TRUNCATION in failure_classes:
            if self.context_window is None:
                console.print("[yellow]⚠ SILENT_TRUNCATION skipped: no context_window provided.[/yellow]")
            else:
                from silentefail.failure_classes.silent_truncation import (
                    SilentTruncationDetector, FILL_PERCENTAGES
                )
                detector = SilentTruncationDetector(self.pipeline, self.context_window)
                total_tests += len(FILL_PERCENTAGES)
                all_results.extend(detector.run())

        if FailureClass.HALLUCINATED_STRUCTURE in failure_classes:
            if self.output_schema is None or self.test_inputs is None:
                console.print(
                    "[yellow]⚠ HALLUCINATED_STRUCTURE skipped: "
                    "output_schema and test_inputs are both required.[/yellow]"
                )
            else:
                from silentefail.failure_classes.hallucinated_structure import (
                    HallucinatedStructureDetector
                )
                detector = HallucinatedStructureDetector(
                    self.pipeline, self.output_schema, self.test_inputs
                )
                total_tests += len(self.test_inputs)
                all_results.extend(detector.run())

        return AuditReport(results=all_results, total_tests=total_tests)
