from __future__ import annotations

import argparse
import os
from typing import Sequence

from .adapters import LineResultsAdapter, PytestJUnitResultsAdapter, PytestJUnitRunner
from .core import execute_repeated
from .reporters import ReportData, build_reporter
from .runner import SubprocessRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flake-wrangler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a test command repeatedly")
    run_parser.add_argument("--repeat", type=int, required=True, help="How many runs to execute")
    run_parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Failure-rate threshold for flaky classification (default: 0.1)",
    )
    run_parser.add_argument(
        "--report",
        choices=["table", "json", "md"],
        default="table",
        help="Report format (default: table)",
    )
    run_parser.add_argument(
        "--out",
        help="Write report output to a file path (default: stdout)",
    )
    run_parser.add_argument(
        "--quarantine-out",
        help="Write flaky test ids (one per line) to a file path",
    )
    run_parser.add_argument(
        "target_command",
        nargs=argparse.REMAINDER,
        help="Command to run. Example: flake-wrangler run --repeat 5 -- pytest -q",
    )
    return parser


def _normalize_command(command: Sequence[str]) -> list[str]:
    command = list(command)
    if command and command[0] == "--":
        command = command[1:]
    return command or ["pytest"]


def _is_pytest_command(command: Sequence[str]) -> bool:
    if not command:
        return False

    first = os.path.basename(command[0])
    if first in {"pytest", "py.test"}:
        return True

    if first.startswith("python") and len(command) >= 3:
        return command[1] == "-m" and command[2] == "pytest"

    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        target_command = _normalize_command(args.target_command)
        if _is_pytest_command(target_command):
            runner = PytestJUnitRunner(target_command)
            adapter = PytestJUnitResultsAdapter()
        else:
            runner = SubprocessRunner(target_command)
            adapter = LineResultsAdapter()
        aggregated = execute_repeated(runner=runner, adapter=adapter, repeat=args.repeat)
        classifications, never_ran = aggregated.classify(threshold=args.threshold)

        reporter = build_reporter(args.report)
        report_data = ReportData(
            repeat=args.repeat,
            threshold=args.threshold,
            tests=classifications,
            never_ran=never_ran,
        )
        rendered = reporter.render(report_data)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.write("\n")
        else:
            print(rendered)

        if args.quarantine_out:
            quarantine_tests = sorted(
                item.test_id for item in classifications if item.verdict.lower() == "flaky"
            )
            with open(args.quarantine_out, "w", encoding="utf-8") as handle:
                if quarantine_tests:
                    handle.write("\n".join(quarantine_tests))
                    handle.write("\n")

        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
