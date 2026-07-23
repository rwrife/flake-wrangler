from __future__ import annotations

import argparse
from typing import Sequence

from .adapters import LineResultsAdapter
from .core import execute_repeated
from .runner import SubprocessRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flake-wrangler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a test command repeatedly")
    run_parser.add_argument("--repeat", type=int, required=True, help="How many runs to execute")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        target_command = _normalize_command(args.target_command)
        runner = SubprocessRunner(target_command)
        adapter = LineResultsAdapter()
        aggregated = execute_repeated(runner=runner, adapter=adapter, repeat=args.repeat)

        for run in aggregated.runs:
            print(f"run={run.run_index} exit={run.exit_code} tests={len(run.test_outcomes)}")

        print("aggregated:")
        for test_id in sorted(aggregated.by_test):
            symbols = ["PASS" if passed else "FAIL" for passed in aggregated.by_test[test_id]]
            print(f"  {test_id}: {', '.join(symbols)}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
