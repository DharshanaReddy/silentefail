"""Golden dataset builder and loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from silentefail.models import GoldenSample


class GoldenDataset:
    def __init__(self, samples: list[GoldenSample] | None = None):
        self.samples: list[GoldenSample] = samples or []

    def add(self, question: str, expected_answer: str, expected_keywords: list[str]) -> "GoldenDataset":
        self.samples.append(GoldenSample(question, expected_answer, expected_keywords))
        return self

    def save(self, path: str | Path) -> None:
        data = [
            {
                "question": s.question,
                "expected_answer": s.expected_answer,
                "expected_keywords": s.expected_keywords,
            }
            for s in self.samples
        ]
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "GoldenDataset":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        samples = [
            GoldenSample(
                question=r["question"],
                expected_answer=r["expected_answer"],
                expected_keywords=r["expected_keywords"],
            )
            for r in raw
        ]
        return cls(samples)

    @classmethod
    def from_list(cls, data: list[tuple | dict]) -> "GoldenDataset":
        samples = []
        for item in data:
            if isinstance(item, tuple):
                samples.append(GoldenSample.from_tuple(item))
            elif isinstance(item, dict):
                samples.append(GoldenSample(**item))
            else:
                samples.append(item)
        return cls(samples)

    def __iter__(self):
        return iter(self.samples)

    def __len__(self):
        return len(self.samples)
