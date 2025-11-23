"""Type analysis module.

Analyzes code using:
- mypy (type coverage)
- vulture (dead code detection)
- interrogate (docstring coverage)
"""

import subprocess
from typing import Any

from btx_fix_mcp.subservers.common.issues import (
    DocstringCoverageMetrics,
    TypeCoverageMetrics,
)
from btx_fix_mcp.config import get_timeout
from btx_fix_mcp.tools_venv import get_tool_path

from .base import BaseAnalyzer


class TypeAnalyzer(BaseAnalyzer):
    """Type coverage and related analysis."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Run type analysis on files.

        Returns:
            Dictionary with keys: type_coverage, dead_code, docstring_coverage
        """
        return {
            "type_coverage": self._analyze_type_coverage(files).model_dump(),
            "dead_code": self._detect_dead_code(files),
            "docstring_coverage": self._analyze_docstring_coverage(files).model_dump(),
        }

    def _analyze_type_coverage(self, files: list[str]) -> TypeCoverageMetrics:
        """Analyze type coverage using mypy."""
        metrics = TypeCoverageMetrics()
        if not files:
            return metrics

        mypy = str(get_tool_path("mypy"))
        try:
            result = self._run_mypy(mypy, files)
            metrics.raw_output = result.stdout + result.stderr
            self._parse_mypy_output(result.stdout, metrics)
            self._calculate_type_coverage_percent(metrics)
        except subprocess.TimeoutExpired:
            self.logger.warning("mypy timed out")
        except FileNotFoundError:
            self.logger.warning("mypy not found")
        except Exception as e:
            self.logger.warning(f"mypy error: {e}")

        return metrics

    def _run_mypy(self, mypy: str, files: list[str]) -> subprocess.CompletedProcess:
        """Run mypy on files."""
        timeout = get_timeout("tool_long", 120)
        return subprocess.run(
            [mypy, "--ignore-missing-imports", "--show-error-codes", "--no-error-summary"] + files,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _parse_mypy_output(self, stdout: str, metrics: TypeCoverageMetrics) -> None:
        """Parse mypy output for typed/untyped function counts."""
        for line in stdout.split("\n"):
            if "error:" in line:
                metrics.errors.append(line.strip())

            if "note: def" not in line:
                continue

            if "-> " not in line:
                metrics.untyped_functions += 1
            else:
                metrics.typed_functions += 1

    def _calculate_type_coverage_percent(self, metrics: TypeCoverageMetrics) -> None:
        """Calculate type coverage percentage."""
        total = metrics.typed_functions + metrics.untyped_functions
        if total > 0:
            metrics.coverage_percent = round((metrics.typed_functions / total) * 100, 1)

    def _detect_dead_code(self, files: list[str]) -> dict[str, Any]:
        """Detect dead code using vulture."""
        results = {"dead_code": [], "raw_output": ""}
        if not files:
            return results

        confidence = self.config.get("dead_code_confidence", 80)
        vulture = str(get_tool_path("vulture"))

        try:
            result = self._run_vulture(vulture, confidence, files)
            results["raw_output"] = result.stdout
            self._parse_vulture_output(result.stdout, results)
        except subprocess.TimeoutExpired:
            self.logger.warning("vulture timed out")
        except FileNotFoundError:
            self.logger.warning("vulture not found")
        except Exception as e:
            self.logger.warning(f"vulture error: {e}")

        return results

    def _run_vulture(self, vulture: str, confidence: int, files: list[str]) -> subprocess.CompletedProcess:
        """Run vulture on files."""
        timeout = get_timeout("tool_analysis", 60)
        return subprocess.run(
            [vulture, f"--min-confidence={confidence}"] + files,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _parse_vulture_output(self, stdout: str, results: dict[str, Any]) -> None:
        """Parse vulture output for dead code."""
        for line in stdout.split("\n"):
            if not line.strip() or "unused" not in line.lower():
                continue

            # Parse: filename.py:123: unused variable 'x' (60% confidence)
            parts = line.split(":")
            if len(parts) < 3:
                continue

            results["dead_code"].append(
                {
                    "file": self._get_relative_path(parts[0]),
                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                    "message": ":".join(parts[2:]).strip(),
                }
            )

    def _analyze_docstring_coverage(self, files: list[str]) -> DocstringCoverageMetrics:
        """Analyze docstring coverage using interrogate."""
        metrics = DocstringCoverageMetrics()
        if not files:
            return metrics

        interrogate = str(get_tool_path("interrogate"))
        try:
            result = self._run_interrogate(interrogate, files)
            metrics.raw_output = result.stdout
            self._parse_interrogate_output(result.stdout, metrics)
        except subprocess.TimeoutExpired:
            self.logger.warning("interrogate timed out")
        except FileNotFoundError:
            self.logger.warning("interrogate not found")
        except Exception as e:
            self.logger.warning(f"interrogate error: {e}")

        return metrics

    def _run_interrogate(self, interrogate: str, files: list[str]) -> subprocess.CompletedProcess:
        """Run interrogate on files."""
        timeout = get_timeout("tool_analysis", 60)
        return subprocess.run(
            [interrogate, "-v", "--fail-under=0"] + files,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _parse_interrogate_output(self, stdout: str, metrics: DocstringCoverageMetrics) -> None:
        """Parse interrogate output for coverage and missing docstrings."""
        import re

        for line in stdout.split("\n"):
            if "%" in line and ("PASSED" in line or "FAILED" in line):
                match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                if match:
                    metrics.coverage_percent = float(match.group(1))
            elif "missing" in line.lower() or "no docstring" in line.lower():
                metrics.missing.append(line.strip())
