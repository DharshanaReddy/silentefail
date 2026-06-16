"""SilentFail — LLM pipeline integrity testing."""
from silentefail.auditor import Auditor, AuditReport, FailureClass
from silentefail.models import FailureResult, GoldenSample
from silentefail.golden.dataset import GoldenDataset
from silentefail.runners.function_runner import FunctionRunner
from silentefail.runners.langchain_runner import LangChainRunner

__version__ = "0.1.0"

__all__ = [
    "Auditor",
    "AuditReport",
    "FailureClass",
    "FailureResult",
    "GoldenSample",
    "GoldenDataset",
    "FunctionRunner",
    "LangChainRunner",
]
