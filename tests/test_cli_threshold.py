from __future__ import annotations

from dataclasses import dataclass

from flake_wrangler import cli
from flake_wrangler.models import TestClassification as Classification


@dataclass
class _FakeRun:
    run_index: int
    exit_code: int
    test_outcomes: dict[str, bool]


class _FakeAggregated:
    def __init__(self) -> None:
        self.runs = [_FakeRun(run_index=1, exit_code=0, test_outcomes={"t": True})]
        self.by_test = {"t": [True]}
        self.classify_calls: list[float] = []

    def classify(self, *, threshold: float = 0.1):
        self.classify_calls.append(threshold)
        return (
            [
                Classification(
                    test_id="t",
                    runs=1,
                    fails=0,
                    failure_rate=0.0,
                    verdict="stable",
                )
            ],
            [],
        )


def test_cli_honors_threshold_argument(monkeypatch, capsys) -> None:
    fake = _FakeAggregated()

    def fake_execute_repeated(*, runner, adapter, repeat):
        return fake

    monkeypatch.setattr(cli, "execute_repeated", fake_execute_repeated)

    code = cli.main(["run", "--repeat", "1", "--threshold", "0.33", "--", "echo", "ok"])

    assert code == 0
    assert fake.classify_calls == [0.33]

    out = capsys.readouterr().out
    assert "Test" in out
    assert "Failure rate" in out
    assert "stable" in out


def test_cli_quarantine_out_writes_only_flaky_in_deterministic_order(monkeypatch, tmp_path) -> None:
    class _FakeAggregatedForQuarantine:
        def classify(self, *, threshold: float = 0.1):
            return (
                [
                    Classification(
                        test_id="tests/z.py::test_stable",
                        runs=3,
                        fails=0,
                        failure_rate=0.0,
                        verdict="stable",
                    ),
                    Classification(
                        test_id="tests/b.py::test_flaky_two",
                        runs=3,
                        fails=2,
                        failure_rate=0.666,
                        verdict="flaky",
                    ),
                    Classification(
                        test_id="tests/a.py::test_flaky_one",
                        runs=3,
                        fails=1,
                        failure_rate=0.333,
                        verdict="flaky",
                    ),
                ],
                [],
            )

    monkeypatch.setattr(cli, "execute_repeated", lambda **kwargs: _FakeAggregatedForQuarantine())

    quarantine_path = tmp_path / "quarantine.txt"
    code = cli.main(
        [
            "run",
            "--repeat",
            "3",
            "--quarantine-out",
            str(quarantine_path),
            "--no-fail-on-flaky",
            "--",
            "echo",
            "ok",
        ]
    )

    assert code == 0
    assert quarantine_path.read_text(encoding="utf-8") == (
        "tests/a.py::test_flaky_one\n"
        "tests/b.py::test_flaky_two\n"
    )


def test_cli_quarantine_out_writes_empty_file_when_no_flaky(monkeypatch, tmp_path) -> None:
    class _FakeAggregatedNoFlaky:
        def classify(self, *, threshold: float = 0.1):
            return (
                [
                    Classification(
                        test_id="tests/a.py::test_stable",
                        runs=2,
                        fails=0,
                        failure_rate=0.0,
                        verdict="stable",
                    )
                ],
                [],
            )

    monkeypatch.setattr(cli, "execute_repeated", lambda **kwargs: _FakeAggregatedNoFlaky())

    quarantine_path = tmp_path / "quarantine-empty.txt"
    code = cli.main(
        [
            "run",
            "--repeat",
            "2",
            "--quarantine-out",
            str(quarantine_path),
            "--",
            "echo",
            "ok",
        ]
    )

    assert code == 0
    assert quarantine_path.read_text(encoding="utf-8") == ""


def test_cli_returns_nonzero_when_flaky_and_fail_on_flaky_enabled(monkeypatch) -> None:
    class _FakeAggregatedFlaky:
        def classify(self, *, threshold: float = 0.1):
            return (
                [
                    Classification(
                        test_id="tests/a.py::test_flaky",
                        runs=3,
                        fails=1,
                        failure_rate=0.333,
                        verdict="flaky",
                    )
                ],
                [],
            )

    monkeypatch.setattr(cli, "execute_repeated", lambda **kwargs: _FakeAggregatedFlaky())

    code = cli.main(["run", "--repeat", "3", "--", "echo", "ok"])
    assert code == 1


def test_cli_returns_zero_when_flaky_and_no_fail_on_flaky(monkeypatch) -> None:
    class _FakeAggregatedFlaky:
        def classify(self, *, threshold: float = 0.1):
            return (
                [
                    Classification(
                        test_id="tests/a.py::test_flaky",
                        runs=3,
                        fails=1,
                        failure_rate=0.333,
                        verdict="flaky",
                    )
                ],
                [],
            )

    monkeypatch.setattr(cli, "execute_repeated", lambda **kwargs: _FakeAggregatedFlaky())

    code = cli.main(["run", "--repeat", "3", "--no-fail-on-flaky", "--", "echo", "ok"])
    assert code == 0
