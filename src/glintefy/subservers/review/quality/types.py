"""Type analysis module.

Analyzes code using:
- mypy (type coverage)
- vulture (dead code detection)
- interrogate (docstring coverage)
"""

import subprocess

from glintefy.config import get_timeout, get_tool_config
from glintefy.subservers.common.issues import (
    DocstringCoverageMetrics,
    TypeCoverageMetrics,
)
from glintefy.tools_venv import get_tool_path

from .analyzer_results import DeadCodeItem, DeadCodeResults, TypeResults
from .base import BaseAnalyzer


class TypeAnalyzer(BaseAnalyzer[TypeResults]):
    """Type coverage and related analysis."""

    def analyze(self, files: list[str]) -> TypeResults:
        """Run type analysis on files.

        Returns:
            TypeResults dataclass with type_coverage, dead_code, docstring_coverage
        """
        return TypeResults(
            type_coverage=self._analyze_type_coverage(files),
            dead_code=self._detect_dead_code(files),
            docstring_coverage=self._analyze_docstring_coverage(files),
        )

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
        mypy_timeout = get_timeout("tool_long", 240)

        # Get mypy config settings
        mypy_config = get_tool_config("mypy")
        python_version = mypy_config.get("python_version", "3.13")
        strict = mypy_config.get("strict", False)
        ignore_missing_imports = mypy_config.get("ignore_missing_imports", True)
        show_error_codes = mypy_config.get("show_error_codes", True)
        pretty = mypy_config.get("pretty", True)

        # Build command with config options
        cmd = [mypy, f"--python-version={python_version}", "--no-error-summary"]

        if strict:
            cmd.append("--strict")
        if ignore_missing_imports:
            cmd.append("--ignore-missing-imports")
        if show_error_codes:
            cmd.append("--show-error-codes")
        if pretty:
            cmd.append("--pretty")

        return subprocess.run(
            cmd + files,
            check=False,
            capture_output=True,
            text=True,
            timeout=mypy_timeout,
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

    def _detect_dead_code(self, files: list[str]) -> DeadCodeResults:
        """Detect dead code using vulture."""
        results = DeadCodeResults()
        if not files:
            return results

        confidence = self.config.get("dead_code_confidence", 80)
        vulture = str(get_tool_path("vulture"))

        try:
            result = self._run_vulture(vulture, confidence, files)
            results.raw_output = result.stdout
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
        vulture_timeout = get_timeout("tool_analysis", 120)
        return subprocess.run(
            [vulture, f"--min-confidence={confidence}"] + files,
            check=False,
            capture_output=True,
            text=True,
            timeout=vulture_timeout,
        )

    def _parse_vulture_output(self, stdout: str, results: DeadCodeResults) -> None:
        """Parse vulture output for dead code."""
        import re

        # Pattern: file_path:line_number: message
        # Handle Windows paths like C:\path\file.py:123: message
        pattern = re.compile(r"^(.+?):(\d+):\s*(.+)$")

        for line in stdout.split("\n"):
            if not line.strip() or "unused" not in line.lower():
                continue

            match = pattern.match(line)
            if not match:
                continue

            file_path, line_num, message = match.groups()
            results.dead_code.append(
                DeadCodeItem(
                    file=self._get_relative_path(file_path),
                    line=int(line_num),
                    message=message.strip(),
                )
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
        interrogate_timeout = get_timeout("tool_analysis", 120)
        return subprocess.run(
            [interrogate, "-v", "--fail-under=0"] + files,
            check=False,
            capture_output=True,
            text=True,
            timeout=interrogate_timeout,
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
