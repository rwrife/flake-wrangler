from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from flake_wrangler.adapters.pytest_junit import PytestJUnitResultsAdapter, PytestJUnitRunner


def test_parse_junit_fixture_maps_outcomes_and_excludes_skips(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "junit_sample.xml"
    xml_path = tmp_path / "junit_sample.xml"
    shutil.copyfile(fixture, xml_path)

    adapter = PytestJUnitResultsAdapter()
    outcomes = adapter.parse(SimpleNamespace(junit_xml_path=str(xml_path)))

    assert outcomes == {
        "tests/test_math.py::test_pass": True,
        "tests/test_math.py::test_fail": False,
        "tests/test_math.py::test_error": False,
    }
    assert "tests/test_math.py::test_skip" not in outcomes
    assert adapter.get_last_skipped_tests() == {"tests/test_math.py::test_skip"}
    # Adapter performs best-effort temp artifact cleanup.
    assert not xml_path.exists()


def test_pytest_runner_adds_junit_xml_argument(monkeypatch) -> None:
    captured_command: list[str] = []

    def fake_run(command, check, capture_output, text):
        nonlocal captured_command
        captured_command = list(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = PytestJUnitRunner(["pytest", "-q"])
    result = runner.run()

    assert result.exit_code == 0
    assert result.stdout == "ok"
    assert any(part.startswith("--junit-xml=") for part in captured_command)

    junit_arg = next(part for part in captured_command if part.startswith("--junit-xml="))
    junit_path = Path(junit_arg.split("=", 1)[1])
    assert junit_path.exists()

    # Cleanup temp artifact created by runner in this unit test.
    junit_path.unlink(missing_ok=True)
