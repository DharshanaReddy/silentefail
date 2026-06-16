"""Log replay utilities — replay captured failure inputs against an updated pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def load_replay_log(path: str | Path) -> list[dict]:
    """Load a JSON-lines replay log written by the auditor."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def replay(pipeline: Callable, log_path: str | Path) -> list[dict]:
    """Re-run captured failure inputs through *pipeline* and return results."""
    entries = load_replay_log(log_path)
    results = []
    for entry in entries:
        inp = entry.get("input")
        try:
            output = pipeline(inp)
            results.append({"input": inp, "output": output, "error": None})
        except Exception as exc:
            results.append({"input": inp, "output": None, "error": str(exc)})
    return results
