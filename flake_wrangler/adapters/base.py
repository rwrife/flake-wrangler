from __future__ import annotations

from typing import Protocol


class ResultsAdapter(Protocol):
    """Converts runner stdout into a normalized per-test pass/fail map."""

    def parse(self, stdout: str) -> dict[str, bool]:
        ...
