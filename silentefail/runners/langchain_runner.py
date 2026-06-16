"""Wraps a LangChain Runnable/chain for use with SilentFail detectors."""
from __future__ import annotations

from typing import Any


class LangChainRunner:
    """
    Wraps a LangChain chain (any object with `.invoke`) so it presents
    a simple callable interface expected by SilentFail detectors.
    """

    def __init__(self, chain: Any, config: dict | None = None):
        if not hasattr(chain, "invoke"):
            raise TypeError(
                f"Expected a LangChain Runnable with .invoke(), got {type(chain).__name__}"
            )
        self.chain = chain
        self.config = config or {}

    def __call__(self, input_data: Any) -> Any:
        return self.chain.invoke(input_data, config=self.config if self.config else None)
