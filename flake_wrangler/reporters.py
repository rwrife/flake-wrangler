from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, Sequence

from .models import TestClassification

ReportFormat = Literal["table", "json", "md"]


@dataclass(frozen=True)
class ReportData:
    repeat: int
    threshold: float
    tests: list[TestClassification]
    never_ran: list[str]


class Reporter:
    def render(self, data: ReportData) -> str:
        raise NotImplementedError


def _to_rows(tests: Sequence[TestClassification]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in tests:
        rows.append(
            [
                item.test_id,
                str(item.runs),
                str(item.fails),
                f"{item.failure_rate:.3f}",
                item.verdict,
            ]
        )
    return rows


class TableReporter(Reporter):
    headers = ["Test", "Runs", "Fails", "Failure rate", "Verdict"]

    def render(self, data: ReportData) -> str:
        rows = _to_rows(data.tests)
        widths = [len(header) for header in self.headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        def format_row(cells: Sequence[str]) -> str:
            return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

        lines = [format_row(self.headers)]
        lines.append(format_row(["-" * width for width in widths]))
        for row in rows:
            lines.append(format_row(row))

        if data.never_ran:
            lines.append("")
            lines.append("Never ran:")
            for test_id in data.never_ran:
                lines.append(f"- {test_id}")

        return "\n".join(lines)


class JsonReporter(Reporter):
    def render(self, data: ReportData) -> str:
        payload = {
            "schema_version": "1.0",
            "tool": "flake-wrangler",
            "threshold": data.threshold,
            "repeat": data.repeat,
            "tests": [
                {
                    "test": item.test_id,
                    "runs": item.runs,
                    "fails": item.fails,
                    "failure_rate": item.failure_rate,
                    "verdict": item.verdict,
                }
                for item in data.tests
            ],
            "never_ran": data.never_ran,
        }
        return json.dumps(payload, indent=2, sort_keys=True)


class MarkdownReporter(Reporter):
    headers = ["Test", "Runs", "Fails", "Failure rate", "Verdict"]

    def render(self, data: ReportData) -> str:
        lines = [
            "| " + " | ".join(self.headers) + " |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
        for row in _to_rows(data.tests):
            lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")

        if data.never_ran:
            lines.append("")
            lines.append("**Never ran**")
            lines.append("")
            for test_id in data.never_ran:
                lines.append(f"- `{test_id}`")

        return "\n".join(lines)


def build_reporter(report_format: ReportFormat) -> Reporter:
    if report_format == "table":
        return TableReporter()
    if report_format == "json":
        return JsonReporter()
    if report_format == "md":
        return MarkdownReporter()
    raise ValueError(f"unsupported report format: {report_format}")
