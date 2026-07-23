from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass
class SubprocessRunResult:
    exit_code: int
    stdout: str
    stderr: str


class SubprocessRunner:
    def __init__(self, command: Sequence[str]) -> None:
        if not command:
            raise ValueError("command must not be empty")
        self.command = list(command)

    def run(self) -> SubprocessRunResult:
        completed = subprocess.run(
            self.command,
            check=False,
            capture_output=True,
            text=True,
        )
        return SubprocessRunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
