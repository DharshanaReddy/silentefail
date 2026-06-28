# SilentFail

[![PyPI](https://img.shields.io/pypi/v/silentefail)](https://pypi.org/project/silentefail/)
[![Python](https://img.shields.io/pypi/pyversions/silentefail)](https://pypi.org/project/silentefail/)
[![CI](https://github.com/DharshanaReddy/silentefail/actions/workflows/ci.yml/badge.svg)](https://github.com/DharshanaReddy/silentefail/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**LLM pipeline integrity testing — catch the failures your tests never will.**

```bash
pip install silentefail
```

---

## Origin

While building data extraction pipelines at Fullcast, I kept hitting the same class of bug: the pipeline returned something that *looked* valid — no exception, no null, a real dict — but the data was wrong, truncated, or hallucinated. Unit tests passed because we were testing the happy path. Production broke because LLMs don't always follow the schema. SilentFail is the harness I wish I'd had. It runs your pipeline against adversarial inputs designed to expose the four failure modes that slip past every eval framework I tried.

---

## Quick Start

```python
from pydantic import BaseModel
from silentefail import Auditor, FailureClass

class InputData(BaseModel):
    text: str
    context: str

class ExtractedData(BaseModel):
    name: str
    value: float
    category: str

def my_pipeline(input_data: dict) -> dict:
    # Your LLM call here
    ...

auditor = Auditor(
    pipeline=my_pipeline,
    input_schema=InputData,
    output_schema=ExtractedData,
    golden_dataset=[
        ("What is 2+2?", "4", ["4", "four"]),
        ("Capital of France?", "Paris", ["Paris"]),
    ],
    context_window=128000,
    test_inputs=[
        {"text": "Revenue was $1.2M", "context": "Q3 report"},
    ],
)

report = auditor.run([
    FailureClass.SCHEMA_DRIFT,
    FailureClass.HALLUCINATED_STRUCTURE,
])

report.summary()
# SilentFail Audit Report
# ========================
# Tests run:         24
# Failures detected: 3
# Pass rate:         87.5%
#
# HIGH severity: 2
#   • SCHEMA_DRIFT: None returned on missing 'context' field
#   • HALLUCINATED_STRUCTURE: Invented key 'confidence_score' not in schema
# MEDIUM severity: 1
#   • SCHEMA_DRIFT: Unhandled KeyError on extra field 'metadata'

report.export("silentefail_report.html")
```

---

## LangChain Integration

```python
from silentefail import Auditor
from silentefail.runners import LangChainRunner

runner = LangChainRunner(your_langchain_chain)

auditor = Auditor(
    pipeline=runner,
    input_schema=InputData,
    output_schema=OutputSchema,
    ...
)
report = auditor.run()
```

---

## The Four Failure Classes

### Class 1 — Schema Drift

Your pipeline receives a slightly malformed input: a missing required field, a `None` where a string is expected, an extra unexpected key. What happens?

- **Silent `None` return** — the pipeline swallows the bad input and returns nothing. No error, no log. Your downstream code crashes mysteriously.
- **Unhandled exception** — `KeyError`, `AttributeError`, or `TypeError` bubbles up instead of a clear `ValidationError`.

SilentFail generates a battery of adversarial input variants from your `input_schema` and runs them all.

```python
auditor = Auditor(pipeline=my_fn, input_schema=MyInputModel)
report = auditor.run([FailureClass.SCHEMA_DRIFT])
```

### Class 2 — Confident Wrong Answers

Given a golden dataset of known question→answer pairs, SilentFail checks two things: is the answer wrong, and does the pipeline express *any* uncertainty?

A pipeline that answers confidently and incorrectly 30% of the time is a calibration failure. This class finds it.

```python
golden = [
    ("What is 2+2?", "4", ["4", "four"]),
    ("Capital of France?", "Paris", ["Paris"]),
]
auditor = Auditor(pipeline=my_fn, golden_dataset=golden)
report = auditor.run([FailureClass.CONFIDENT_WRONG])
```

### Class 3 — Silent Truncation

At 50% context fill your pipeline returns 800 tokens. At 95% context fill it returns 80 tokens. No error — just a quietly shorter answer. Required fields are present but empty. Reasoning stops mid-sentence.

SilentFail pads inputs to 50%, 75%, 90%, 95%, and 99% of your declared context window and compares output length and completeness.

```python
auditor = Auditor(pipeline=my_fn, context_window=128000)
report = auditor.run([FailureClass.SILENT_TRUNCATION])
```

### Class 4 — Hallucinated Structure

Your output schema says `{name, value, category}`. The model returns `{name, value, category, confidence_score, reasoning, source_url}`. Or it returns `{name}` and drops the rest. Or the types are wrong — `value` is a string, not a float.

This class runs real inputs through your pipeline and validates every output against your `output_schema`.

```python
auditor = Auditor(
    pipeline=my_fn,
    output_schema=ExtractedData,
    test_inputs=[{"text": "Revenue was $1.2M", "context": "Q3"}],
)
report = auditor.run([FailureClass.HALLUCINATED_STRUCTURE])
```

---

## Why This Is Different

| Tool | What it tests |
|------|---------------|
| Evals / LLM-as-judge | Output *quality* |
| Pytest + mocks | Happy-path logic |
| **SilentFail** | **Pipeline *integrity* under adversarial conditions** |

Eval frameworks tell you if your model is smart. SilentFail tells you if your pipeline is *safe* — whether it will fail silently or loudly when reality diverges from your assumptions.

---

## Report

`report.export("report.html")` generates a self-contained dark-themed HTML file — no external dependencies, no CDN calls. Each failure shows the input, the output, the failure type, a severity badge, and a one-line fix recommendation. Share it with your team or drop it in a PR.

> View a [sample report](assets/sample_report.html) generated against the built-in example pipeline.

---

## API Reference

```python
Auditor(
    pipeline: Callable,           # Any callable: fn, chain.invoke, LangChainRunner(chain)
    input_schema: BaseModel,      # For SCHEMA_DRIFT
    output_schema: BaseModel,     # For HALLUCINATED_STRUCTURE
    golden_dataset: list[tuple],  # For CONFIDENT_WRONG: (question, answer, [keywords])
    context_window: int,          # For SILENT_TRUNCATION: token limit
    test_inputs: list,            # For HALLUCINATED_STRUCTURE: real inputs
)

auditor.run(failure_classes=[...]) -> AuditReport

report.summary()         # Rich console output
report.export(path)      # HTML file
report.to_dict()         # Machine-readable dict
```

---

## Installation

```bash
# Core (no LangChain)
pip install silentefail

# With LangChain support
pip install "silentefail[langchain]"

# For development
pip install "silentefail[dev]"
```

---

## Roadmap — v0.2.0

- [ ] **Async support** — run all four detectors in parallel for faster audits
- [ ] **OpenAI / Anthropic native runners** — first-class support without LangChain
- [ ] **CI integration** — `silentefail run` CLI command for pre-merge pipeline checks
- [ ] **Streaming truncation detection** — detect mid-token cutoffs in streaming responses
- [ ] **Golden dataset hub** — community-contributed golden datasets by domain (legal, medical, finance)
- [ ] **Pytest plugin** — `@silentefail.audit` decorator for inline pipeline tests

---

## Portfolio

Built by [Dharsha Reddy](https://github.com/DharshanaReddy).
