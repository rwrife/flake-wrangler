from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Sequence, cast

from .adapters import LineResultsAdapter, PytestJUnitResultsAdapter, PytestJUnitRunner
from .core import execute_repeated
from .reporters import ReportData, ReportFormat, build_reporter
from .runner import SubprocessRunner

DEFAULT_CONFIG_PATH = "flake-wrangler.toml"
RUNNER_CHOICES = ("auto", "pytest", "line")
REPORT_CHOICES = ("table", "json", "md")


@dataclass(frozen=True)
class RunSettings:
    runner: str
    repeat: int
    threshold: float
    report: ReportFormat
    out: str | None
    quarantine_out: str | None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flake-wrangler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a test command repeatedly")
    run_parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to TOML defaults file (default: flake-wrangler.toml)",
    )
    run_parser.add_argument(
        "--runner",
        choices=RUNNER_CHOICES,
        default=None,
        help="Runner mode: auto-detect from command, force pytest, or line parser",
    )
    run_parser.add_argument(
        "--repeat",
        type=int,
        default=None,
        help="How many runs to execute (can be set in config)",
    )
    run_parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Failure-rate threshold for flaky classification (default: 0.1)",
    )
    run_parser.add_argument(
        "--report",
        choices=REPORT_CHOICES,
        default=None,
        help="Report format (default: table)",
    )
    run_parser.add_argument(
        "--out",
        default=None,
        help="Write report output to a file path (default: stdout)",
    )
    run_parser.add_argument(
        "--quarantine-out",
        dest="quarantine_out",
        default=None,
        help="Write flaky test ids (one per line) to a file path",
    )
    run_parser.add_argument(
        "target_command",
        nargs=argparse.REMAINDER,
        help="Command to run. Example: flake-wrangler run --repeat 5 -- pytest -q",
    )
    return parser


def _normalize_command(command: Sequence[str]) -> list[str]:
    normalized = list(command)
    if normalized and normalized[0] == "--":
        normalized = normalized[1:]
    return normalized or ["pytest"]


def _is_pytest_command(command: Sequence[str]) -> bool:
    if not command:
        return False

    first = os.path.basename(command[0])
    if first in {"pytest", "py.test"}:
        return True

    if first.startswith("python") and len(command) >= 3:
        return command[1] == "-m" and command[2] == "pytest"

    return False


def _load_run_config(config_path: str) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with path.open("rb") as handle:
            parsed = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in {config_path}: {exc}") from exc

    if not isinstance(parsed, dict):
        return {}

    raw_run = parsed.get("run", parsed)
    if not isinstance(raw_run, dict):
        raise ValueError(
            f"Invalid config structure in {config_path}: expected a [run] table"
        )

    normalized: dict[str, Any] = {}
    for key, value in raw_run.items():
        if isinstance(key, str):
            normalized[key.replace("-", "_")] = value
    return normalized


def _resolve_run_settings(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RunSettings:
    try:
        config = _load_run_config(args.config)
    except ValueError as exc:
        parser.error(str(exc))

    runner = args.runner if args.runner is not None else config.get("runner", "auto")
    if not isinstance(runner, str) or runner not in RUNNER_CHOICES:
        parser.error(
            "Invalid runner. Use one of: auto, pytest, line (via --runner or config run.runner)"
        )

    repeat = args.repeat if args.repeat is not None else config.get("repeat")
    if repeat is None:
        parser.error(
            "Missing required repeat count. Pass --repeat or set run.repeat in flake-wrangler.toml"
        )
    if not isinstance(repeat, int):
        parser.error("run.repeat must be an integer")
    if repeat <= 0:
        parser.error("repeat must be greater than 0")

    threshold = args.threshold if args.threshold is not None else config.get("threshold", 0.1)
    if not isinstance(threshold, (int, float)):
        parser.error("threshold must be a number")
    threshold = float(threshold)
    if not 0 <= threshold <= 1:
        parser.error("threshold must be between 0 and 1")

    report = args.report if args.report is not None else config.get("report", "table")
    if not isinstance(report, str) or report not in REPORT_CHOICES:
        parser.error("report must be one of: table, json, md")

    out = args.out if args.out is not None else config.get("out")
    if out is not None and not isinstance(out, str):
        parser.error("out must be a string path")

    quarantine_out = (
        args.quarantine_out if args.quarantine_out is not None else config.get("quarantine_out")
    )
    if quarantine_out is not None and not isinstance(quarantine_out, str):
        parser.error("quarantine_out must be a string path")

    return RunSettings(
        runner=runner,
        repeat=repeat,
        threshold=threshold,
        report=cast(ReportFormat, report),
        out=out,
        quarantine_out=quarantine_out,
    )


def _build_execution_pair(target_command: Sequence[str], runner_mode: str):
    command = _normalize_command(target_command)

    if runner_mode == "pytest":
        return PytestJUnitRunner(command), PytestJUnitResultsAdapter()
    if runner_mode == "line":
        return SubprocessRunner(command), LineResultsAdapter()

    if _is_pytest_command(command):
        return PytestJUnitRunner(command), PytestJUnitResultsAdapter()
    return SubprocessRunner(command), LineResultsAdapter()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        settings = _resolve_run_settings(args, parser)
        runner, adapter = _build_execution_pair(args.target_command, settings.runner)

        aggregated = execute_repeated(runner=runner, adapter=adapter, repeat=settings.repeat)
        classifications, never_ran = aggregated.classify(threshold=settings.threshold)

        reporter = build_reporter(settings.report)
        report_data = ReportData(
            repeat=settings.repeat,
            threshold=settings.threshold,
            tests=classifications,
            never_ran=never_ran,
        )
        rendered = reporter.render(report_data)

        if settings.out:
            with open(settings.out, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.write("\n")
        else:
            print(rendered)

        if settings.quarantine_out:
            quarantine_tests = sorted(
                item.test_id for item in classifications if item.verdict.lower() == "flaky"
            )
            with open(settings.quarantine_out, "w", encoding="utf-8") as handle:
                if quarantine_tests:
                    handle.write("\n".join(quarantine_tests))
                    handle.write("\n")

        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
