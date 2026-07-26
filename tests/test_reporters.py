from __future__ import annotations

import json

from flake_wrangler import cli
from flake_wrangler.models import TestClassification as Classification
from flake_wrangler.reporters import JsonReporter, MarkdownReporter, ReportData, TableReporter


def _sample_data() -> ReportData:
    return ReportData(
        repeat=5,
        threshold=0.2,
        tests=[
            Classification(
                test_id="tests/a.py::test_alpha",
                runs=5,
                fails=0,
                failure_rate=0.0,
                verdict="stable",
            ),
            Classification(
                test_id="tests/b.py::test_beta",
                runs=5,
                fails=2,
                failure_rate=0.4,
                verdict="flaky",
            ),
        ],
        never_ran=["tests/c.py::test_skipped"],
    )


def test_table_reporter_includes_required_columns() -> None:
    rendered = TableReporter().render(_sample_data())

    assert "Test" in rendered
    assert "Runs" in rendered
    assert "Fails" in rendered
    assert "Failure rate" in rendered
    assert "Verdict" in rendered
    assert "tests/b.py::test_beta" in rendered
    assert "0.400" in rendered


def test_json_reporter_emits_stable_schema() -> None:
    rendered = JsonReporter().render(_sample_data())
    payload = json.loads(rendered)

    assert payload["schema_version"] == "1.0"
    assert payload["tool"] == "flake-wrangler"
    assert payload["threshold"] == 0.2
    assert payload["repeat"] == 5
    assert payload["tests"][1]["test"] == "tests/b.py::test_beta"
    assert payload["tests"][1]["verdict"] == "flaky"
    assert payload["never_ran"] == ["tests/c.py::test_skipped"]


def test_markdown_reporter_emits_comment_friendly_table() -> None:
    rendered = MarkdownReporter().render(_sample_data())

    assert "| Test | Runs | Fails | Failure rate | Verdict |" in rendered
    assert "| tests/a.py::test_alpha | 5 | 0 | 0.000 | stable |" in rendered
    assert "**Never ran**" in rendered


def test_cli_out_writes_report_to_file(monkeypatch, tmp_path, capsys) -> None:
    class _FakeAggregated:
        def classify(self, *, threshold: float = 0.1):
            return (
                [
                    Classification(
                        test_id="tests/a.py::test_alpha",
                        runs=2,
                        fails=1,
                        failure_rate=0.5,
                        verdict="flaky",
                    )
                ],
                [],
            )

    monkeypatch.setattr(cli, "execute_repeated", lambda **kwargs: _FakeAggregated())

    out_path = tmp_path / "report.md"
    code = cli.main(
        [
            "run",
            "--repeat",
            "2",
            "--report",
            "md",
            "--out",
            str(out_path),
            "--",
            "echo",
            "ok",
        ]
    )

    assert code == 0
    assert capsys.readouterr().out == ""
    content = out_path.read_text(encoding="utf-8")
    assert "| Test | Runs | Fails | Failure rate | Verdict |" in content
    assert "tests/a.py::test_alpha" in content
