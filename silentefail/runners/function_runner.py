"""Wraps any Python callable for use with SilentFail detectors."""
from __future__ import annotations

from typing import Any, Callable


class FunctionRunner:
    """Thin wrapper that normalises a callable into the pipeline interface."""

    def __init__(self, fn: Callable, **kwargs):
        self.fn = fn
        self.kwargs = kwargs

    def __call__(self, input_data: Any) -> Any:
        return self.fn(input_data, **self.kwargs)
