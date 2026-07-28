from __future__ import annotations

from flake_wrangler import cli
from flake_wrangler.models import TestClassification as Classification


class _FakeAggregated:
    def __init__(self) -> None:
        self.classify_calls: list[float] = []

    def classify(self, *, threshold: float = 0.1):
        self.classify_calls.append(threshold)
        return (
            [
                Classification(
                    test_id="tests/a.py::test_flaky",
                    runs=4,
                    fails=2,
                    failure_rate=0.5,
                    verdict="flaky",
                )
            ],
            [],
        )


def test_cli_config_defaults_and_cli_flags_override(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "flake-wrangler.toml").write_text(
        """
[run]
runner = "line"
repeat = 4
threshold = 0.25
report = "json"
out = "from-config.json"
quarantine-out = "from-config.txt"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    fake = _FakeAggregated()
    calls: list[dict[str, object]] = []

    def fake_execute_repeated(*, runner, adapter, repeat):
        calls.append({"runner": runner, "adapter": adapter, "repeat": repeat})
        return fake

    monkeypatch.setattr(cli, "execute_repeated", fake_execute_repeated)

    # Call 1: consume config defaults.
    code = cli.main(["run", "--", "echo", "ok"])
    assert code == 0
    assert calls[0]["repeat"] == 4
    assert calls[0]["runner"].__class__.__name__ == "SubprocessRunner"
    assert calls[0]["adapter"].__class__.__name__ == "LineResultsAdapter"
    assert (tmp_path / "from-config.json").exists()
    assert (tmp_path / "from-config.txt").read_text(encoding="utf-8") == "tests/a.py::test_flaky\n"

    # Call 2: explicit CLI flags override config values.
    code = cli.main(
        [
            "run",
            "--runner",
            "pytest",
            "--repeat",
            "2",
            "--threshold",
            "0.8",
            "--report",
            "md",
            "--out",
            "from-cli.md",
            "--quarantine-out",
            "from-cli.txt",
            "--",
            "echo",
            "ok",
        ]
    )
    assert code == 0
    assert calls[1]["repeat"] == 2
    assert calls[1]["runner"].__class__.__name__ == "PytestJUnitRunner"
    assert calls[1]["adapter"].__class__.__name__ == "PytestJUnitResultsAdapter"
    assert (tmp_path / "from-cli.md").exists()
    assert (tmp_path / "from-cli.txt").read_text(encoding="utf-8") == "tests/a.py::test_flaky\n"

    assert fake.classify_calls == [0.25, 0.8]
    assert capsys.readouterr().out == ""
