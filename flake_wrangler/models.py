from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunSnapshot:
    run_index: int
    exit_code: int
    test_outcomes: dict[str, bool]


@dataclass
class AggregatedRunResults:
    repeat: int
    runs: list[RunSnapshot] = field(default_factory=list)
    by_test: dict[str, list[bool]] = field(default_factory=dict)

    def record_run(self, run_index: int, exit_code: int, test_outcomes: dict[str, bool]) -> None:
        self.runs.append(
            RunSnapshot(
                run_index=run_index,
                exit_code=exit_code,
                test_outcomes=dict(test_outcomes),
            )
        )
        for test_id, passed in test_outcomes.items():
            self.by_test.setdefault(test_id, []).append(passed)
