from __future__ import annotations

from flake_wrangler.models import AggregatedRunResults


def test_classification_applies_threshold_boundaries() -> None:
    aggregated = AggregatedRunResults(repeat=4)
    aggregated.record_run(
        run_index=1,
        exit_code=0,
        test_outcomes={
            "tests/a.py::test_stable": True,
            "tests/b.py::test_boundary": False,
            "tests/c.py::test_suspect": False,
            "tests/d.py::test_flaky": False,
        },
    )
    aggregated.record_run(
        run_index=2,
        exit_code=0,
        test_outcomes={
            "tests/a.py::test_stable": True,
            "tests/b.py::test_boundary": False,
            "tests/c.py::test_suspect": True,
            "tests/d.py::test_flaky": False,
        },
    )
    aggregated.record_run(
        run_index=3,
        exit_code=0,
        test_outcomes={
            "tests/a.py::test_stable": True,
            "tests/b.py::test_boundary": True,
            "tests/c.py::test_suspect": True,
            "tests/d.py::test_flaky": False,
        },
    )
    aggregated.record_run(
        run_index=4,
        exit_code=0,
        test_outcomes={
            "tests/a.py::test_stable": True,
            "tests/b.py::test_boundary": True,
            "tests/c.py::test_suspect": True,
            "tests/d.py::test_flaky": True,
        },
    )

    classifications, never_ran = aggregated.classify(threshold=0.5)

    verdicts = {item.test_id: item.verdict for item in classifications}
    rates = {item.test_id: item.failure_rate for item in classifications}

    assert never_ran == []
    assert verdicts["tests/a.py::test_stable"] == "stable"
    assert verdicts["tests/c.py::test_suspect"] == "suspect"
    # Exactly at threshold should be flaky.
    assert rates["tests/b.py::test_boundary"] == 0.5
    assert verdicts["tests/b.py::test_boundary"] == "flaky"
    assert verdicts["tests/d.py::test_flaky"] == "flaky"


def test_classification_reports_never_ran_when_always_skipped() -> None:
    aggregated = AggregatedRunResults(repeat=3)
    aggregated.record_run(
        run_index=1,
        exit_code=0,
        test_outcomes={"tests/a.py::test_mixed": True},
        skipped_tests={"tests/z.py::test_never_ran", "tests/a.py::test_mixed"},
    )
    aggregated.record_run(
        run_index=2,
        exit_code=0,
        test_outcomes={"tests/a.py::test_mixed": True},
        skipped_tests={"tests/z.py::test_never_ran"},
    )
    aggregated.record_run(
        run_index=3,
        exit_code=0,
        test_outcomes={"tests/a.py::test_mixed": False},
        skipped_tests={"tests/z.py::test_never_ran"},
    )

    classifications, never_ran = aggregated.classify(threshold=0.5)
    by_test = {item.test_id: item for item in classifications}

    assert never_ran == ["tests/z.py::test_never_ran"]
    # Mixed skipped + executed test should not be considered never-ran.
    assert by_test["tests/a.py::test_mixed"].runs == 3
    assert by_test["tests/a.py::test_mixed"].fails == 1
    assert by_test["tests/a.py::test_mixed"].verdict == "suspect"
