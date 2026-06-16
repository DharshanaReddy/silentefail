"""HTML report generator — produces a single self-contained file."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from silentefail.auditor import AuditReport

_TEMPLATE_DIR = Path(__file__).parent


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    def tojson_filter(value, indent=None):
        try:
            return json.dumps(value, indent=indent, ensure_ascii=False, default=str)
        except Exception:
            return str(value)

    env.filters["tojson"] = tojson_filter
    return env


def generate_html(report: "AuditReport") -> str:
    env = _jinja_env()
    template = env.get_template("template.html")

    total = report.total_tests
    failures = report.total_failures
    pass_rate = round(100 * (total - failures) / total, 1) if total else 100.0

    # Convert FailureResult objects to plain dicts for the template
    failures_by_class: dict[str, list[dict]] = {}
    for cls_name, cls_failures in report.failures_by_class.items():
        failures_by_class[cls_name] = [f.to_dict() for f in cls_failures]

    return template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total_tests=total,
        total_failures=failures,
        pass_rate=pass_rate,
        severity_breakdown=report.severity_breakdown,
        failures_by_class=failures_by_class,
    )


def export_html(report: "AuditReport", path: str) -> None:
    html = generate_html(report)
    Path(path).write_text(html, encoding="utf-8")
