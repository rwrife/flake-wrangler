from __future__ import annotations

from typing import Any
from typing import Protocol


class ResultsAdapter(Protocol):
    """Converts a run result into a normalized per-test pass/fail map."""

    def parse(self, run_result: Any) -> dict[str, bool]:
        ...
