from __future__ import annotations

from typing import Protocol

from .models import AggregatedRunResults


class RunResultLike(Protocol):
    exit_code: int
    stdout: str


class SupportsRun(Protocol):
    def run(self) -> RunResultLike:
        ...


class SupportsParse(Protocol):
    def parse(self, stdout: str) -> dict[str, bool]:
        ...


def execute_repeated(*, runner: SupportsRun, adapter: SupportsParse, repeat: int) -> AggregatedRunResults:
    """Run the test command N times and aggregate per-test pass/fail outcomes."""
    if repeat < 1:
        raise ValueError("repeat must be >= 1")

    aggregated = AggregatedRunResults(repeat=repeat)
    for run_index in range(1, repeat + 1):
        run_result = runner.run()
        test_outcomes = adapter.parse(run_result.stdout)
        aggregated.record_run(
            run_index=run_index,
            exit_code=run_result.exit_code,
            test_outcomes=test_outcomes,
        )

    return aggregated
