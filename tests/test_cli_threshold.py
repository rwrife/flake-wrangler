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
