from __future__ import annotations

from dataclasses import dataclass

import pytest

from flake_wrangler.core import execute_repeated


@dataclass
class FakeRunResult:
    exit_code: int
    stdout: str


class FakeRunner:
    def __init__(self, runs: list[FakeRunResult]) -> None:
        self._runs = list(runs)
        self.calls = 0

    def run(self) -> FakeRunResult:
        if not self._runs:
            raise AssertionError("runner called more times than expected")
        self.calls += 1
        return self._runs.pop(0)


class FakeAdapter:
    def __init__(self, parsed_runs: list[dict[str, bool]]) -> None:
        self._parsed_runs = list(parsed_runs)

    def parse(self, run_result: object) -> dict[str, bool]:
        if not self._parsed_runs:
            raise AssertionError("adapter called more times than expected")
        return self._parsed_runs.pop(0)


class FakeSkippingAdapter(FakeAdapter):
    def __init__(self, parsed_runs: list[dict[str, bool]], skipped_by_run: list[set[str]]) -> None:
        super().__init__(parsed_runs)
        self._skipped_by_run = list(skipped_by_run)
        self._last_skipped: set[str] = set()

    def parse(self, run_result: object) -> dict[str, bool]:
        outcomes = super().parse(run_result)
        if not self._skipped_by_run:
            raise AssertionError("skipped-by-run exhausted")
        self._last_skipped = self._skipped_by_run.pop(0)
        return outcomes

    def get_last_skipped_tests(self) -> set[str]:
        return set(self._last_skipped)


def test_execute_repeated_aggregates_results_and_keeps_going_on_non_zero_exit() -> None:
    runner = FakeRunner(
        [
            FakeRunResult(exit_code=0, stdout="run1"),
            FakeRunResult(exit_code=1, stdout="run2"),
            FakeRunResult(exit_code=0, stdout="run3"),
        ]
    )
    adapter = FakeAdapter(
        [
            {"tests/a.py::test_alpha": True, "tests/b.py::test_beta": False},
            {"tests/a.py::test_alpha": False, "tests/b.py::test_beta": False},
            {"tests/a.py::test_alpha": True, "tests/b.py::test_beta": True},
        ]
    )

    aggregated = execute_repeated(runner=runner, adapter=adapter, repeat=3)

    assert runner.calls == 3
    assert [run.exit_code for run in aggregated.runs] == [0, 1, 0]
    assert aggregated.by_test == {
        "tests/a.py::test_alpha": [True, False, True],
        "tests/b.py::test_beta": [False, False, True],
    }


def test_execute_repeated_tracks_skipped_only_tests_across_runs() -> None:
    runner = FakeRunner(
        [
            FakeRunResult(exit_code=0, stdout="run1"),
            FakeRunResult(exit_code=0, stdout="run2"),
        ]
    )
    adapter = FakeSkippingAdapter(
        [
            {"tests/a.py::test_alpha": True},
            {"tests/a.py::test_alpha": True},
        ],
        skipped_by_run=[
            {"tests/b.py::test_skipped"},
            {"tests/b.py::test_skipped"},
        ],
    )

    aggregated = execute_repeated(runner=runner, adapter=adapter, repeat=2)
    classifications, never_ran = aggregated.classify(threshold=0.1)

    assert [item.test_id for item in classifications] == ["tests/a.py::test_alpha"]
    assert never_ran == ["tests/b.py::test_skipped"]


def test_execute_repeated_requires_positive_repeat() -> None:
    with pytest.raises(ValueError, match="repeat must be >= 1"):
        execute_repeated(runner=FakeRunner([]), adapter=FakeAdapter([]), repeat=0)
