from __future__ import annotations

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class PytestJUnitRunResult:
    exit_code: int
    stdout: str
    stderr: str
    junit_xml_path: str


class PytestJUnitRunner:
    """Run pytest and emit JUnit XML to a temporary file."""

    def __init__(self, command: Sequence[str] | None = None) -> None:
        cmd = list(command or ["pytest"])
        if not cmd:
            raise ValueError("command must not be empty")
        self.command = cmd

    def run(self) -> PytestJUnitRunResult:
        with tempfile.NamedTemporaryFile(prefix="flake-wrangler-", suffix=".xml", delete=False) as tmp:
            junit_xml_path = tmp.name

        command = [*self.command, f"--junit-xml={junit_xml_path}"]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        return PytestJUnitRunResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            junit_xml_path=junit_xml_path,
        )


class PytestJUnitResultsAdapter:
    """Parse pytest JUnit XML into normalized pass/fail outcomes.

    Skipped tests are excluded from output so they do not affect fail-rate math.
    """

    def parse(self, run_result: object) -> dict[str, bool]:
        junit_xml_path = getattr(run_result, "junit_xml_path", None)
        if not isinstance(junit_xml_path, str) or not junit_xml_path:
            return {}

        try:
            outcomes = self.parse_junit_xml(junit_xml_path)
        finally:
            # Best-effort cleanup of temporary artifact.
            try:
                os.unlink(junit_xml_path)
            except OSError:
                pass

        return outcomes

    def parse_junit_xml(self, junit_xml_path: str) -> dict[str, bool]:
        xml_path = Path(junit_xml_path)
        if not xml_path.exists():
            return {}

        tree = ET.parse(xml_path)
        root = tree.getroot()

        outcomes: dict[str, bool] = {}
        for testcase in root.iter("testcase"):
            node_id = _build_node_id(testcase)
            if not node_id:
                continue

            if testcase.find("skipped") is not None:
                continue

            passed = testcase.find("failure") is None and testcase.find("error") is None
            # If duplicate entries appear (e.g., rerun plugins), any failure wins.
            if node_id in outcomes:
                outcomes[node_id] = outcomes[node_id] and passed
            else:
                outcomes[node_id] = passed

        return outcomes


def _build_node_id(testcase: ET.Element) -> str:
    name = (testcase.get("name") or "").strip()
    if not name:
        return ""

    # Some emitters already include node ids in `name`.
    if "::" in name:
        return name

    file_attr = (testcase.get("file") or "").strip()
    classname = (testcase.get("classname") or "").strip()

    if file_attr:
        if classname:
            module_from_file = file_attr.removesuffix(".py").replace("/", ".")
            if classname == module_from_file:
                return f"{file_attr}::{name}"
            if classname.startswith(module_from_file + "."):
                class_tail = classname[len(module_from_file) + 1 :].replace(".", "::")
                return f"{file_attr}::{class_tail}::{name}"
        return f"{file_attr}::{name}"

    if classname:
        parts = [part for part in classname.split(".") if part]
        module_parts: list[str] = []
        class_parts: list[str] = []
        for part in parts:
            if class_parts:
                class_parts.append(part)
            elif part[:1].isupper():
                class_parts.append(part)
            else:
                module_parts.append(part)

        if module_parts:
            module_path = "/".join(module_parts) + ".py"
            if class_parts:
                return f"{module_path}::{'::'.join(class_parts)}::{name}"
            return f"{module_path}::{name}"

        return f"{classname.replace('.', '::')}::{name}"

    return name
