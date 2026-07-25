from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Verdict = Literal["stable", "suspect", "flaky"]


@dataclass(frozen=True)
class TestClassification:
    test_id: str
    runs: int
    fails: int
    failure_rate: float
    verdict: Verdict


@dataclass
class RunSnapshot:
    run_index: int
    exit_code: int
    test_outcomes: dict[str, bool]
    skipped_tests: set[str] = field(default_factory=set)


@dataclass
class AggregatedRunResults:
    repeat: int
    runs: list[RunSnapshot] = field(default_factory=list)
    by_test: dict[str, list[bool]] = field(default_factory=dict)
    skipped_by_test: dict[str, int] = field(default_factory=dict)

    def record_run(
        self,
        run_index: int,
        exit_code: int,
        test_outcomes: dict[str, bool],
        skipped_tests: set[str] | None = None,
    ) -> None:
        skipped = set(skipped_tests or set())
        self.runs.append(
            RunSnapshot(
                run_index=run_index,
                exit_code=exit_code,
                test_outcomes=dict(test_outcomes),
                skipped_tests=skipped,
            )
        )
        for test_id, passed in test_outcomes.items():
            self.by_test.setdefault(test_id, []).append(passed)

        for test_id in skipped:
            self.skipped_by_test[test_id] = self.skipped_by_test.get(test_id, 0) + 1

    def classify(self, *, threshold: float = 0.1) -> tuple[list[TestClassification], list[str]]:
        """Classify tests by fail-rate and identify tests that never ran.

        Rules:
        - rate == 0 -> stable
        - 0 < rate < threshold -> suspect
        - rate >= threshold -> flaky
        - tests seen only as skipped across all runs are returned in never_ran
        """
        if threshold < 0:
            raise ValueError("threshold must be >= 0")

        classifications: list[TestClassification] = []
        never_ran: list[str] = []

        all_test_ids = set(self.by_test) | set(self.skipped_by_test)
        for test_id in sorted(all_test_ids):
            outcomes = self.by_test.get(test_id, [])
            run_count = len(outcomes)
            if run_count == 0:
                if self.skipped_by_test.get(test_id, 0) > 0:
                    never_ran.append(test_id)
                continue

            fail_count = sum(1 for passed in outcomes if not passed)
            failure_rate = fail_count / run_count

            if failure_rate == 0:
                verdict: Verdict = "stable"
            elif failure_rate < threshold:
                verdict = "suspect"
            else:
                verdict = "flaky"

            classifications.append(
                TestClassification(
                    test_id=test_id,
                    runs=run_count,
                    fails=fail_count,
                    failure_rate=failure_rate,
                    verdict=verdict,
                )
            )

        return classifications, never_ran
