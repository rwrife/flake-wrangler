from __future__ import annotations


class LineResultsAdapter:
    """Parse lines like: '<test-id> PASS' or '<test-id> FAIL'."""

    def parse(self, stdout: str) -> dict[str, bool]:
        outcomes: dict[str, bool] = {}
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.rsplit(maxsplit=1)
            if len(parts) != 2:
                continue

            test_id, status = parts
            normalized = status.lower()
            if normalized == "pass":
                outcomes[test_id] = True
            elif normalized == "fail":
                outcomes[test_id] = False
        return outcomes
